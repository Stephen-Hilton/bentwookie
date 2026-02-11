"""Agent Manager for BentWookie V2.

Spawns, monitors, and communicates with Claude Code agent instances
running in BW-managed terminal shells using subprocess + pty.
"""

import asyncio
import fcntl
import os
import pty
import select
import signal
import subprocess
from typing import Any

from pathlib import Path

from ..constants import (
    AGENT_STATUS_ERROR,
    AGENT_STATUS_IDLE,
    AGENT_STATUS_TERMINATED,
    AGENT_STATUS_WAITING,
    AGENT_STATUS_WORKING,
    DEFAULT_MODEL,
    ROLE_BUSINESS_ARCHITECT,
    ROLE_BUSINESS_OWNER,
    ROLE_CODING_AGENT,
    ROLE_ENTERPRISE_ARCHITECT,
    ROLE_NAMES,
    ROLE_SERVICE_ENGINEER,
    ROLE_TESTING_AGENT,
)
from ..db import queries
from ..logging_util import BWLogger
from ..settings import get_agent_timeout, get_max_concurrent_agents, get_model, get_setting, resolve_setting
from .prompts import load_prompt

# Maximum output buffer size per agent (100 KB).
_MAX_BUFFER_SIZE = 100 * 1024


class AgentManager:
    """Manages the lifecycle of Claude Code agent subprocesses.

    Each agent runs as a ``claude`` CLI process inside a BW-owned
    pseudo-terminal so that BW can observe, message, or terminate it at
    any time.
    """

    def __init__(self) -> None:
        """Initialize the manager with empty tracking structures."""
        self._processes: dict[int, subprocess.Popen] = {}
        self._master_fds: dict[int, int] = {}
        self._output_buffers: dict[int, str] = {}
        self.logger = BWLogger(name="bentwookie.agents.manager")

    # -----------------------------------------------------------------
    # Spawn
    # -----------------------------------------------------------------

    async def spawn_agent(
        self,
        role: str,
        project_id: int,
        component_id: int | None = None,
        model: str | None = None,
    ) -> int:
        """Create a new agent record and spawn a Claude CLI subprocess.

        Args:
            role: Agent role (one of the ``ROLE_*`` constants).
            project_id: The project this agent belongs to.
            component_id: Optional component the agent is assigned to.
            model: Claude model override.  Falls back to
                ``get_model()`` then ``DEFAULT_MODEL``.

        Returns:
            The database ID of the newly created agent.

        Raises:
            RuntimeError: If the maximum number of concurrent agents has
                been reached or the subprocess fails to start.
        """
        active_count = queries.count_active_agents(project_id)
        max_agents = get_max_concurrent_agents()
        if active_count >= max_agents:
            raise RuntimeError(
                f"Max concurrent agents ({max_agents}) reached for "
                f"project {project_id}"
            )

        resolved_model = model or resolve_setting("model", agent_role=role) or DEFAULT_MODEL
        agent_name = f"{ROLE_NAMES.get(role, role)}-{project_id}"
        if component_id is not None:
            agent_name += f"-c{component_id}"

        # Persist the agent record.
        agent_id = queries.create_agent(
            prjid=project_id,
            agtrole=role,
            agtname=agent_name,
            agtmodel=resolved_model,
            agtcmpid=component_id,
        )

        try:
            # Create a pseudo-terminal pair.
            master_fd, slave_fd = pty.openpty()

            # Make the master fd non-blocking so reads never hang.
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Resolve working directory from project's code directory.
            project = queries.get_project(project_id)
            work_dir = project.get("prjcodedir") if project else None

            # Build the command with configurable permission mode.
            permission_mode = get_setting(
                "agent_permission_mode", "dangerously-skip-permissions"
            )
            cmd = ["claude", "--model", resolved_model]
            if permission_mode == "dangerously-skip-permissions":
                cmd.append("--dangerously-skip-permissions")
            else:
                cmd.extend(["--permission-mode", permission_mode])

            proc = subprocess.Popen(
                cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                cwd=work_dir if work_dir and Path(work_dir).is_dir() else None,
            )

            # The slave fd is now owned by the child; close our copy.
            os.close(slave_fd)

            # Track the subprocess and pty.
            self._processes[agent_id] = proc
            self._master_fds[agent_id] = master_fd
            self._output_buffers[agent_id] = ""

            # Update the agent record with the shell PID.
            queries.update_agent(
                agent_id,
                agtshellpid=proc.pid,
                agtstatus=AGENT_STATUS_IDLE,
            )

            self.logger.info(
                f"Agent {agent_id} ({agent_name}) spawned with PID "
                f"{proc.pid}, model={resolved_model}"
            )

            # Send the system prompt so the agent knows its role.
            system_prompt = self._get_system_prompt(role, project_id, component_id)
            await self.send_message(agent_id, system_prompt)

        except Exception as exc:
            queries.update_agent(
                agent_id,
                agtstatus=AGENT_STATUS_ERROR,
                agterror=str(exc),
            )
            self.logger.error(f"Agent {agent_id} failed to spawn: {exc}")
            raise RuntimeError(f"Failed to spawn agent {agent_id}: {exc}") from exc

        return agent_id

    # -----------------------------------------------------------------
    # Messaging
    # -----------------------------------------------------------------

    async def send_message(
        self,
        agent_id: int,
        message: str,
        urgent: bool = False,
    ) -> None:
        """Write a message to the agent's stdin via the master fd.

        Args:
            agent_id: Target agent database ID.
            message: The text to send.
            urgent: If ``True`` the message is prefixed with
                ``[URGENT] ``.

        Raises:
            KeyError: If the agent is not tracked by this manager.
            OSError: If the write to the pty fails.
        """
        master_fd = self._master_fds.get(agent_id)
        if master_fd is None:
            raise KeyError(f"Agent {agent_id} is not tracked by this manager")

        payload = message
        if urgent:
            payload = f"[URGENT] {payload}"

        # Ensure the message ends with a newline so the CLI processes
        # it as a complete input.
        if not payload.endswith("\n"):
            payload += "\n"

        os.write(master_fd, payload.encode("utf-8"))

        self.logger.debug(
            f"Sent {'urgent ' if urgent else ''}message to agent "
            f"{agent_id} ({len(payload)} bytes)"
        )

    def write_input(self, agent_id: int, text: str) -> None:
        """Write raw text to an agent's stdin (synchronous, no framing).

        This is a low-level helper used by the interview engine to
        forward user messages directly.  Unlike :meth:`send_message`,
        it is synchronous and does not add an ``[URGENT]`` prefix.

        Args:
            agent_id: Target agent database ID.
            text: The text to write.

        Raises:
            KeyError: If the agent is not tracked by this manager.
            OSError: If the write to the pty fails.
        """
        master_fd = self._master_fds.get(agent_id)
        if master_fd is None:
            raise KeyError(f"Agent {agent_id} is not tracked by this manager")

        payload = text if text.endswith("\n") else text + "\n"
        os.write(master_fd, payload.encode("utf-8"))
        self.logger.debug(
            f"write_input to agent {agent_id} ({len(payload)} bytes)"
        )

    def is_agent_alive(self, agent_id: int) -> bool:
        """Check whether an agent subprocess is still running.

        Args:
            agent_id: Target agent database ID.

        Returns:
            ``True`` if the subprocess exists and has not exited.
        """
        proc = self._processes.get(agent_id)
        if proc is None:
            return False
        return proc.poll() is None

    # -----------------------------------------------------------------
    # Output reading
    # -----------------------------------------------------------------

    def read_output(self, agent_id: int, max_bytes: int = 4096) -> str:
        """Non-blocking read from the agent's master fd.

        Args:
            agent_id: Target agent database ID.
            max_bytes: Maximum number of bytes to read in one call.

        Returns:
            Decoded output string, or an empty string if nothing is
            available.
        """
        master_fd = self._master_fds.get(agent_id)
        if master_fd is None:
            return ""

        ready, _, _ = select.select([master_fd], [], [], 0)
        if not ready:
            return ""

        try:
            data = os.read(master_fd, max_bytes)
            return data.decode("utf-8", errors="replace")
        except OSError:
            return ""

    def get_agent_output_buffer(self, agent_id: int) -> str:
        """Return the accumulated output buffer for an agent.

        Args:
            agent_id: Target agent database ID.

        Returns:
            The full output buffer string (may be empty).
        """
        return self._output_buffers.get(agent_id, "")

    def _poll_output(self, agent_id: int) -> None:
        """Read available output from an agent and append to its buffer.

        The buffer is capped at ``_MAX_BUFFER_SIZE`` bytes; older data
        is discarded when the cap is exceeded.  Output chunks are also
        persisted to the ``agent_output`` table so the web UI can
        stream them.

        Args:
            agent_id: Target agent database ID.
        """
        chunk = self.read_output(agent_id)
        if not chunk:
            return

        buf = self._output_buffers.get(agent_id, "") + chunk
        if len(buf) > _MAX_BUFFER_SIZE:
            buf = buf[-_MAX_BUFFER_SIZE:]
        self._output_buffers[agent_id] = buf

        # Persist to DB for web UI streaming
        try:
            queries.append_agent_output(agent_id, chunk)
        except Exception:
            pass  # Don't fail the poll if DB write fails

    async def poll_all_outputs(self) -> None:
        """Poll output from all active agents."""
        for agent_id in list(self._master_fds):
            self._poll_output(agent_id)

    # -----------------------------------------------------------------
    # Termination
    # -----------------------------------------------------------------

    async def terminate_agent(self, agent_id: int) -> None:
        """Terminate an agent subprocess and clean up resources.

        Sends ``SIGTERM`` first, waits up to 5 seconds, then sends
        ``SIGKILL`` if the process is still alive.  Updates the agent
        status to ``terminated`` in the database and closes the pty
        master fd.

        Args:
            agent_id: Target agent database ID.
        """
        proc = self._processes.get(agent_id)
        if proc is not None:
            try:
                proc.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, proc.wait),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(
                        f"Agent {agent_id} (PID {proc.pid}) did not "
                        f"exit after SIGTERM, sending SIGKILL"
                    )
                    proc.kill()
                    proc.wait()
            except ProcessLookupError:
                # Process already exited.
                pass
            except Exception as exc:
                self.logger.error(f"Error terminating agent {agent_id}: {exc}")

        # Close the pty master fd.
        master_fd = self._master_fds.pop(agent_id, None)
        if master_fd is not None:
            try:
                os.close(master_fd)
            except OSError:
                pass

        # Remove internal tracking.
        self._processes.pop(agent_id, None)
        self._output_buffers.pop(agent_id, None)

        # Update database record.
        queries.update_agent(agent_id, agtstatus=AGENT_STATUS_TERMINATED)

        self.logger.info(f"Agent {agent_id} terminated")

    async def terminate_all(self) -> None:
        """Terminate all managed agent subprocesses."""
        agent_ids = list(self._processes.keys())
        for agent_id in agent_ids:
            await self.terminate_agent(agent_id)
        self.logger.info(f"Terminated {len(agent_ids)} agent(s)")

    # -----------------------------------------------------------------
    # Completion / error detection
    # -----------------------------------------------------------------

    async def check_agent_complete(self, agent_id: int) -> bool:
        """Check whether an agent has signalled task completion.

        Looks for the configurable safe word in the agent's output
        buffer. Falls back to legacy ``TASK_COMPLETE`` marker.

        Args:
            agent_id: Target agent database ID.

        Returns:
            ``True`` if the completion marker was found.
        """
        from ..settings import get_safe_word

        buf = self._output_buffers.get(agent_id, "")
        safe_word = get_safe_word()
        return safe_word in buf or "TASK_COMPLETE" in buf

    async def check_agent_error(self, agent_id: int) -> str | None:
        """Check whether an agent has signalled a task failure.

        Looks for the ``TASK_FAILED:`` marker in the agent's output
        buffer and extracts the reason.

        Args:
            agent_id: Target agent database ID.

        Returns:
            The error reason string, or ``None`` if no failure marker
            was found.
        """
        buf = self._output_buffers.get(agent_id, "")
        marker = "TASK_FAILED:"
        idx = buf.find(marker)
        if idx == -1:
            return None
        # Extract the reason after the marker
        reason = buf[idx + len(marker):].strip()
        # Take only the first line of the reason
        first_line = reason.split("\n", 1)[0].strip()
        return first_line or "Unknown error"

    # -----------------------------------------------------------------
    # Listing helpers
    # -----------------------------------------------------------------

    def list_agents(self) -> list[dict]:
        """List all agents from the database.

        Returns:
            List of agent dicts.
        """
        return queries.list_agents()

    def get_active_agents(self) -> list[dict]:
        """Return agents with an active status.

        Active statuses are ``idle``, ``working``, and ``waiting``.

        Returns:
            List of agent dicts whose status is active.
        """
        all_agents = queries.list_agents()
        active_statuses = {
            AGENT_STATUS_IDLE,
            AGENT_STATUS_WORKING,
            AGENT_STATUS_WAITING,
        }
        return [a for a in all_agents if a.get("agtstatus") in active_statuses]

    # -----------------------------------------------------------------
    # System prompts
    # -----------------------------------------------------------------

    # Map role constants to prompt file abbreviations.
    _ROLE_ABBREV: dict[str, str] = {
        ROLE_BUSINESS_OWNER: "ba",
        ROLE_BUSINESS_ARCHITECT: "ba",
        ROLE_ENTERPRISE_ARCHITECT: "ea",
        ROLE_SERVICE_ENGINEER: "se",
        ROLE_CODING_AGENT: "ca",
        ROLE_TESTING_AGENT: "ta",
    }

    def _get_system_prompt(
        self,
        role: str,
        project_id: int,
        component_id: int | None,
    ) -> str:
        """Build a system prompt appropriate for the agent's role.

        The prompt includes the project context and, when applicable,
        the component specification so the agent has the minimal context
        it needs to perform its job.

        Args:
            role: Agent role constant.
            project_id: Project database ID.
            component_id: Optional component database ID.

        Returns:
            The system prompt string.
        """
        project = queries.get_project(project_id)
        project_name = project["prjname"] if project else f"Project {project_id}"
        project_desc = (
            project.get("prjdesc") or "No description available."
            if project
            else "No description available."
        )

        component_info = ""
        if component_id is not None:
            component = queries.get_component(component_id)
            if component:
                component_info = (
                    f"\n\n## Assigned Component\n"
                    f"- Name: {component['cmpname']}\n"
                    f"- Level: {component['cmplevel']}\n"
                    f"- Status: {component['cmpstatus']}\n"
                )
                if component.get("cmpdesc"):
                    component_info += f"- Description: {component['cmpdesc']}\n"
                if component.get("cmpspec"):
                    component_info += f"\n### Specification\n{component['cmpspec']}\n"

                # Include connection map for the component.
                connections = queries.get_connections_for_component(component_id)
                if connections:
                    component_info += "\n### Connection Map\n"
                    for conn in connections:
                        component_info += (
                            f"- {conn['from_name']} -> " f"{conn['to_name']}"
                        )
                        if conn.get("condesc"):
                            component_info += f": {conn['condesc']}"
                        component_info += "\n"

                # Include test specs for the component.
                test_specs = queries.list_test_specs(cmpid=component_id)
                if test_specs:
                    component_info += "\n### Test Specifications\n"
                    for ts in test_specs:
                        component_info += f"- {ts['tsname']}"
                        if ts.get("tsdesc"):
                            component_info += f": {ts['tsdesc']}"
                        component_info += "\n"

        header = load_prompt(
            "all_startup_header",
            project_name=project_name,
            project_desc=project_desc,
        )

        abbrev = self._ROLE_ABBREV.get(role)
        if abbrev:
            role_section = load_prompt(f"{abbrev}_startup")
        else:
            role_section = (
                f"## Role: {ROLE_NAMES.get(role, role)}\n\n"
                f"You are a {ROLE_NAMES.get(role, role)} agent.\n"
            )

        timeout_minutes = get_agent_timeout()
        footer = load_prompt(
            "all_startup_footer",
            timeout_minutes=str(timeout_minutes),
        )

        return header + role_section + component_info + footer
