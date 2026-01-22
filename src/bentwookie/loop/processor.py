"""Request processor using Claude Agent SDK."""

import asyncio
import json
import os
import re
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

# Test retry limit to prevent infinite dev<->test loops
MAX_TEST_RETRIES = 3

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


def _parse_test_results(response_text: str) -> dict | None:
    """Parse test results JSON from Claude's response.

    Args:
        response_text: Full response text from Claude.

    Returns:
        Parsed test results dict or None if not found/invalid.
    """
    # Look for JSON block in the response
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Also try to find raw JSON object
    json_match = re.search(r'\{[^{}]*"error_count"[^{}]*\}', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _generate_error_fix_plan(code_dir: str, test_results: dict) -> str:
    """Generate a new PLAN.md focused on fixing test errors.

    Reads the existing PLAN.md and TESTPLAN.md, extracts error information,
    and creates a new plan focused on fixes.

    Args:
        code_dir: Path to the code directory.
        test_results: Parsed test results dict.

    Returns:
        Path to the updated PLAN.md.
    """
    plan_path = Path(code_dir) / "PLAN.md"
    testplan_path = Path(code_dir) / "TESTPLAN.md"

    # Read existing documents
    old_plan = ""
    if plan_path.exists():
        old_plan = plan_path.read_text()

    testplan = ""
    if testplan_path.exists():
        testplan = testplan_path.read_text()

    # Extract error sections from TESTPLAN
    error_sections = []
    if testplan:
        # Find all ERROR blocks
        error_pattern = r'(\*\*ERROR\*\*:.*?)(?=###|\Z)'
        errors = re.findall(error_pattern, testplan, re.DOTALL)
        error_sections = errors

    # Extract summary section from old plan
    summary_match = re.search(r'## Summary(.*?)(?=##|\Z)', old_plan, re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else ""

    # Generate new plan
    failed_tests = test_results.get("failed_tests", [])
    error_count = test_results.get("error_count", 0)

    new_plan = f"""# Error Fix Plan

**IMPORTANT**: This plan was auto-generated after test failures. Review this document,
all code in the working directory, and resolve all errors.

## Original Summary
{summary}

## Test Failure Summary
- **Total Errors**: {error_count}
- **Failed Tests**: {', '.join(failed_tests) if failed_tests else 'See TESTPLAN.md'}

## Errors to Fix

Review TESTPLAN.md for detailed error information. Key errors:

"""
    for i, error in enumerate(error_sections[:5], 1):  # Limit to first 5 errors
        new_plan += f"### Error {i}\n{error.strip()}\n\n"

    new_plan += """
## Implementation Steps

1. **Review each failed test** in TESTPLAN.md
2. **Analyze the error details** (Error Type, Message, Stack Trace)
3. **Apply the suggested fixes** from the Analysis sections
4. **Verify fixes** don't break other functionality
5. **Update TESTPLAN.md** if you add new tests

## Guidelines

- Focus on fixing errors, not adding new features
- Run quick sanity checks after each fix
- Document any changes to the implementation approach
"""

    # Write the new plan
    plan_path.write_text(new_plan)
    return str(plan_path)


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

# BentWookie project ID for auto-created bug-fix requests
BENTWOOKIE_PROJECT_ID = 1


def _create_bugfix_request(original_request: dict, error_msg: str) -> int | None:
    """Create a bug-fix request for BentWookie when a request fails.

    Args:
        original_request: The request that failed.
        error_msg: The error message describing the failure.

    Returns:
        The new request ID, or None if creation failed.
    """
    logger = get_logger()

    try:
        # Build the bug-fix prompt with error details
        prompt = f"""## Bug Fix Request

**Original Request**: {original_request.get('reqname', 'Unknown')} (ID: {original_request.get('reqid')})
**Project**: {original_request.get('prjname', 'Unknown')}
**Phase**: {original_request.get('reqphase', 'Unknown')}

### Error Details

{error_msg}

### Task

Please investigate and fix this error. Review the error details above, identify the root cause, and implement a fix.

### Context

This bug-fix request was auto-generated when request ID {original_request.get('reqid')} failed with an error.
"""

        # Create the bug-fix request for BentWookie (project ID 3)
        reqid = queries.create_request(
            prjid=BENTWOOKIE_PROJECT_ID,
            reqname=f"Bug-Fix: {original_request.get('reqname', 'Unknown')[:40]}",
            reqprompt=prompt,
            reqtype="bug_fix",
            reqstatus="tbd",
            reqphase="plan",
            reqpriority=3,  # Higher priority for bug fixes
        )

        logger.info(
            f"Created bug-fix request {reqid} for failed request {original_request.get('reqid')}"
        )
        return reqid

    except Exception as e:
        logger.warning(f"Failed to create bug-fix request: {e}")
        return None

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

    # Mark as work in progress and clear any previous error
    queries.update_request_error(reqid, None)
    queries.update_request_status(reqid, STATUS_WIP)

    if not SDK_AVAILABLE:
        error_msg = "Claude Agent SDK not available. Install with: pip install claude-agent-sdk"
        logger.error(error_msg)
        queries.update_request_error(reqid, error_msg)
        queries.update_request_status(reqid, STATUS_ERR)
        _create_bugfix_request(request, error_msg)
        return False

    # Check auth mode and validate accordingly
    from ..settings import get_auth_mode, AUTH_MODE_API, AUTH_MODE_MAX

    auth_mode = get_auth_mode()
    if auth_mode == AUTH_MODE_API:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            error_msg = (
                "Auth mode is 'api' but ANTHROPIC_API_KEY not set. "
                "Either set the key: export ANTHROPIC_API_KEY='your-key' "
                "Or switch to Max mode: bw config --auth max"
            )
            logger.error(error_msg)
            queries.update_request_error(reqid, error_msg)
            queries.update_request_status(reqid, STATUS_ERR)
            _create_bugfix_request(request, error_msg)
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

        # Determine working directory with fallback hierarchy:
        # 1. Request reqcodedir (if set)
        # 2. Project prjcodedir (if set)
        # 3. Create CWD/project_name subfolder (auto-created)
        code_dir = request.get("reqcodedir")
        if not code_dir:
            code_dir = request.get("prjcodedir")
        if not code_dir:
            # Create project-named subfolder in CWD
            project_name = request.get("prjname", "project")
            code_dir = os.path.join(os.getcwd(), project_name)
            # Auto-create the directory if it doesn't exist
            Path(code_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created project code directory: {code_dir}")

        cwd = str(Path(code_dir).resolve())

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

        # Special handling for test phase - check for failures
        if phase == "test":
            test_results = _parse_test_results(response_text)
            if test_results and test_results.get("error_count", 0) > 0:
                error_count = test_results["error_count"]
                retry_count = request.get("reqtestretries", 0) or 0

                if retry_count >= MAX_TEST_RETRIES:
                    # Max retries exceeded - mark as error
                    error_msg = (
                        f"Max test retries ({MAX_TEST_RETRIES}) exceeded. "
                        f"{error_count} test(s) still failing."
                    )
                    logger.error(f"Request {reqid} failed: {error_msg}")
                    queries.update_request_error(reqid, error_msg)
                    queries.update_request_status(reqid, STATUS_ERR)
                    queries.add_learning(
                        request["prjid"],
                        f"Request '{request['reqname']}' exceeded max test retries with {error_count} failures"
                    )
                    _create_bugfix_request(request, error_msg)
                    return False

                # Generate error fix plan and loop back to dev
                logger.warning(
                    f"Request {reqid} has {error_count} test failure(s). "
                    f"Generating fix plan and returning to dev phase (retry {retry_count + 1}/{MAX_TEST_RETRIES})"
                )

                # Generate new PLAN.md with error fixes
                _generate_error_fix_plan(cwd, test_results)

                # Increment retry counter and go back to dev
                queries.increment_request_test_retries(reqid)
                queries.update_request_phase(reqid, "dev")
                queries.update_request_status(reqid, STATUS_TBD)

                logger.info(f"Request {reqid} returned to dev phase for error fixes")
                return True

            # Tests passed - reset retry counter and continue
            if request.get("reqtestretries", 0):
                queries.reset_request_test_retries(reqid)
                logger.info(f"Request {reqid} tests passed, retry counter reset")

        # Advance to next phase (skip deploy/verify for local infrastructure)
        next_phase = get_next_phase(phase, reqid)
        if next_phase and next_phase != "complete":
            queries.update_request_phase(reqid, next_phase)
            queries.update_request_status(reqid, STATUS_TBD)
            logger.info(f"Request {reqid} advanced to phase: {next_phase}")
        else:
            # Request is complete (next_phase is None or "complete")
            queries.update_request_phase(reqid, "complete")
            queries.update_request_status(reqid, STATUS_DONE)
            logger.info(f"Request {reqid} completed all phases")

        return True

    except asyncio.TimeoutError:
        error_msg = f"Timed out in phase {phase}"
        logger.error(f"Request {reqid} {error_msg}")
        queries.update_request_error(reqid, error_msg)
        queries.update_request_status(reqid, STATUS_TMOUT)
        _create_bugfix_request(request, error_msg)
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

        # Build user-friendly error message
        friendly_error = error_msg
        if "credit" in error_msg.lower() or "balance" in error_msg.lower() or "billing" in error_msg.lower():
            friendly_error = "Insufficient credits. Add credits at: https://console.anthropic.com/settings/billing"
            logger.error(f"Request {reqid} failed: {friendly_error}")
        elif "exit code 1" in error_msg.lower() or "command failed" in error_msg.lower():
            friendly_error = "Claude CLI returned an error. Check your API credits and authentication."
            logger.error(f"Request {reqid} failed: {friendly_error}")
        elif "api" in error_msg.lower() or "key" in error_msg.lower() or "auth" in error_msg.lower():
            friendly_error = f"Authentication error: {error_msg}"
            logger.error(f"Request {reqid} failed: {friendly_error}")
        else:
            friendly_error = f"Error in phase {phase}: {error_msg}"
            logger.error(f"Request {reqid} failed: {friendly_error}")

        queries.update_request_error(reqid, friendly_error)
        queries.update_request_status(reqid, STATUS_ERR)

        # Try to add learning about the error
        try:
            queries.add_learning(
                request["prjid"],
                f"Error in {phase} phase for {request['reqname']}: {error_msg[:200]}"
            )
        except Exception:
            pass

        # Create bug-fix request for BentWookie
        _create_bugfix_request(request, friendly_error)

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

    # Advance to next phase (skip deploy/verify for local infrastructure)
    next_phase = get_next_phase(phase, reqid)
    if next_phase:
        queries.update_request_phase(reqid, next_phase)
        queries.update_request_status(reqid, STATUS_TBD)
    else:
        queries.update_request_status(reqid, STATUS_DONE)

    return True
