"""Request processor using Claude Agent SDK."""

import asyncio
import os
import time
from pathlib import Path

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

# Rate limit handling
MAX_RETRIES = 3
INITIAL_BACKOFF = 60  # seconds
MAX_BACKOFF = 600  # 10 minutes

# Track rate limit state globally so daemon can pause
_rate_limited_until: float = 0


def is_rate_limited() -> bool:
    """Check if we're currently rate limited.

    Returns:
        True if rate limited and should wait.
    """
    return time.time() < _rate_limited_until


def get_rate_limit_wait() -> float:
    """Get seconds to wait before retrying.

    Returns:
        Seconds until rate limit expires, or 0 if not limited.
    """
    wait = _rate_limited_until - time.time()
    return max(0, wait)


def _is_rate_limit_error(error_msg: str) -> bool:
    """Check if an error message indicates rate limiting.

    Args:
        error_msg: Error message string.

    Returns:
        True if this is a rate limit error.
    """
    error_lower = error_msg.lower()
    return any(indicator in error_lower for indicator in [
        "rate limit",
        "rate_limit",
        "ratelimit",
        "429",
        "too many requests",
        "overloaded",
        "capacity",
    ])
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

    # Check auth mode and validate accordingly
    from ..settings import get_auth_mode, AUTH_MODE_API, AUTH_MODE_MAX

    auth_mode = get_auth_mode()
    if auth_mode == AUTH_MODE_API:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error(
                "Auth mode is 'api' but ANTHROPIC_API_KEY not set.\n"
                "  Either set the key: export ANTHROPIC_API_KEY='your-key'\n"
                "  Or switch to Max mode: bw config --auth max"
            )
            queries.update_request_status(reqid, STATUS_ERR)
            return False
    elif auth_mode == AUTH_MODE_MAX:
        # Unset API key so SDK uses CLI's web auth instead
        if "ANTHROPIC_API_KEY" in os.environ:
            logger.debug("Unsetting ANTHROPIC_API_KEY to use Claude Max web auth")
            del os.environ["ANTHROPIC_API_KEY"]
        logger.debug("Using Claude Max subscription (web auth)")

    try:
        # Build phase-specific prompt
        prompt = get_phase_prompt(request)

        # Determine working directory (must be absolute path)
        code_dir = request.get("reqcodedir")
        if code_dir:
            cwd = str(Path(code_dir).resolve())
        else:
            cwd = os.getcwd()

        # Configure Claude SDK
        options = ClaudeAgentOptions(
            model=DEFAULT_MODEL,
            cwd=cwd,
            system_prompt=get_system_prompt(request),
            allowed_tools=get_phase_tools(phase),
            permission_mode=DEFAULT_PERMISSION_MODE,
            max_turns=DAEMON_MAX_TURNS,
        )

        logger.info(f"Using cwd: {cwd}")

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
        global _rate_limited_until
        error_msg = str(e)

        # Check for rate limit errors - these should be retried
        if _is_rate_limit_error(error_msg):
            backoff = INITIAL_BACKOFF
            _rate_limited_until = time.time() + backoff
            logger.warning(
                f"Request {reqid} hit rate limit. Will retry in {backoff}s.\n"
                f"  Error: {error_msg[:100]}"
            )
            # Keep status as TBD so it gets retried
            queries.update_request_status(reqid, STATUS_TBD)
            return False

        # Check for common issues and provide helpful messages
        if "credit" in error_msg.lower() or "balance" in error_msg.lower() or "billing" in error_msg.lower():
            logger.error(
                f"Request {reqid} failed: Insufficient credits.\n"
                "  Add credits at: https://console.anthropic.com/settings/billing"
            )
        elif "exit code 1" in error_msg.lower() or "command failed" in error_msg.lower():
            # Generic CLI error - might be billing, auth, or other issue
            logger.error(
                f"Request {reqid} failed: Claude CLI returned an error.\n"
                "  Check your API credits and authentication."
            )
        elif "api" in error_msg.lower() or "key" in error_msg.lower() or "auth" in error_msg.lower():
            logger.error(f"Request {reqid} failed: Authentication error - {error_msg}")
        else:
            logger.error(f"Request {reqid} failed in phase {phase}: {error_msg}")

        queries.update_request_status(reqid, STATUS_ERR)

        # Try to add learning about the error
        try:
            queries.add_learning(
                request["prjid"],
                f"Error in {phase} phase for {request['reqname']}: {error_msg[:200]}"
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
