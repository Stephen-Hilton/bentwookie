"""Request processor using Claude Agent SDK."""

import asyncio

from ..constants import (
    DAEMON_MAX_TURNS,
    DEFAULT_MODEL,
    DEFAULT_PERMISSION_MODE,
    STATUS_DONE,
    STATUS_ERR,
    STATUS_TBD,
    STATUS_TMOUT,
    STATUS_WIP,
)
from ..db import queries
from ..logging_util import get_logger
from .phases import (
    get_next_phase,
    get_phase_prompt,
    get_phase_timeout,
    get_phase_tools,
    get_system_prompt,
    save_to_docs,
)

# Import Claude Agent SDK
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        TextBlock,
        ToolResultBlock,
        ToolUseBlock,
        query,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


async def process_request(request: dict) -> bool:
    """Process a single request through its current phase.

    Args:
        request: Request dict from database (with joined project fields).

    Returns:
        True if processing succeeded, False otherwise.
    """
    logger = get_logger()
    reqid = request["reqid"]
    phase = request["reqphase"]

    logger.info(f"Processing request {reqid} ({request['reqname']}) - phase: {phase}")

    # Mark as work in progress
    queries.update_request_status(reqid, STATUS_WIP)

    if not SDK_AVAILABLE:
        logger.error("Claude Agent SDK not available. Install with: pip install claude-agent-sdk")
        queries.update_request_status(reqid, STATUS_ERR)
        return False

    try:
        # Build phase-specific prompt
        prompt = get_phase_prompt(request)

        # Configure Claude SDK
        options = ClaudeAgentOptions(
            model=DEFAULT_MODEL,
            cwd=request.get("reqcodedir") or ".",
            system_prompt=get_system_prompt(request),
            allowed_tools=get_phase_tools(phase),
            permission_mode=DEFAULT_PERMISSION_MODE,
            max_turns=DAEMON_MAX_TURNS,
        )

        # Set timeout
        timeout = get_phase_timeout(phase)

        # Run Claude with timeout
        response_text = await asyncio.wait_for(
            _run_claude(prompt, options, logger),
            timeout=timeout
        )

        # Save output to docs if substantial
        if response_text and len(response_text) > 500:
            doc_path = save_to_docs(request, response_text)
            queries.update_request_docpath(reqid, doc_path)
            logger.info(f"Saved phase output to: {doc_path}")

        # Advance to next phase
        next_phase = get_next_phase(phase)
        if next_phase:
            queries.update_request_phase(reqid, next_phase)
            queries.update_request_status(reqid, STATUS_TBD)
            logger.info(f"Request {reqid} advanced to phase: {next_phase}")
        else:
            # Request is complete
            queries.update_request_status(reqid, STATUS_DONE)
            logger.info(f"Request {reqid} completed all phases")

        return True

    except asyncio.TimeoutError:
        logger.error(f"Request {reqid} timed out in phase {phase}")
        queries.update_request_status(reqid, STATUS_TMOUT)
        return False

    except Exception as e:
        logger.exception(f"Error processing request {reqid}: {e}")
        queries.update_request_status(reqid, STATUS_ERR)

        # Try to add learning about the error
        try:
            queries.add_learning(
                request["prjid"],
                f"Error in {phase} phase for {request['reqname']}: {str(e)[:200]}"
            )
        except Exception:
            pass

        return False


async def _run_claude(
    prompt: str,
    options: "ClaudeAgentOptions",
    logger,
) -> str:
    """Run Claude Agent SDK and collect response.

    Args:
        prompt: The prompt to send.
        options: Claude agent options.
        logger: Logger instance.

    Returns:
        Combined text response from Claude.
    """
    response_text = ""
    tool_count = 0

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_text += block.text + "\n"
                elif isinstance(block, ToolUseBlock):
                    tool_count += 1
                    logger.debug(f"Tool use: {block.name}")

    logger.info(f"Claude completed with {tool_count} tool uses")
    return response_text.strip()


def process_request_sync(request: dict) -> bool:
    """Synchronous wrapper for process_request.

    Args:
        request: Request dict from database.

    Returns:
        True if processing succeeded, False otherwise.
    """
    return asyncio.run(process_request(request))


# Fallback implementation when SDK is not available
async def _process_request_mock(request: dict) -> bool:
    """Mock implementation for testing without SDK.

    Args:
        request: Request dict.

    Returns:
        Always True (simulates success).
    """
    logger = get_logger()
    reqid = request["reqid"]
    phase = request["reqphase"]

    logger.warning(f"Mock processing request {reqid} (SDK not available)")

    # Simulate some work
    await asyncio.sleep(1)

    # Advance to next phase
    next_phase = get_next_phase(phase)
    if next_phase:
        queries.update_request_phase(reqid, next_phase)
        queries.update_request_status(reqid, STATUS_TBD)
    else:
        queries.update_request_status(reqid, STATUS_DONE)

    return True
