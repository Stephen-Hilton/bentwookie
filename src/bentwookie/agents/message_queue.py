"""Database-backed message queue for inter-agent communication.

Provides queuing, delivery, and management of messages between BentWookie
agents.  Normal messages queue until the recipient finishes current work;
urgent messages are delivered immediately (interrupting the agent).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..constants import (
    MESSAGE_STATUS_DELIVERED,
    MESSAGE_STATUS_QUEUED,
    MESSAGE_STATUS_READ,
    MSG_TYPE_NORMAL,
    MSG_TYPE_URGENT,
)
from ..db import queries
from ..logging_util import BWLogger, get_logger

if TYPE_CHECKING:
    from .manager import AgentManager

logger: BWLogger = get_logger()


class MessageQueue:
    """Database-backed message queue for inter-agent communication.

    Messages are persisted in the ``agent_message`` table.  The queue
    prioritises urgent messages over normal ones when dequeuing.

    Args:
        manager: The :class:`AgentManager` instance used to write messages
            to agent stdin.
    """

    def __init__(self, manager: AgentManager) -> None:
        self.manager = manager

    # ------------------------------------------------------------------
    # Enqueue / dequeue
    # ------------------------------------------------------------------

    def enqueue(
        self,
        sender_id: int | None,
        recipient_id: int,
        body: str,
        msg_type: str = MSG_TYPE_NORMAL,
    ) -> int:
        """Insert a message into the agent_message table.

        Args:
            sender_id: Agent ID of the sender, or ``None`` for system
                messages.
            recipient_id: Agent ID of the recipient.
            body: The message body text.
            msg_type: ``"normal"`` (default) or ``"urgent"``.

        Returns:
            The new message ID.
        """
        msg_id: int = queries.create_message(
            to_agtid=recipient_id,
            msgbody=body,
            from_agtid=sender_id,
            msgtype=msg_type,
        )
        logger.info(
            f"Message {msg_id} enqueued: "
            f"sender={sender_id} -> recipient={recipient_id} "
            f"type={msg_type}"
        )
        return msg_id

    def dequeue(self, agent_id: int) -> dict | None:
        """Get the next pending message for an agent.

        Urgent messages are returned before normal ones.

        Args:
            agent_id: The recipient agent ID.

        Returns:
            A message ``dict`` or ``None`` if the queue is empty.
        """
        msg = queries.dequeue_message(agent_id)
        if msg:
            logger.debug(
                f"Dequeued message {msg['msgid']} for agent {agent_id}"
            )
        return msg

    # ------------------------------------------------------------------
    # Delivery helpers
    # ------------------------------------------------------------------

    async def deliver(self, agent_id: int) -> bool:
        """Dequeue the next message for *agent_id* and deliver it.

        The message is written to the agent's stdin via
        :pymethod:`AgentManager.send_message` and its status is updated
        to ``'delivered'``.

        Args:
            agent_id: The recipient agent ID.

        Returns:
            ``True`` if a message was delivered, ``False`` if the queue
            was empty.
        """
        msg = self.dequeue(agent_id)
        if msg is None:
            return False

        await self.manager.send_message(agent_id, msg["msgbody"])
        queries.mark_message_read(msg["msgid"])
        # The dequeue call already marks the message as 'delivered'.
        # We keep the explicit update here so callers can rely on
        # the status being set even if dequeue semantics change.
        logger.info(
            f"Delivered message {msg['msgid']} to agent {agent_id}"
        )
        return True

    async def deliver_all_pending(self) -> int:
        """Deliver pending messages to every active agent.

        Iterates through all active agents (those whose status is not
        ``terminated`` or ``error``) and delivers any queued messages.

        Returns:
            Total number of messages delivered across all agents.
        """
        from ..constants import AGENT_STATUS_TERMINATED, AGENT_STATUS_ERROR

        active_agents: list[dict] = queries.list_agents()
        delivered_count = 0

        for agent in active_agents:
            if agent["agtstatus"] in (
                AGENT_STATUS_TERMINATED,
                AGENT_STATUS_ERROR,
            ):
                continue

            agent_id: int = agent["agtid"]
            while await self.deliver(agent_id):
                delivered_count += 1

        if delivered_count:
            logger.info(
                f"Delivered {delivered_count} pending message(s) "
                f"across active agents"
            )
        return delivered_count

    async def check_urgent(self, agent_id: int) -> bool:
        """Check for and immediately deliver urgent messages.

        If any urgent messages are queued for *agent_id*, they are
        delivered right away (interrupting the agent's current work).

        Args:
            agent_id: The agent to check.

        Returns:
            ``True`` if one or more urgent messages were delivered.
        """
        urgent_msgs: list[dict] = queries.list_messages(
            to_agtid=agent_id,
            msgtype=MSG_TYPE_URGENT,
            status=MESSAGE_STATUS_QUEUED,
        )

        if not urgent_msgs:
            return False

        for msg in urgent_msgs:
            await self.manager.send_message(agent_id, msg["msgbody"])
            queries.mark_message_read(msg["msgid"])
            logger.info(
                f"Urgent message {msg['msgid']} delivered "
                f"(interrupt) to agent {agent_id}"
            )

        return True

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_pending_count(self, agent_id: int | None = None) -> int:
        """Return the number of queued (pending) messages.

        Args:
            agent_id: If given, count only messages addressed to this
                agent.  Otherwise count all queued messages.

        Returns:
            The count of pending messages.
        """
        return queries.count_pending_messages(agtid=agent_id)

    def list_messages(
        self,
        agent_id: int | None = None,
        msg_type: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """List messages with optional filters.

        Args:
            agent_id: Filter by recipient agent ID.
            msg_type: Filter by message type (``"normal"`` /
                ``"urgent"``).
            status: Filter by message status (``"queued"`` /
                ``"delivered"`` / ``"read"``).

        Returns:
            A list of message dicts matching the filters.
        """
        return queries.list_messages(
            to_agtid=agent_id,
            msgtype=msg_type,
            status=status,
        )

    def mark_read(self, message_id: int) -> None:
        """Mark a message as read.

        Args:
            message_id: The ID of the message to mark.
        """
        queries.mark_message_read(message_id)
        logger.debug(f"Message {message_id} marked as read")
