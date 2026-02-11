"""Orchestrator for the BentWookie V2 agent swarm.

Manages the main event loop that coordinates agent work assignment,
message delivery, task completion handling, and the rework protocol.
"""

import asyncio
import os
import time

from ..constants import (
    AGENT_STATUS_ERROR,
    AGENT_STATUS_IDLE,
    AGENT_STATUS_WORKING,
    BUILD_STATUS_ASSIGNED,
    BUILD_STATUS_COMPLETE,
    BUILD_STATUS_ERROR,
    BUILD_STATUS_IN_PROGRESS,
    BUILD_STATUS_PENDING,
    BUILD_STATUS_REWORK,
    BUILD_TASK_ASSEMBLE,
    BUILD_TASK_IMPLEMENT,
    BUILD_TASK_INTEGRATE,
    BUILD_TASK_TEST,
    COMPONENT_STATUS_BUILDING,
    COMPONENT_STATUS_BUILT,
    COMPONENT_STATUS_ERROR,
    DAEMON_STATUS_PAUSED,
    DAEMON_STATUS_RUNNING,
    DAEMON_STATUS_STOPPED,
    INTERVIEW_STATUS_COMPLETE,
    INTERVIEW_TYPE_BO,
    INTERVIEW_TYPE_EA,
    LEVEL_COMPONENT,
    LEVEL_FUNCTION,
    LEVEL_SERVICE,
    NEXT_PHASE,
    PHASE_BUILD,
    PHASE_COMPLETE,
    PHASE_DEFINE,
    PHASE_DESIGN,
    PHASE_VALIDATE,
    ROLE_CODING_AGENT,
    ROLE_ENTERPRISE_ARCHITECT,
    ROLE_SERVICE_ENGINEER,
    ROLE_TESTING_AGENT,
)
from ..db import queries
from ..logging_util import BWLogger, get_logger
from ..settings import (
    get_agent_timeout,
    get_max_concurrent_agents,
    get_phase_timeout,
    get_poll_interval,
    resolve_setting,
)
from .manager import AgentManager
from .message_queue import MessageQueue
from .prompts import load_prompt


