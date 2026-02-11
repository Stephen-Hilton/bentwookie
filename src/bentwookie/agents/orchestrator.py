"""Task-Queue-Driven Orchestrator for BentWookie V2.

Replaces the phase-based dependency engine with a simple poll loop:
  1. Check daemon state (skip if paused)
  2. Poll all agent outputs (PTY reads)
  3. Check working agents for safe word / process death
  4. Expire overdue tasks
  5. Find ready tasks from queue
  6. Assign ready tasks to agents (find/spawn)
  7. Sleep poll_interval
"""

import asyncio
import os
import re
import time

from ..constants import (
    ABBREV_TO_ROLE,
    AGENT_STATUS_ERROR,
    AGENT_STATUS_IDLE,
    AGENT_STATUS_TERMINATED,
    AGENT_STATUS_WORKING,
    DAEMON_STATUS_PAUSED,
    DAEMON_STATUS_RUNNING,
    DAEMON_STATUS_STOPPED,
    ROLE_CONTEXT_SCOPE,
    ROLE_TESTING_AGENT,
    TQ_REQUEST_COLLAB,
)
from ..db import queries
from ..logging_util import BWLogger, get_logger
from ..settings import (
    get_max_concurrent_agents,
    get_max_task_retries,
    get_orchestrator_poll_interval,
    get_safe_word,
    resolve_setting,
)
from .manager import AgentManager
from .prompts import load_prompt


