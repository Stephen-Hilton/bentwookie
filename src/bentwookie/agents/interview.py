"""Interview engine for BentWookie V2.

Manages conversational interviews with AI agents (Business Owner and
Enterprise Architect) during the Define phase.  Each interview runs as
a Claude Code agent in a BW-managed terminal shell.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from ..constants import (
    AGENT_STATUS_ERROR,
    INTERVIEW_STATUS_ACTIVE,
    INTERVIEW_STATUS_COMPLETE,
    INTERVIEW_STATUS_ERROR,
    INTERVIEW_STATUS_PENDING,
    INTERVIEW_TYPE_BO,
    INTERVIEW_TYPE_EA,
    ROLE_BUSINESS_OWNER,
    ROLE_ENTERPRISE_ARCHITECT,
)
from ..db import queries
from ..logging_util import BWLogger
from .prompts import load_prompt

if TYPE_CHECKING:
    from .manager import AgentManager

# Poll timing for response collection
_POLL_INTERVAL: float = 0.5  # seconds between poll attempts
_POLL_TIMEOUT: float = 120.0  # max seconds to wait for a response
_POLL_SILENCE: float = 2.0  # seconds of silence before returning


class InterviewEngine:
    """Manages conversational interviews with AI agents.

    The interview engine orchestrates two sequential interviews during
    the Define phase:

    1. **Business Owner** -- extracts business goals, target users,
       success criteria, constraints, and timeline preferences.
    2. **Enterprise Architect** -- extracts technology stack, scalability
       needs, integration points, security requirements, data model,
       and deployment strategy.

    Each interview creates a Claude Code agent via the AgentManager,
    streams user messages into the agent's stdin, and captures agent
    responses.  Transcripts are persisted in the database.
    """

    def __init__(self, manager: AgentManager) -> None:
        self._manager = manager
        self._logger = BWLogger(name="bentwookie.interview")
        # Map interview_id -> agent_id for active interviews
        self._active: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_interview(
        self,
        project_id: int,
        interview_type: str,
    ) -> int:
        """Start a new interview session.

        Creates an interview record, spawns a Claude Code agent with the
        appropriate role, and sends the initial system prompt.

        Args:
            project_id: ID of the project being defined.
            interview_type: One of ``INTERVIEW_TYPE_BO`` or
                ``INTERVIEW_TYPE_EA``.

        Returns:
            The interview ID.

        Raises:
            ValueError: If *interview_type* is not recognised.
        """
        if interview_type not in (INTERVIEW_TYPE_BO, INTERVIEW_TYPE_EA):
            raise ValueError(
                f"Invalid interview type: {interview_type!r}. "
                f"Must be {INTERVIEW_TYPE_BO!r} or {INTERVIEW_TYPE_EA!r}."
            )

        # Persist interview record
        interview_id = queries.create_interview(project_id, interview_type)
        self._logger.info(
            f"Created interview {interview_id} "
            f"(type={interview_type}, project={project_id})"
        )

        # Determine agent role
        role = (
            ROLE_BUSINESS_OWNER
            if interview_type == INTERVIEW_TYPE_BO
            else ROLE_ENTERPRISE_ARCHITECT
        )

        # Spawn the agent via the manager
        try:
            agent_id = await self._manager.spawn_agent(
                project_id=project_id,
                role=role,
            )
        except RuntimeError as exc:
            queries.update_interview(
                interview_id, itvstatus=INTERVIEW_STATUS_ERROR
            )
            self._logger.error(
                f"Interview {interview_id}: failed to spawn agent: {exc}"
            )
            raise

        self._active[interview_id] = agent_id

        # Mark interview as active
        queries.update_interview(
            interview_id, itvstatus=INTERVIEW_STATUS_ACTIVE
        )

        # Build and send the initial prompt
        project = queries.get_project(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        prompt = self._get_interview_prompt(interview_type, project)

        try:
            self._manager.write_input(agent_id, prompt)
        except (KeyError, OSError) as exc:
            self._handle_agent_death(interview_id, agent_id)
            raise RuntimeError(
                f"Failed to send initial prompt to agent "
                f"{agent_id}: {exc}"
            ) from exc

        # Save the system prompt as the first agent message
        queries.create_interview_message(
            interview_id, "agent", prompt
        )

        self._logger.info(
            f"Interview {interview_id} started with agent {agent_id}"
        )
        return interview_id

    async def send_user_message(
        self,
        interview_id: int,
        content: str,
    ) -> None:
        """Send a user message to the interview agent.

        The message is persisted in the database and forwarded to the
        agent's stdin via the manager.  If the agent process has died,
        the interview is marked as ``error``.

        Args:
            interview_id: ID of the active interview.
            content: The user's message text.

        Raises:
            ValueError: If the interview is not active.
            RuntimeError: If the agent process is no longer alive.
        """
        agent_id = self._active.get(interview_id)
        if agent_id is None:
            raise ValueError(
                f"Interview {interview_id} is not active"
            )

        # Check agent is still alive before sending
        if not self._manager.is_agent_alive(agent_id):
            self._handle_agent_death(interview_id, agent_id)
            raise RuntimeError(
                f"Agent {agent_id} for interview {interview_id} has "
                f"died unexpectedly"
            )

        # Persist user message
        queries.create_interview_message(interview_id, "user", content)

        # Forward to agent stdin
        self._manager.write_input(agent_id, content)

        self._logger.debug(
            f"User message sent to interview {interview_id}"
        )

    async def get_response(
        self,
        interview_id: int,
    ) -> str | None:
        """Read a single chunk of output from the interview agent.

        If no output is available yet, returns ``None``.  If the agent
        process has died, the interview is marked as ``error``.

        Args:
            interview_id: ID of the active interview.

        Returns:
            The agent response text, or ``None`` if nothing is
            available yet.

        Raises:
            ValueError: If the interview is not active.
            RuntimeError: If the agent process is no longer alive.
        """
        agent_id = self._active.get(interview_id)
        if agent_id is None:
            raise ValueError(
                f"Interview {interview_id} is not active"
            )

        # Check agent liveness
        if not self._manager.is_agent_alive(agent_id):
            self._handle_agent_death(interview_id, agent_id)
            raise RuntimeError(
                f"Agent {agent_id} for interview {interview_id} has "
                f"died unexpectedly"
            )

        output = self._manager.read_output(agent_id)
        if output:
            queries.create_interview_message(
                interview_id, "agent", output
            )
        return output if output else None

    async def poll_response(
        self,
        interview_id: int,
    ) -> str | None:
        """Poll for a complete response from the interview agent.

        Repeatedly reads output with a short sleep between attempts.
        Accumulates text until the agent stops producing output for
        ``_POLL_SILENCE`` seconds, or until ``_POLL_TIMEOUT`` is
        reached.

        Args:
            interview_id: ID of the active interview.

        Returns:
            The accumulated response text, or ``None`` if nothing was
            received before the timeout.

        Raises:
            ValueError: If the interview is not active.
        """
        agent_id = self._active.get(interview_id)
        if agent_id is None:
            raise ValueError(
                f"Interview {interview_id} is not active"
            )

        accumulated: list[str] = []
        elapsed: float = 0.0
        silence: float = 0.0

        while elapsed < _POLL_TIMEOUT:
            # Detect agent death mid-poll
            if not self._manager.is_agent_alive(agent_id):
                self._logger.warning(
                    f"Agent {agent_id} died during poll for "
                    f"interview {interview_id}"
                )
                # Return whatever we have so far; caller decides
                # whether partial output is usable
                if not accumulated:
                    self._handle_agent_death(interview_id, agent_id)
                    return None
                break

            output = self._manager.read_output(agent_id)
            if output:
                accumulated.append(output)
                silence = 0.0
            else:
                silence += _POLL_INTERVAL
                if accumulated and silence >= _POLL_SILENCE:
                    # Agent has gone quiet after producing output
                    break

            await asyncio.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL

        if not accumulated:
            return None

        full_response = "".join(accumulated)

        # Persist the complete response as a single message
        queries.create_interview_message(
            interview_id, "agent", full_response
        )

        self._logger.debug(
            f"Polled response from interview {interview_id} "
            f"({len(full_response)} chars)"
        )
        return full_response

    async def complete_interview(
        self,
        interview_id: int,
    ) -> str:
        """Complete an interview and produce a structured summary.

        Sends a completion prompt to the agent, waits for the summary,
        persists it on the interview record, terminates the agent, and
        returns the summary text.

        Args:
            interview_id: ID of the active interview.

        Returns:
            The structured summary produced by the agent.

        Raises:
            ValueError: If the interview is not active.
            RuntimeError: If the agent fails to produce a summary.
        """
        agent_id = self._active.get(interview_id)
        if agent_id is None:
            raise ValueError(
                f"Interview {interview_id} is not active"
            )

        interview = queries.get_interview(interview_id)
        if interview is None:
            raise ValueError(f"Interview {interview_id} not found")

        interview_type = interview["itvtype"]

        # Check agent is still alive before requesting summary
        if not self._manager.is_agent_alive(agent_id):
            self._handle_agent_death(interview_id, agent_id)
            raise RuntimeError(
                f"Agent {agent_id} for interview {interview_id} has "
                f"died before summary could be generated"
            )

        # Send the completion prompt
        completion_prompt = self._get_completion_prompt(interview_type)
        try:
            self._manager.write_input(agent_id, completion_prompt)
        except (KeyError, OSError) as exc:
            self._handle_agent_death(interview_id, agent_id)
            raise RuntimeError(
                f"Failed to send completion prompt to agent "
                f"{agent_id}: {exc}"
            ) from exc

        queries.create_interview_message(
            interview_id, "user", completion_prompt
        )

        # Wait for the summary
        summary = await self.poll_response(interview_id)
        if not summary:
            queries.update_interview(
                interview_id, itvstatus=INTERVIEW_STATUS_ERROR
            )
            self._logger.error(
                f"Interview {interview_id}: agent failed to produce "
                f"a summary"
            )
            raise RuntimeError(
                f"Agent failed to produce a summary for interview "
                f"{interview_id}"
            )

        # Persist summary and mark complete
        queries.update_interview(
            interview_id,
            itvstatus=INTERVIEW_STATUS_COMPLETE,
            itvsummary=summary,
        )

        # Terminate the agent
        await self._manager.terminate_agent(agent_id)
        del self._active[interview_id]

        self._logger.info(
            f"Interview {interview_id} completed "
            f"({len(summary)} char summary)"
        )
        return summary

    def get_transcript(self, interview_id: int) -> list[dict]:
        """Return the full transcript of an interview.

        Args:
            interview_id: ID of the interview.

        Returns:
            Chronologically ordered list of message dicts with keys
            such as ``imsgsender`` and ``imsgcontent``.
        """
        return queries.get_interview_messages(interview_id)

    # ------------------------------------------------------------------
    # Error handling (private)
    # ------------------------------------------------------------------

    def _handle_agent_death(
        self,
        interview_id: int,
        agent_id: int,
    ) -> None:
        """Handle an agent process that has died unexpectedly.

        Marks the interview as ``error``, cleans up internal tracking,
        and logs the incident.

        Args:
            interview_id: ID of the interview whose agent died.
            agent_id: ID of the dead agent.
        """
        error_msg = (
            f"Agent {agent_id} process died unexpectedly during "
            f"interview {interview_id}"
        )
        self._logger.error(error_msg)

        queries.update_interview(
            interview_id, itvstatus=INTERVIEW_STATUS_ERROR
        )
        queries.update_agent(
            agent_id,
            agtstatus=AGENT_STATUS_ERROR,
            agterror=error_msg,
        )

        # Remove from active tracking
        self._active.pop(interview_id, None)

    async def _check_agent_timeout(
        self,
        interview_id: int,
        agent_id: int,
        timeout: float = _POLL_TIMEOUT,
    ) -> None:
        """Verify the agent responds within the given timeout.

        If no output is received within *timeout* seconds, the
        interview is marked as ``error`` and the agent is terminated.

        Args:
            interview_id: ID of the active interview.
            agent_id: ID of the agent to check.
            timeout: Maximum seconds to wait.

        Raises:
            RuntimeError: If the agent times out.
        """
        elapsed: float = 0.0
        while elapsed < timeout:
            if not self._manager.is_agent_alive(agent_id):
                self._handle_agent_death(interview_id, agent_id)
                raise RuntimeError(
                    f"Agent {agent_id} died while waiting for response "
                    f"(interview {interview_id})"
                )

            output = self._manager.read_output(agent_id)
            if output:
                return  # agent is responsive

            await asyncio.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL

        # Timed out
        error_msg = (
            f"Agent {agent_id} timed out after {timeout}s for "
            f"interview {interview_id}"
        )
        self._logger.error(error_msg)

        queries.update_interview(
            interview_id, itvstatus=INTERVIEW_STATUS_ERROR
        )
        queries.update_agent(
            agent_id,
            agtstatus=AGENT_STATUS_ERROR,
            agterror=error_msg,
        )
        self._active.pop(interview_id, None)

        # Attempt to terminate the stuck agent
        try:
            await self._manager.terminate_agent(agent_id)
        except Exception as exc:
            self._logger.error(
                f"Failed to terminate timed-out agent {agent_id}: {exc}"
            )

        raise RuntimeError(error_msg)

    # ------------------------------------------------------------------
    # Prompt generation (private)
    # ------------------------------------------------------------------

    def _get_interview_prompt(
        self,
        interview_type: str,
        project: dict,
    ) -> str:
        """Build the initial system prompt for an interview.

        Args:
            interview_type: ``INTERVIEW_TYPE_BO`` or
                ``INTERVIEW_TYPE_EA``.
            project: Project dict (must contain at least ``prjname``).

        Returns:
            The system prompt string.
        """
        project_name = project.get("prjname", "Unnamed Project")
        project_desc = project.get("prjdesc") or "No description yet."

        if interview_type == INTERVIEW_TYPE_BO:
            return load_prompt(
                "ba_interview01_intro",
                project_name=project_name,
                project_desc=project_desc,
            )

        # INTERVIEW_TYPE_EA
        # Retrieve the BO transcript so the EA can build on it
        bo_transcript_section = ""
        bo_interviews = queries.list_interviews(
            prjid=project.get("prjid"), status=INTERVIEW_STATUS_COMPLETE
        )
        for bo_itv in bo_interviews:
            if bo_itv.get("itvtype") == INTERVIEW_TYPE_BO:
                bo_messages = queries.get_interview_messages(bo_itv["itvid"])
                if bo_messages:
                    lines = []
                    for msg in bo_messages:
                        sender = msg.get("imsgsender", "unknown")
                        text = msg.get("imsgcontent", "")
                        lines.append(f"[{sender}] {text}")
                    bo_transcript_section = (
                        "\n\n--- Business Owner Interview Transcript ---\n"
                        + "\n".join(lines)
                        + "\n--- End of Transcript ---\n\n"
                    )
                elif bo_itv.get("itvsummary"):
                    bo_transcript_section = (
                        "\n\n--- Business Owner Summary ---\n"
                        + bo_itv["itvsummary"]
                        + "\n--- End of Summary ---\n\n"
                    )
                break  # use the first completed BO interview

        return load_prompt(
            "ea_interview01_intro",
            project_name=project_name,
            project_desc=project_desc,
            bo_transcript_section=bo_transcript_section,
        )

    def _get_completion_prompt(self, interview_type: str) -> str:
        """Build the prompt that asks the agent to summarise.

        Args:
            interview_type: ``INTERVIEW_TYPE_BO`` or
                ``INTERVIEW_TYPE_EA``.

        Returns:
            The completion prompt string.
        """
        if interview_type == INTERVIEW_TYPE_BO:
            return load_prompt("ba_interview02_summary")

        return load_prompt("ea_interview02_summary")


# ------------------------------------------------------------------
# Web-facing response generation (Claude CLI in print mode)
# ------------------------------------------------------------------

_interview_sessions: dict[int, str] = {}


def _build_web_system_prompt(interview: dict) -> str:
    """Build a system prompt for web-based interview responses.

    Mirrors ``InterviewEngine._get_interview_prompt()`` but operates
    on an interview dict rather than requiring a running AgentManager.
    """
    prjid = interview.get("prjid")
    project = queries.get_project(prjid) if prjid else None
    project_name = (project or interview).get("prjname", "Unnamed Project")
    project_desc = (project or {}).get("prjdesc") or "No description yet."
    itvtype = interview.get("itvtype", INTERVIEW_TYPE_BO)

    if itvtype == INTERVIEW_TYPE_BO:
        return load_prompt(
            "ba_interview01_intro",
            project_name=project_name,
            project_desc=project_desc,
        )

    # Enterprise Architect — inject BO transcript
    bo_transcript_section = ""
    bo_interviews = queries.list_interviews(
        prjid=prjid, status=INTERVIEW_STATUS_COMPLETE
    )
    for bo_itv in bo_interviews:
        if bo_itv.get("itvtype") == INTERVIEW_TYPE_BO:
            bo_messages = queries.get_interview_messages(bo_itv["itvid"])
            if bo_messages:
                lines = []
                for msg in bo_messages:
                    sender = msg.get("imsgsender", "unknown")
                    text = msg.get("imsgcontent", "")
                    lines.append(f"[{sender}] {text}")
                bo_transcript_section = (
                    "\n\n--- Business Owner Interview Transcript ---\n"
                    + "\n".join(lines)
                    + "\n--- End of Transcript ---\n\n"
                )
            elif bo_itv.get("itvsummary"):
                bo_transcript_section = (
                    "\n\n--- Business Owner Summary ---\n"
                    + bo_itv["itvsummary"]
                    + "\n--- End of Summary ---\n\n"
                )
            break

    return load_prompt(
        "ea_interview01_intro",
        project_name=project_name,
        project_desc=project_desc,
        bo_transcript_section=bo_transcript_section,
    )


def generate_response(interview: dict, user_message: str) -> str:
    """Generate an AI interview response via Claude CLI in print mode.

    Uses the ``claude`` CLI with ``-p`` (print mode) so that it works
    with Max subscription auth — no API key required.  Conversation
    state is maintained across messages via Claude's session persistence.

    Args:
        interview: Interview dict (must contain ``itvid``).
        user_message: The user's message text.

    Returns:
        The AI response text.

    Raises:
        FileNotFoundError: If the ``claude`` CLI is not installed.
        RuntimeError: If the CLI returns a non-zero exit code.
    """
    import subprocess
    import uuid

    from ..settings import get_model

    itvid = interview["itvid"]
    model = get_model()

    if itvid not in _interview_sessions:
        # First message — create session with system prompt
        session_id = str(uuid.uuid4())
        _interview_sessions[itvid] = session_id
        system_prompt = _build_web_system_prompt(interview)
        cmd = [
            "claude", "-p",
            "--model", model,
            "--system-prompt", system_prompt,
            "--session-id", session_id,
            user_message,
        ]
    else:
        # Subsequent — resume existing session
        session_id = _interview_sessions[itvid]
        cmd = [
            "claude", "-p",
            "--model", model,
            "--resume", session_id,
            user_message,
        ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=180,
    )

    if result.returncode != 0:
        # If resume failed (stale session), retry with fresh session
        if itvid in _interview_sessions and "--resume" in " ".join(cmd):
            del _interview_sessions[itvid]
            return generate_response(interview, user_message)
        raise RuntimeError(f"Claude CLI error: {result.stderr[:500]}")

    return result.stdout.strip()