class Orchestrator:
    """Main orchestration loop for the BentWookie agent swarm.

    Coordinates agent spawning, work assignment based on the dependency
    graph, message delivery, completion handling, and the rework protocol.
    """

    def __init__(self) -> None:
        """Initialize the orchestrator.

        Sets up the agent manager, message queue, logger, and internal
        state tracking for the main event loop.
        """
        self.manager = AgentManager()
        self.message_queue = MessageQueue(self.manager)
        self.logger: BWLogger = get_logger()
        self._running: bool = False
        self._project_id: int | None = None

    async def start(self, project_id: int) -> None:
        """Start the orchestrator for a given project.

        Sets the daemon state to 'running' in the database, then enters
        the main event loop. On exit (normal or exceptional), the daemon
        state is set to 'stopped'.

        Args:
            project_id: The project ID to orchestrate.
        """
        self._project_id = project_id
        self._running = True
        pid = os.getpid()

        self.logger.info(
            f"Orchestrator starting for project {project_id} "
            f"(PID {pid})"
        )

        try:
            queries.set_daemon_state(
                pid=pid,
                dsstatus=DAEMON_STATUS_RUNNING,
                dsphase="build",
                dsproject_id=project_id,
            )
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
            self.logger.info(
                f"Orchestrator stopped for project {project_id}"
            )

    async def stop(self) -> None:
        """Stop the orchestrator gracefully.

        Sets the running flag to False so the main loop exits on its
        next iteration, terminates all managed agents, and marks the
        daemon as stopped in the database.
        """
        self.logger.info("Orchestrator stop requested")
        self._running = False

        await self.manager.terminate_all()

        queries.set_daemon_state(
            pid=None,
            dsstatus=DAEMON_STATUS_STOPPED,
            dsphase=None,
            dsproject_id=self._project_id,
        )

    async def pause(self) -> None:
        """Pause the orchestrator.

        Sets the daemon state to 'paused'. The main loop will continue
        running but will skip work assignment and completion checks
        until resumed.
        """
        self.logger.info("Orchestrator pausing")
        queries.set_daemon_state(
            pid=os.getpid(),
            dsstatus=DAEMON_STATUS_PAUSED,
            dsphase="build",
            dsproject_id=self._project_id,
        )

    async def resume(self) -> None:
        """Resume the orchestrator from a paused state.

        Sets the daemon state back to 'running' so the main loop
        resumes normal work assignment and processing.
        """
        self.logger.info("Orchestrator resuming")
        queries.set_daemon_state(
            pid=os.getpid(),
            dsstatus=DAEMON_STATUS_RUNNING,
            dsphase="build",
            dsproject_id=self._project_id,
        )

    async def _main_loop(self) -> None:
        """Core event loop for the orchestrator.

        While running, this loop repeatedly:
        1. Checks the daemon state (skips work if paused).
        2. Polls all agent outputs via the agent manager.
        3. Delivers pending messages via the message queue.
        4. Checks for urgent messages on all agents.
        5. Finds ready work from the dependency graph.
        6. Assigns work to idle agents (or spawns new ones).
        7. Checks for completed or failed tasks.
        8. Handles rework tasks (creates amendments, routes to
           architect or service engineer).
        9. Checks for phase advancement.
        10. Updates the daemon heartbeat.
        11. Sleeps for the configured poll interval.
        """
        assert self._project_id is not None

        self.logger.info("Main orchestration loop started")

        while self._running:
            try:
                poll_interval = get_poll_interval()

                # ----------------------------------------------------------
                # 1. Check daemon state -- skip work assignment if paused
                # ----------------------------------------------------------
                daemon_state = queries.get_daemon_state()
                if (
                    daemon_state
                    and daemon_state.get("dsstatus") == DAEMON_STATUS_PAUSED
                ):
                    self.logger.debug("Orchestrator is paused, skipping")
                    await asyncio.sleep(poll_interval)
                    continue

                # ----------------------------------------------------------
                # 2. Poll agent outputs
                # ----------------------------------------------------------
                await self.manager.poll_all_outputs()

                # ----------------------------------------------------------
                # 3. Deliver pending normal messages
                # ----------------------------------------------------------
                await self.message_queue.deliver_all_pending()

                # ----------------------------------------------------------
                # 4. Check for urgent messages on all agents
                # ----------------------------------------------------------
                active_agents = queries.list_agents(
                    prjid=self._project_id,
                    status=AGENT_STATUS_WORKING,
                )
                for agent in active_agents:
                    await self.message_queue.check_urgent(
                        agent["agtid"]
                    )

                # ----------------------------------------------------------
                # 5. Find ready work
                # ----------------------------------------------------------
                ready_tasks = await self._find_ready_work(
                    self._project_id
                )

                # ----------------------------------------------------------
                # 6. Assign work to idle agents
                # ----------------------------------------------------------
                if ready_tasks:
                    assigned = await self._assign_work(ready_tasks)
                    if assigned > 0:
                        self.logger.info(
                            f"Assigned {assigned} task(s) to agents"
                        )

                # ----------------------------------------------------------
                # 7. Check for completed / failed tasks
                # ----------------------------------------------------------
                await self._check_completions()

                # ----------------------------------------------------------
                # 8. Handle rework tasks
                # ----------------------------------------------------------
                await self._handle_rework_tasks()

                # ----------------------------------------------------------
                # 9. Check for phase advancement
                # ----------------------------------------------------------
                await self._advance_phase()

                # ----------------------------------------------------------
                # 10. Update heartbeat
                # ----------------------------------------------------------
                queries.update_daemon_heartbeat()

            except asyncio.CancelledError:
                self.logger.info("Main loop cancelled")
                break
            except Exception as exc:
                self.logger.exception(
                    f"Error in orchestration loop: {exc}"
                )
                # Avoid tight error loops
                await asyncio.sleep(poll_interval)
                continue

            # ----------------------------------------------------------
            # 11. Sleep until next iteration
            # ----------------------------------------------------------
            await asyncio.sleep(poll_interval)

        self.logger.info("Main orchestration loop exited")

    # ------------------------------------------------------------------
    # Work discovery
    # ------------------------------------------------------------------

    async def _find_ready_work(
        self, project_id: int
    ) -> list[dict]:
        """Find build tasks that are ready to be assigned.

        A task is "ready" when:
        - Its component's dependencies are all satisfied (status in
          'built' or 'tested'), as determined by
          ``queries.find_ready_components()``.
        - It has a corresponding build task in 'pending' status.

        Args:
            project_id: The project to search within.

        Returns:
            List of build task dicts that are ready for assignment.
        """
        ready_components = queries.find_ready_components(project_id)
        if not ready_components:
            return []

        ready_cmpids = {c["cmpid"] for c in ready_components}

        pending_tasks = queries.list_build_tasks(
            prjid=project_id, status=BUILD_STATUS_PENDING
        )

        ready_tasks = [
            task
            for task in pending_tasks
            if task["cmpid"] in ready_cmpids
        ]

        if ready_tasks:
            self.logger.debug(
                f"Found {len(ready_tasks)} ready task(s) across "
                f"{len(ready_cmpids)} unblocked component(s)"
            )

        return ready_tasks

    # ------------------------------------------------------------------
    # Work assignment
    # ------------------------------------------------------------------

    async def _assign_work(self, tasks: list[dict]) -> int:
        """Assign ready tasks to idle or newly spawned agents.

        For each task, the orchestrator:
        1. Determines the required agent role.
        2. Looks for an idle agent of that role, or spawns a new one
           if the concurrency ceiling allows.
        3. Updates the build task status to 'assigned' and sends the
           task prompt to the agent.

        Args:
            tasks: List of ready build task dicts.

        Returns:
            Number of tasks successfully assigned.
        """
        assert self._project_id is not None

        max_agents = get_max_concurrent_agents()
        assigned_count = 0

        for task in tasks:
            # Check global concurrency ceiling
            active_count = queries.count_active_agents(self._project_id)
            if active_count >= max_agents:
                self.logger.debug(
                    f"Agent ceiling reached ({active_count}/{max_agents})"
                )
                break

            role = self._get_role_for_task(task)
            agent = await self._get_or_spawn_agent(role)

            if agent is None:
                self.logger.warning(
                    f"Could not obtain agent for task {task['btid']} "
                    f"(role={role})"
                )
                continue

            # Mark task as assigned
            queries.update_build_task(
                task["btid"],
                agtid=agent["agtid"],
                btstatus=BUILD_STATUS_ASSIGNED,
            )

            # Update component status to 'building'
            queries.update_component(
                task["cmpid"], cmpstatus=COMPONENT_STATUS_BUILDING
            )

            # Update agent to working, link to component
            queries.update_agent(
                agent["agtid"],
                agtstatus=AGENT_STATUS_WORKING,
                agtcmpid=task["cmpid"],
            )

            # Build and send the prompt, including relevant saved context
            prompt = task.get("btprompt") or self._build_task_prompt(
                task
            )

            # Include saved context from prior work on this component
            prior_context = queries.get_latest_agent_context(agent["agtid"])
            if prior_context and prior_context.get("cmpid") == task["cmpid"]:
                prompt += (
                    "\n\n## Prior Context\n"
                    f"{prior_context['accontext']}\n"
                )

            await self.manager.send_message(agent["agtid"], prompt)

            # Transition task to in_progress
            queries.update_build_task(
                task["btid"], btstatus=BUILD_STATUS_IN_PROGRESS
            )

            self.logger.info(
                f"Assigned task {task['btid']} "
                f"({task.get('cmpname', 'unknown')}/{task['bttype']}) "
                f"to agent {agent['agtid']} ({role})"
            )
            assigned_count += 1

        return assigned_count

    async def _get_or_spawn_agent(
        self, role: str
    ) -> dict | None:
        """Find an idle agent of the given role, or spawn a new one.

        Args:
            role: The agent role to look for (e.g. 'coding_agent').

        Returns:
            Agent dict if one was found or spawned, None otherwise.
        """
        assert self._project_id is not None

        # Look for an existing idle agent of this role
        idle_agents = queries.list_agents(
            prjid=self._project_id,
            status=AGENT_STATUS_IDLE,
            role=role,
        )
        if idle_agents:
            return idle_agents[0]

        # Check per-type limit via hierarchical settings
        per_type_max = resolve_setting("max_agents", agent_role=role)
        if per_type_max is not None:
            role_agents = queries.list_agents(
                prjid=self._project_id, role=role
            )
            active_role = sum(
                1 for a in role_agents
                if a.get("agtstatus") in ("idle", "working", "waiting")
            )
            if active_role >= int(per_type_max):
                self.logger.debug(
                    f"Per-type limit reached for {role} "
                    f"({active_role}/{per_type_max})"
                )
                return None

        # Spawn a new agent if under the global ceiling
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
    # Completion / failure handling
    # ------------------------------------------------------------------

    async def _check_completions(self) -> None:
        """Check for agents that have finished or timed out.

        Iterates through all working agents and checks:
        - Whether the agent has produced a completion marker in its
          output (indicating successful task completion).
        - Whether the agent task has exceeded the configured timeout,
          in which case it is treated as a failure.

        Delegates to ``_handle_completion`` or ``_handle_failure``
        accordingly.
        """
        assert self._project_id is not None

        default_timeout = get_agent_timeout()
        now = time.time()

        working_agents = queries.list_agents(
            prjid=self._project_id,
            status=AGENT_STATUS_WORKING,
        )

        for agent in working_agents:
            agent_id = agent["agtid"]

            # Find the in-progress task for this agent
            in_progress = queries.list_build_tasks(
                prjid=self._project_id,
                status=BUILD_STATUS_IN_PROGRESS,
                agtid=agent_id,
            )
            if not in_progress:
                continue

            task = in_progress[0]
            task_id = task["btid"]

            # Check for completion via the agent manager
            is_complete = await self.manager.check_agent_complete(
                agent_id
            )
            if is_complete:
                await self._handle_completion(agent_id, task_id)
                continue

            # Check for errors via the agent manager
            error = await self.manager.check_agent_error(agent_id)
            if error:
                await self._handle_failure(agent_id, task_id, error)
                continue

            # Check for timeout (using hierarchical settings)
            agent_role = agent.get("agtrole", "")
            timeout_minutes = resolve_setting(
                "agent_timeout",
                agent_id=agent_id,
                agent_role=agent_role,
            ) or default_timeout
            timeout_seconds = int(timeout_minutes) * 60

            started = agent.get("agttouchts")
            if started:
                try:
                    if hasattr(started, "timestamp"):
                        started_ts = started.timestamp()
                    else:
                        from datetime import datetime

                        started_ts = datetime.fromisoformat(
                            str(started)
                        ).timestamp()
                    elapsed = now - started_ts
                    if elapsed > timeout_seconds:
                        await self._handle_failure(
                            agent_id,
                            task_id,
                            f"Agent timed out after "
                            f"{timeout_minutes} minutes",
                        )
                except (ValueError, TypeError, OSError):
                    pass  # Skip timeout check on parse errors

    async def _handle_completion(
        self, agent_id: int, task_id: int
    ) -> None:
        """Handle successful completion of a build task.

        Marks the build task as 'complete', updates the component
        status to 'built', resets the agent to 'idle', and logs the
        event. Also checks whether any downstream tasks are now
        unblocked.

        Args:
            agent_id: The agent that completed the task.
            task_id: The build task that was completed.
        """
        task = queries.get_build_task(task_id)
        if not task:
            self.logger.error(
                f"Completion handler: task {task_id} not found"
            )
            return

        # Mark task complete
        queries.update_build_task(
            task_id, btstatus=BUILD_STATUS_COMPLETE
        )

        # Update component status
        queries.update_component(
            task["cmpid"], cmpstatus=COMPONENT_STATUS_BUILT
        )

        # Save agent context before clearing
        output_buf = self.manager.get_agent_output_buffer(agent_id)
        if output_buf:
            summary = output_buf[-2000:]  # Last 2KB as context summary
            queries.save_agent_context(
                agtid=agent_id,
                cmpid=task["cmpid"],
                btid=task_id,
                accontext=summary,
                acstatus="complete",
            )

        # Reset agent to idle
        queries.update_agent(
            agent_id,
            agtstatus=AGENT_STATUS_IDLE,
            agtcmpid=None,
        )

        self.logger.info(
            f"Task {task_id} completed by agent {agent_id} "
            f"(component: {task.get('cmpname', 'unknown')})"
        )

        # Check if newly unblocked work exists (will be picked up
        # on the next loop iteration via _find_ready_work)
        if self._project_id:
            dependents = queries.get_dependents(task["cmpid"])
            if dependents:
                self.logger.info(
                    f"Completion of component {task['cmpid']} may "
                    f"unblock {len(dependents)} dependent(s)"
                )

    async def _handle_failure(
        self, agent_id: int, task_id: int, error: str
    ) -> None:
        """Handle a failed build task.

        Marks the build task as 'error' with the error message, sets
        the component status to 'error', marks the agent as 'error',
        and implements the rework protocol:

        - If the failing agent is a coding agent, notify the service
          engineer for the parent service.
        - If the failing agent is a service engineer, notify the
          enterprise architect.
        - If the issue appears structural, create a design amendment.

        Args:
            agent_id: The agent that failed.
            task_id: The build task that failed.
            error: Description of the failure.
        """
        task = queries.get_build_task(task_id)
        if not task:
            self.logger.error(
                f"Failure handler: task {task_id} not found"
            )
            return

        self.logger.error(
            f"Task {task_id} failed on agent {agent_id}: {error}"
        )

        # Mark task as error
        queries.update_build_task(
            task_id, btstatus=BUILD_STATUS_ERROR, bterror=error
        )

        # Update component status
        queries.update_component(
            task["cmpid"], cmpstatus=COMPONENT_STATUS_ERROR
        )

        # Mark agent as error
        queries.update_agent(
            agent_id,
            agtstatus=AGENT_STATUS_ERROR,
            agterror=error,
            agtcmpid=None,
        )

        # Terminate the agent's shell process
        await self.manager.terminate_agent(agent_id)

        # ----------------------------------------------------------
        # Rework protocol
        # ----------------------------------------------------------
        agent = queries.get_agent(agent_id)
        if not agent:
            return

        agent_role = agent.get("agtrole", "")

        if agent_role == ROLE_CODING_AGENT:
            # Notify the service engineer for the parent service
            await self._notify_service_engineer(task, error)

        elif agent_role == ROLE_SERVICE_ENGINEER:
            # Escalate to the enterprise architect
            await self._notify_architect(task, error)

        # If the error looks structural, create a design amendment
        structural_keywords = [
            "dependency",
            "interface",
            "contract",
            "schema",
            "architecture",
            "structural",
            "connection",
            "integration",
        ]
        error_lower = error.lower()
        if any(kw in error_lower for kw in structural_keywords):
            queries.create_design_amendment(
                cmpid=task["cmpid"],
                dareason=error,
                dachange=(
                    "Structural issue detected during build. "
                    "Requires architect review."
                ),
                agtid=agent_id,
            )
            self.logger.info(
                f"Design amendment created for component "
                f"{task['cmpid']} due to structural error"
            )

    # ------------------------------------------------------------------
    # Rework protocol helpers
    # ------------------------------------------------------------------

    async def _notify_service_engineer(
        self, task: dict, error: str
    ) -> None:
        """Notify the service engineer about a coding agent failure.

        Finds the service engineer responsible for the service that
        contains the failed component and sends a normal message.

        Args:
            task: The failed build task dict.
            error: Description of the failure.
        """
        assert self._project_id is not None

        # Walk up to find the service-level component
        component = queries.get_component(task["cmpid"])
        if not component:
            return

        ancestors = queries.get_component_ancestors(task["cmpid"])
        service_cmpid = None
        for anc in ancestors:
            if anc.get("cmplevel") == "service":
                service_cmpid = anc["cmpid"]
                break

        # Find the service engineer for this service
        se_agents = queries.list_agents(
            prjid=self._project_id,
            role=ROLE_SERVICE_ENGINEER,
        )
        target_se = None
        for se in se_agents:
            if se.get("agtcmpid") == service_cmpid:
                target_se = se
                break

        # Fall back to any active service engineer
        if target_se is None and se_agents:
            for se in se_agents:
                if se.get("agtstatus") in (
                    AGENT_STATUS_IDLE,
                    AGENT_STATUS_WORKING,
                ):
                    target_se = se
                    break

        if target_se:
            queries.create_message(
                to_agtid=target_se["agtid"],
                from_agtid=None,
                msgbody=load_prompt(
                    "ca_rework_notify",
                    cmp_name=component.get("cmpname", "unknown"),
                    task_id=str(task["btid"]),
                    error=error,
                ),
                msgtype="normal",
            )
            self.logger.info(
                f"Notified service engineer {target_se['agtid']} "
                f"about failure on task {task['btid']}"
            )

    async def _notify_architect(
        self, task: dict, error: str
    ) -> None:
        """Escalate a service engineer failure to the architect.

        Sends an urgent message to the enterprise architect about a
        structural or integration-level failure.

        Args:
            task: The failed build task dict.
            error: Description of the failure.
        """
        assert self._project_id is not None

        component = queries.get_component(task["cmpid"])
        cmp_name = component.get("cmpname", "unknown") if component else "unknown"

        arch_agents = queries.list_agents(
            prjid=self._project_id,
            role=ROLE_ENTERPRISE_ARCHITECT,
        )

        if arch_agents:
            architect = arch_agents[0]
            queries.create_message(
                to_agtid=architect["agtid"],
                from_agtid=None,
                msgbody=load_prompt(
                    "ea_escalation_notify",
                    cmp_name=cmp_name,
                    task_id=str(task["btid"]),
                    error=error,
                ),
                msgtype="urgent",
            )
            self.logger.info(
                f"Escalated failure on task {task['btid']} to "
                f"architect {architect['agtid']}"
            )

    # ------------------------------------------------------------------
    # Phase progression
    # ------------------------------------------------------------------

    async def _advance_phase(self) -> None:
        """Check if the current phase is complete and advance the project.

        Phase transition rules:
        - define -> design: Both BO and EA interviews are complete.
        - design -> validate: All service-level components have build plans.
        - validate -> build: All component/function-level test specs are
          finalized (status = 'approved').
        - build -> complete: All build tasks are complete (none pending,
          in_progress, assigned, blocked, or rework).
        """
        assert self._project_id is not None

        project = queries.get_project(self._project_id)
        if not project:
            self.logger.error(
                f"Cannot advance phase: project {self._project_id} "
                f"not found"
            )
            return

        current_phase = project.get("prjphase", "")
        next_phase = NEXT_PHASE.get(current_phase)

        if next_phase is None:
            # Already at terminal phase (complete)
            return

        phase_complete = False

        if current_phase == PHASE_DEFINE:
            phase_complete = self._is_define_complete()

        elif current_phase == PHASE_DESIGN:
            phase_complete = self._is_design_complete()

        elif current_phase == PHASE_VALIDATE:
            phase_complete = self._is_validate_complete()

        elif current_phase == PHASE_BUILD:
            phase_complete = self._is_build_complete()

        if phase_complete:
            queries.update_project(
                self._project_id, prjphase=next_phase
            )

            # Update daemon state to reflect the new phase
            queries.set_daemon_state(
                pid=os.getpid(),
                dsstatus=DAEMON_STATUS_RUNNING,
                dsphase=next_phase,
                dsproject_id=self._project_id,
            )

            self.logger.info(
                f"Project {self._project_id} advanced from "
                f"'{current_phase}' to '{next_phase}'"
            )

    def _is_define_complete(self) -> bool:
        """Check if the define phase is complete.

        Both Business Owner and Enterprise Architect interviews must
        have status 'complete'.

        Returns:
            True if both interviews are complete.
        """
        assert self._project_id is not None

        interviews = queries.list_interviews(prjid=self._project_id)
        if not interviews:
            return False

        bo_complete = False
        ea_complete = False

        for itv in interviews:
            itv_type = itv.get("itvtype", "")
            itv_status = itv.get("itvstatus", "")

            if (
                itv_type == INTERVIEW_TYPE_BO
                and itv_status == INTERVIEW_STATUS_COMPLETE
            ):
                bo_complete = True
            elif (
                itv_type == INTERVIEW_TYPE_EA
                and itv_status == INTERVIEW_STATUS_COMPLETE
            ):
                ea_complete = True

        return bo_complete and ea_complete

    def _is_design_complete(self) -> bool:
        """Check if the design phase is complete.

        All service-level components must have an approved build plan.

        Returns:
            True if all services have build plans.
        """
        assert self._project_id is not None

        services = queries.list_components(
            prjid=self._project_id, level=LEVEL_SERVICE
        )
        if not services:
            return False

        for svc in services:
            plan = queries.get_build_plan(svc["cmpid"])
            if not plan or plan.get("bpstatus") not in (
                "approved",
                "final",
            ):
                return False

        return True

    def _is_validate_complete(self) -> bool:
        """Check if the validate phase is complete.

        All component-level and function-level items must have at least
        one test spec with status 'approved'.

        Returns:
            True if all component/function test specs are finalized.
        """
        assert self._project_id is not None

        buildable = []
        for level in (LEVEL_COMPONENT, LEVEL_FUNCTION):
            buildable.extend(
                queries.list_components(
                    prjid=self._project_id, level=level
                )
            )

        if not buildable:
            return False

        for cmp in buildable:
            specs = queries.list_test_specs(cmpid=cmp["cmpid"])
            if not specs:
                return False
            # At least one spec must be approved/finalized
            has_approved = any(
                ts.get("tsstatus") in ("approved", "final")
                for ts in specs
            )
            if not has_approved:
                return False

        return True

    def _is_build_complete(self) -> bool:
        """Check if the build phase is complete.

        All build tasks must have status 'complete'. There must be no
        tasks in pending, assigned, in_progress, blocked, or rework
        status.

        Returns:
            True if all build tasks are complete.
        """
        assert self._project_id is not None

        progress = queries.get_build_progress(self._project_id)
        total = progress.get("total", 0)

        if total == 0:
            return False

        complete = progress.get("complete", 0)
        return complete == total

    # ------------------------------------------------------------------
    # Rework protocol (standalone handler for 'rework' status tasks)
    # ------------------------------------------------------------------

    async def _handle_rework_tasks(self) -> None:
        """Process build tasks that have been flagged for rework.

        When a build task has status 'rework':
        1. Create a design_amendment record documenting the issue.
        2. If the rework reason is structural (affects dependencies),
           send an urgent message to the enterprise architect.
        3. If the rework is local (non-structural), authorize the
           service engineer to apply the fix and reset the task to
           'pending' for reassignment.
        """
        assert self._project_id is not None

        rework_tasks = queries.list_build_tasks(
            prjid=self._project_id, status=BUILD_STATUS_REWORK
        )

        if not rework_tasks:
            return

        self.logger.info(
            f"Processing {len(rework_tasks)} rework task(s)"
        )

        for task in rework_tasks:
            task_id = task["btid"]
            cmpid = task["cmpid"]
            agent_id = task.get("agtid")
            error = task.get("bterror", "Rework required")

            # 1. Create a design amendment record
            amendment_id = queries.create_design_amendment(
                cmpid=cmpid,
                dareason=error,
                dachange="Rework flagged during build phase.",
                agtid=agent_id,
            )

            self.logger.info(
                f"Design amendment {amendment_id} created for rework "
                f"task {task_id} (component {cmpid})"
            )

            # 2. Determine if the issue is structural
            structural_keywords = [
                "dependency",
                "interface",
                "contract",
                "schema",
                "architecture",
                "structural",
                "connection",
                "integration",
            ]
            error_lower = error.lower()
            is_structural = any(
                kw in error_lower for kw in structural_keywords
            )

            if is_structural:
                # Send urgent message to the enterprise architect
                arch_agents = queries.list_agents(
                    prjid=self._project_id,
                    role=ROLE_ENTERPRISE_ARCHITECT,
                )

                if arch_agents:
                    architect = arch_agents[0]
                    component = queries.get_component(cmpid)
                    cmp_name = (
                        component.get("cmpname", "unknown")
                        if component
                        else "unknown"
                    )

                    queries.create_message(
                        to_agtid=architect["agtid"],
                        from_agtid=agent_id,
                        msgbody=load_prompt(
                            "ea_rework_structural",
                            task_id=str(task_id),
                            cmp_name=cmp_name,
                            error=error,
                        ),
                        msgtype="urgent",
                    )

                    self.logger.info(
                        f"Sent urgent rework message to architect "
                        f"{architect['agtid']} for task {task_id}"
                    )

                # Mark task as error until architect resolves it
                queries.update_build_task(
                    task_id, btstatus=BUILD_STATUS_ERROR
                )
                queries.update_component(
                    cmpid, cmpstatus=COMPONENT_STATUS_ERROR
                )

            else:
                # Local rework: authorize the service engineer to fix
                # Find the service engineer for this component's
                # parent service
                ancestors = queries.get_component_ancestors(cmpid)
                service_cmpid = None
                for anc in ancestors:
                    if anc.get("cmplevel") == LEVEL_SERVICE:
                        service_cmpid = anc["cmpid"]
                        break

                se_agents = queries.list_agents(
                    prjid=self._project_id,
                    role=ROLE_SERVICE_ENGINEER,
                )
                target_se = None
                for se in se_agents:
                    if se.get("agtcmpid") == service_cmpid:
                        target_se = se
                        break

                # Fall back to any active service engineer
                if target_se is None and se_agents:
                    for se in se_agents:
                        if se.get("agtstatus") in (
                            AGENT_STATUS_IDLE,
                            AGENT_STATUS_WORKING,
                        ):
                            target_se = se
                            break

                if target_se:
                    component = queries.get_component(cmpid)
                    cmp_name = (
                        component.get("cmpname", "unknown")
                        if component
                        else "unknown"
                    )

                    queries.create_message(
                        to_agtid=target_se["agtid"],
                        from_agtid=agent_id,
                        msgbody=load_prompt(
                            "se_rework_local",
                            task_id=str(task_id),
                            cmp_name=cmp_name,
                            error=error,
                        ),
                        msgtype="normal",
                    )

                    self.logger.info(
                        f"Authorized service engineer "
                        f"{target_se['agtid']} for local rework on "
                        f"task {task_id}"
                    )

                # Reset task to pending for reassignment
                queries.update_build_task(
                    task_id, btstatus=BUILD_STATUS_PENDING
                )

                # Free the agent if one was assigned
                if agent_id:
                    queries.update_agent(
                        agent_id,
                        agtstatus=AGENT_STATUS_IDLE,
                        agtcmpid=None,
                    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_role_for_task(self, task: dict) -> str:
        """Determine the appropriate agent role for a build task.

        Args:
            task: Build task dict containing at least 'bttype'.

        Returns:
            Agent role constant string.
        """
        task_type = task.get("bttype", BUILD_TASK_IMPLEMENT)

        if task_type == BUILD_TASK_IMPLEMENT:
            return ROLE_CODING_AGENT
        elif task_type in (BUILD_TASK_ASSEMBLE, BUILD_TASK_INTEGRATE):
            return ROLE_SERVICE_ENGINEER
        elif task_type == BUILD_TASK_TEST:
            return ROLE_TESTING_AGENT
        else:
            return ROLE_CODING_AGENT

    def _build_task_prompt(self, task: dict) -> str:
        """Build a default prompt for a build task.

        Used when the task does not have a pre-generated prompt stored
        in ``btprompt``.

        Args:
            task: Build task dict.

        Returns:
            Prompt string to send to the agent.
        """
        component = queries.get_component(task["cmpid"])
        cmp_name = (
            component.get("cmpname", "unknown") if component else "unknown"
        )
        cmp_spec = (
            component.get("cmpspec", "") if component else ""
        )
        cmp_desc = (
            component.get("cmpdesc", "") if component else ""
        )

        # Gather test specs for this component
        test_specs = queries.list_test_specs(cmpid=task["cmpid"])
        test_section = ""
        if test_specs:
            test_section = "\n## Test Specifications\n\n"
            for ts in test_specs:
                test_section += f"### {ts.get('tsname', 'Test')}\n"
                test_section += f"{ts.get('tsdesc', '')}\n\n"

        # Gather connection map
        connections = queries.get_connections_for_component(
            task["cmpid"]
        )
        conn_section = ""
        if connections:
            conn_section = "\n## Connection Map\n\n"
            for conn in connections:
                conn_section += (
                    f"- {conn.get('from_name', '?')} -> "
                    f"{conn.get('to_name', '?')}: "
                    f"{conn.get('condesc', '')}\n"
                )

        task_type = task.get("bttype", BUILD_TASK_IMPLEMENT)
        role_name = self._get_role_for_task(task).replace("_", " ")

        return load_prompt(
            "all_build_task",
            task_type=task_type.title(),
            cmp_name=cmp_name,
            cmp_desc=cmp_desc,
            cmp_spec=cmp_spec,
            conn_section=conn_section,
            test_section=test_section,
            role_name=role_name,
        )