class Orchestrator:
    """Task-queue-driven orchestrator for the BentWookie agent swarm.

    Polls the task_queue table, assigns work to agents, monitors for
    the safe word in agent output, and handles retries.
    """

    def __init__(self) -> None:
        self.manager = AgentManager()
        self.logger: BWLogger = get_logger()
        self._running: bool = False
        self._project_id: int | None = None

    async def start(self, project_id: int) -> None:
        """Start the orchestrator for a project."""
        self._project_id = project_id
        self._running = True
        pid = os.getpid()

        self.logger.info(
            f"Orchestrator starting for project {project_id} (PID {pid})"
        )

        try:
            queries.set_daemon_state(
                pid=pid,
                dsstatus=DAEMON_STATUS_RUNNING,
                dsphase="active",
                dsproject_id=project_id,
            )
            self._seed_workflow()
            await self._main_loop()
        except Exception as exc:
            self.logger.exception(
                f"Orchestrator crashed for project {project_id}: {exc}"
            )
            raise
        finally:
            self._running = False
            queries.set_daemon_state(
                pid=None,
                dsstatus=DAEMON_STATUS_STOPPED,
                dsphase=None,
                dsproject_id=project_id,
            )
            self.logger.info(f"Orchestrator stopped for project {project_id}")

    async def stop(self) -> None:
        """Graceful shutdown: send shutdown prompt, close agents, mark stopped."""
        self.logger.info("Orchestrator stop requested")
        self._running = False

        # Send shutdown prompt to all active agents
        safe_word = get_safe_word()
        shutdown_prompt = load_prompt("all_agent_shutdown", safe_word=safe_word)

        active_agents = queries.list_agents(
            prjid=self._project_id, status=AGENT_STATUS_WORKING
        )
        for agent in active_agents:
            try:
                await self.manager.send_message(agent["agtid"], shutdown_prompt)
            except Exception:
                pass

        # Give agents a moment to save context, then terminate
        await asyncio.sleep(3)
        await self.manager.terminate_all()

        queries.set_daemon_state(
            pid=None,
            dsstatus=DAEMON_STATUS_STOPPED,
            dsphase=None,
            dsproject_id=self._project_id,
        )

    async def pause(self) -> None:
        """Pause the orchestrator."""
        self.logger.info("Orchestrator pausing")
        queries.set_daemon_state(
            pid=os.getpid(),
            dsstatus=DAEMON_STATUS_PAUSED,
            dsphase="active",
            dsproject_id=self._project_id,
        )

    async def resume(self) -> None:
        """Resume from paused state."""
        self.logger.info("Orchestrator resuming")
        queries.set_daemon_state(
            pid=os.getpid(),
            dsstatus=DAEMON_STATUS_RUNNING,
            dsphase="active",
            dsproject_id=self._project_id,
        )

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    async def _main_loop(self) -> None:
        """Core event loop."""
        assert self._project_id is not None

        self.logger.info("Task queue orchestration loop started")

        while self._running:
            poll_interval = get_orchestrator_poll_interval()

            try:
                # 1. Check daemon state
                daemon_state = queries.get_daemon_state()
                if (
                    daemon_state
                    and daemon_state.get("dsstatus") == DAEMON_STATUS_PAUSED
                ):
                    self.logger.debug("Orchestrator is paused, skipping")
                    await asyncio.sleep(poll_interval)
                    continue

                # 2. Poll all agent outputs
                await self.manager.poll_all_outputs()

                # 3. Check working agents for safe word / process death
                await self._check_completions()

                # 4. Expire overdue tasks
                expired = queries.expire_overdue_tasks(self._project_id)
                if expired:
                    self.logger.info(f"Expired {expired} overdue task(s)")

                # 5. Find ready tasks
                ready_tasks = queries.find_ready_tasks(self._project_id)

                # 6. Assign ready tasks to agents
                if ready_tasks:
                    assigned = await self._assign_tasks(ready_tasks)
                    if assigned > 0:
                        self.logger.info(f"Assigned {assigned} task(s)")

                # 7. Update heartbeat
                queries.update_daemon_heartbeat()

            except asyncio.CancelledError:
                self.logger.info("Main loop cancelled")
                break
            except Exception as exc:
                self.logger.exception(f"Error in orchestration loop: {exc}")
                await asyncio.sleep(poll_interval)
                continue

            await asyncio.sleep(poll_interval)

        self.logger.info("Task queue orchestration loop exited")

    # ------------------------------------------------------------------
    # Completion checking
    # ------------------------------------------------------------------

    async def _check_completions(self) -> None:
        """Check working agents for safe word or process death."""
        assert self._project_id is not None

        safe_word = get_safe_word()

        working_agents = queries.list_agents(
            prjid=self._project_id, status=AGENT_STATUS_WORKING
        )

        for agent in working_agents:
            agent_id = agent["agtid"]
            task = queries.get_active_task_for_agent(agent_id)
            if not task:
                continue

            buf = self.manager.get_agent_output_buffer(agent_id)

            # Check for safe word
            if safe_word in buf:
                await self._handle_task_complete(agent, task, buf)
                continue

            # Check if process died
            if not self.manager.is_agent_alive(agent_id):
                await self._handle_no_safe_word(agent, task)
                continue

            # Check for TASK_FAILED marker
            error = await self.manager.check_agent_error(agent_id)
            if error:
                self.logger.error(
                    f"Task {task['tqid']} failed on agent {agent_id}: {error}"
                )
                queries.fail_task(task["tqid"], error)
                queries.update_agent(
                    agent_id,
                    agtstatus=AGENT_STATUS_ERROR,
                    agterror=error,
                    agtcmpid=None,
                )
                await self.manager.terminate_agent(agent_id)

    async def _handle_task_complete(
        self, agent: dict, task: dict, output: str
    ) -> None:
        """Handle safe word detection - task is complete."""
        agent_id = agent["agtid"]
        tqid = task["tqid"]

        self.logger.info(
            f"Task {tqid} completed by agent {agent_id} "
            f"({agent.get('agtname', 'unknown')})"
        )

        # Parse follow-up tasks from output
        followups = self._parse_followup_tasks(output)
        if followups:
            assert self._project_id is not None
            for fu in followups:
                fu_id = queries.enqueue_task(
                    prjid=self._project_id,
                    tqagent_type=fu["agent_type"],
                    tqinstructions=fu["instructions"],
                    tqauthor=agent.get("agtname", "agent"),
                    tqcmpid=fu.get("cmpid"),
                    tqpriority=fu.get("priority", 5),
                )
                self.logger.info(
                    f"Auto-enqueued follow-up task {fu_id} "
                    f"(type={fu['agent_type']}) from agent {agent_id}"
                )

        # Save scoped context
        role = agent.get("agtrole", "")
        scope_level = ROLE_CONTEXT_SCOPE.get(role, "request")
        scope_id = task.get("tqcmpid") or self._project_id or 0
        summary = output[-2000:]  # Last 2KB as context
        queries.save_scoped_context(
            agtid=agent_id,
            scope_level=scope_level,
            scope_id=scope_id,
            tqid=tqid,
            context=summary,
            cmpid=task.get("tqcmpid"),
        )

        # Mark task complete
        queries.complete_task(tqid, result=summary)

        # Reset agent to idle (or terminate testing agents)
        if role == ROLE_TESTING_AGENT:
            await self.manager.terminate_agent(agent_id)
        else:
            queries.update_agent(
                agent_id,
                agtstatus=AGENT_STATUS_IDLE,
                agtcmpid=None,
            )
            # Clear the output buffer for next task
            self.manager._output_buffers[agent_id] = ""

    async def _handle_no_safe_word(self, agent: dict, task: dict) -> None:
        """Handle agent death without safe word - retry or fail."""
        agent_id = agent["agtid"]
        tqid = task["tqid"]
        retry_count = task.get("tqretry_count", 0)
        max_retries = task.get("tqmax_retries") or get_max_task_retries()

        self.logger.warning(
            f"Agent {agent_id} died without safe word for task {tqid} "
            f"(retry {retry_count}/{max_retries})"
        )

        # Clean up dead agent
        await self.manager.terminate_agent(agent_id)

        if retry_count >= max_retries:
            queries.fail_task(tqid, "Agent died without safe word after max retries")
            self.logger.error(f"Task {tqid} permanently failed after {max_retries} retries")
        else:
            # Prepend reissue warning to instructions
            safe_word = get_safe_word()
            warning = load_prompt("all_reissue_warning", safe_word=safe_word)
            original = task.get("tqinstructions", "")
            queries.update_task(
                tqid,
                tqstatus="pending",
                tqagent_id=None,
                tqprevious_work=warning + "\n\n" + original,
                tqretry_count=retry_count + 1,
            )
            self.logger.info(f"Task {tqid} requeued for retry (attempt {retry_count + 1})")

    # ------------------------------------------------------------------
    # Task assignment
    # ------------------------------------------------------------------

    async def _assign_tasks(self, ready_tasks: list[dict]) -> int:
        """Assign ready tasks to idle or newly spawned agents."""
        assert self._project_id is not None

        max_agents = get_max_concurrent_agents()
        assigned_count = 0

        for task in ready_tasks:
            # Check global concurrency ceiling
            active_count = queries.count_active_agents(self._project_id)
            if active_count >= max_agents:
                self.logger.debug(
                    f"Agent ceiling reached ({active_count}/{max_agents})"
                )
                break

            agent_type = task["tqagent_type"]
            agent_name = task.get("tqagent_name")
            agent = await self._get_or_spawn_agent(agent_type, agent_name)

            if agent is None:
                continue

            # Mark task assigned
            queries.assign_task(task["tqid"], agent["agtid"])

            # Update agent to working
            queries.update_agent(
                agent["agtid"],
                agtstatus=AGENT_STATUS_WORKING,
                agtcmpid=task.get("tqcmpid"),
            )

            # Build enriched prompt
            prompt = self._enrich_prompt(task)

            # Send to agent
            await self.manager.send_message(agent["agtid"], prompt)

            # Transition to in_progress
            queries.update_task(task["tqid"], tqstatus="in_progress")

            self.logger.info(
                f"Assigned task {task['tqid']} to agent {agent['agtid']} "
                f"({agent.get('agtname', 'unknown')}, type={agent_type})"
            )
            assigned_count += 1

        return assigned_count

    async def _get_or_spawn_agent(
        self, role: str, agent_name: str | None = None
    ) -> dict | None:
        """Find an idle agent of the given role, or spawn a new one."""
        assert self._project_id is not None

        # If specific name requested, find that agent
        if agent_name:
            all_agents = queries.list_agents(prjid=self._project_id, role=role)
            for a in all_agents:
                if a.get("agtname") == agent_name:
                    if a.get("agtstatus") == AGENT_STATUS_IDLE:
                        return a
                    return None  # Agent exists but busy

        # Find an idle agent of this role
        idle_agents = queries.list_agents(
            prjid=self._project_id, status=AGENT_STATUS_IDLE, role=role
        )
        if idle_agents:
            return idle_agents[0]

        # Check per-type limit
        per_type_max = resolve_setting("max_agents", agent_role=role)
        if per_type_max is not None:
            role_agents = queries.list_agents(prjid=self._project_id, role=role)
            active_role = sum(
                1 for a in role_agents
                if a.get("agtstatus") in ("idle", "working", "waiting")
            )
            if active_role >= int(per_type_max):
                self.logger.debug(
                    f"Per-type limit reached for {role} ({active_role}/{per_type_max})"
                )
                return None

        # Spawn new agent if under global ceiling
        max_agents = get_max_concurrent_agents()
        active_count = queries.count_active_agents(self._project_id)
        if active_count >= max_agents:
            return None

        agent_id = await self.manager.spawn_agent(
            project_id=self._project_id, role=role
        )
        if agent_id is None:
            return None

        return queries.get_agent(agent_id)

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _enrich_prompt(self, task: dict) -> str:
        """Build enriched prompt: prefix + instructions + library + swarm + context."""
        assert self._project_id is not None

        safe_word = get_safe_word()
        parts: list[str] = []

        # Task prefix with safe word
        prefix = load_prompt("all_task_prefix", safe_word=safe_word)
        parts.append(prefix)

        # Previous work / reissue warning if present
        if task.get("tqprevious_work"):
            parts.append(task["tqprevious_work"])

        # Main instructions
        parts.append(task["tqinstructions"])

        # Library summary
        library = queries.build_task_library(self._project_id)
        if library:
            parts.append(library)

        # Swarm summary
        swarm = queries.build_swarm_summary(self._project_id)
        if swarm:
            parts.append(swarm)

        # Collaboration suffix
        if task.get("tqrequest_type") == TQ_REQUEST_COLLAB:
            collab = load_prompt("all_collab_suffix")
            parts.append(collab)

        # Restore scoped context
        role = task.get("tqagent_type", "")
        scope_level = ROLE_CONTEXT_SCOPE.get(role, "request")
        scope_id = task.get("tqcmpid") or self._project_id
        prior = queries.get_context_for_scope(scope_level, scope_id)
        if prior:
            parts.append(f"\n## Prior Context\n{prior['accontext']}\n")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Follow-up task parsing
    # ------------------------------------------------------------------

    def _parse_followup_tasks(self, output: str) -> list[dict]:
        """Parse TASK_QUEUE_START...TASK_QUEUE_END blocks from agent output."""
        pattern = r"TASK_QUEUE_START\s*\n(.*?)TASK_QUEUE_END"
        blocks = re.findall(pattern, output, re.DOTALL)

        tasks: list[dict] = []
        for block in blocks:
            # Split by --- separator for multiple tasks
            entries = re.split(r"\n---\s*\n", block.strip())
            for entry in entries:
                task = self._parse_single_task_entry(entry.strip())
                if task:
                    tasks.append(task)

        return tasks

    def _parse_single_task_entry(self, entry: str) -> dict | None:
        """Parse a single task entry from a TASK_QUEUE block."""
        if not entry:
            return None

        result: dict = {}
        current_key = None
        current_lines: list[str] = []

        for line in entry.split("\n"):
            # Check for key: value pattern
            match = re.match(r"^(\w+):\s*(.*)", line)
            if match:
                # Save previous key
                if current_key and current_lines:
                    result[current_key] = "\n".join(current_lines).strip()
                current_key = match.group(1).strip()
                value = match.group(2).strip()
                current_lines = [value] if value and value != "|" else []
            else:
                # Continuation line
                stripped = line.lstrip()
                if stripped and current_key:
                    current_lines.append(stripped)

        # Save last key
        if current_key and current_lines:
            result[current_key] = "\n".join(current_lines).strip()

        # Validate required fields
        agent_type_raw = result.get("agent_type", "").strip()
        instructions = result.get("instructions", "").strip()

        if not agent_type_raw or not instructions:
            return None

        # Map abbreviation to full role name
        agent_type = ABBREV_TO_ROLE.get(agent_type_raw, agent_type_raw)

        priority = 5
        try:
            priority = int(result.get("priority", "5"))
        except ValueError:
            pass

        return {
            "agent_type": agent_type,
            "instructions": instructions,
            "priority": priority,
            "cmpid": None,  # Could be resolved from component name in future
        }

    # ------------------------------------------------------------------
    # Workflow seeding
    # ------------------------------------------------------------------

    def _seed_workflow(self) -> None:
        """If the task queue is empty, seed it with the first workflow task."""
        assert self._project_id is not None

        existing = queries.list_tasks(prjid=self._project_id, limit=1)
        if existing:
            return  # Queue already has tasks

        self.logger.info(
            f"Seeding workflow for project {self._project_id} "
            f"(task 1: BA interview placeholder)"
        )
        queries.enqueue_task(
            prjid=self._project_id,
            tqagent_type="business_architect",
            tqinstructions="Conduct business owner interview to capture project requirements.",
            tqauthor="system",
            tqworkflow_step=1,
            tqpriority=1,
        )
