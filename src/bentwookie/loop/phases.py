"""Phase-specific logic and prompt generation for BentWookie."""

from pathlib import Path

from ..constants import (
    NEXT_PHASE,
    PHASE_TIMEOUTS,
    PHASE_TOOLS,
    TYPE_NAMES,
)
from ..db import queries


def get_templates_dir() -> Path:
    """Get the path to the templates directory."""
    # Use data/prompts/phases for user-editable templates
    return Path("data/prompts/phases")


def get_bundled_templates_dir() -> Path:
    """Get the path to the bundled (fallback) templates directory."""
    return Path(__file__).parent.parent / "templates" / "phases"


def get_system_template_path() -> Path:
    """Get the path to the system prompt template."""
    return Path("data/prompts/system.md")


def get_bundled_system_template_path() -> Path:
    """Get the path to the bundled system prompt template."""
    return Path(__file__).parent.parent / "templates" / "system.md"


def load_phase_template(phase: str) -> str:
    """Load the template for a given phase.

    Args:
        phase: Phase name (plan, dev, test, deploy, verify, document, commit).

    Returns:
        Template content as string.

    Raises:
        FileNotFoundError: If template doesn't exist.
    """
    from ..logging_util import get_logger

    logger = get_logger()

    # Try user-editable location first
    template_path = get_templates_dir() / f"{phase}.md"
    if template_path.exists():
        return template_path.read_text()

    # Fall back to bundled templates
    bundled_path = get_bundled_templates_dir() / f"{phase}.md"
    if bundled_path.exists():
        logger.debug(f"Using bundled template for {phase} (user template not found)")
        return bundled_path.read_text()

    raise FileNotFoundError(
        f"Template for phase '{phase}' not found in {template_path} or {bundled_path}"
    )


def _load_plan_document(code_dir: str) -> str:
    """Load PLAN.md from the code directory if it exists.

    Args:
        code_dir: Path to the code directory.

    Returns:
        Plan content or empty string if not found.
    """
    plan_path = Path(code_dir) / "PLAN.md"
    if plan_path.exists():
        try:
            content = plan_path.read_text()
            return f"\n## Current PLAN.md Content\n\n```markdown\n{content}\n```\n"
        except Exception:
            return ""
    return ""


def _load_testplan_document(code_dir: str) -> str:
    """Load TESTPLAN.md from the code directory if it exists.

    Args:
        code_dir: Path to the code directory.

    Returns:
        Test plan content or empty string if not found.
    """
    testplan_path = Path(code_dir) / "TESTPLAN.md"
    if testplan_path.exists():
        try:
            content = testplan_path.read_text()
            return f"\n## Current TESTPLAN.md Content\n\n```markdown\n{content}\n```\n"
        except Exception:
            return ""
    return ""


def get_phase_prompt(request: dict) -> str:
    """Build the complete prompt for processing a request in its current phase.

    Args:
        request: Request dict from database (includes joined project fields).

    Returns:
        Formatted prompt string.
    """
    phase = request["reqphase"]
    template = load_phase_template(phase)

    # Get effective infrastructure (project + request overrides)
    infrastructure = ""
    if phase in ("deploy", "plan", "dev"):
        # Use effective infrastructure which merges project + request
        effective_infra = queries.get_effective_infrastructure(request["reqid"])
        if effective_infra:
            infrastructure = "\n".join(
                f"- **{inftype}**: {inf['infprovider']} ({inf['infval'] or 'default'})"
                for inftype, inf in effective_infra.items()
            )
        else:
            infrastructure = "- Local development environment"

    # Get project learnings for context (includes global learnings with prjid=-1)
    learnings = queries.get_learnings_with_global(request["prjid"])
    learnings_text = ""
    if learnings:
        # Separate global and project-specific learnings
        global_learnings = [l for l in learnings if l.get("scope") == "global"]
        project_learnings = [l for l in learnings if l.get("scope") == "project"]

        learnings_parts = []
        if global_learnings:
            learnings_parts.append("### Global Learnings\n" + "\n".join(
                f"- {l['lrndesc']}" for l in global_learnings[:5]
            ))
        if project_learnings:
            learnings_parts.append("### Project Learnings\n" + "\n".join(
                f"- {l['lrndesc']}" for l in project_learnings[:10]
            ))

        if learnings_parts:
            learnings_text = "\n\n## Learnings\n" + "\n\n".join(learnings_parts)

    # Get code directory for loading plan/testplan documents
    code_dir = request.get("reqcodedir") or "."

    # Load PLAN and TESTPLAN content for dev and test phases
    plan_content = ""
    testplan_content = ""
    if phase in ("dev", "test"):
        plan_content = _load_plan_document(code_dir)
        testplan_content = _load_testplan_document(code_dir)

    # Get commit branch info for commit phase
    branch_mode = ""
    target_branch = ""
    if phase == "commit":
        commit_info = get_commit_branch_info(request)
        branch_mode = commit_info["branch_mode"]
        target_branch = commit_info["target_branch"]

    # Format the template
    prompt = template.format(
        project_name=request.get("prjname", "Unknown"),
        project_version=request.get("prjversion", "poc"),
        project_phase=request.get("project_phase", "dev"),
        request_name=request["reqname"],
        request_type=TYPE_NAMES.get(request["reqtype"], request["reqtype"]),
        request_prompt=request["reqprompt"],
        code_dir=code_dir,
        infrastructure=infrastructure,
        plan_content=plan_content,
        testplan_content=testplan_content,
        branch_mode=branch_mode,
        target_branch=target_branch,
    )

    # Append project prompt if present
    if request.get("prjprompt"):
        prompt += f"\n\n## Project Guidelines\n\n{request['prjprompt']}\n"

    # Append learnings if any
    if learnings_text:
        prompt += learnings_text

    return prompt


def get_phase_tools(phase: str) -> list[str]:
    """Get the list of allowed tools for a phase.

    Args:
        phase: Phase name.

    Returns:
        List of tool names allowed for this phase.
    """
    return PHASE_TOOLS.get(phase, ["Read"])


def get_phase_timeout(phase: str) -> int:
    """Get the timeout in seconds for a phase.

    Args:
        phase: Phase name.

    Returns:
        Timeout in seconds.
    """
    return PHASE_TIMEOUTS.get(phase, 30 * 60)  # Default 30 minutes


def is_local_only(reqid: int) -> bool:
    """Check if all infrastructure for a request is local.

    Args:
        reqid: Request ID.

    Returns:
        True if all infrastructure is local (or no infrastructure defined).
    """
    effective_infra = queries.get_effective_infrastructure(reqid)

    if not effective_infra:
        # No infrastructure defined = local development
        return True

    # Check if all providers are "local"
    for inftype, inf in effective_infra.items():
        provider = inf.get("infprovider", "local").lower()
        value = (inf.get("infval") or "").lower()

        # Check both provider and value for "local" indicators
        if provider != "local" and "local" not in value:
            return False

    return True


def get_commit_branch_info(request: dict) -> dict:
    """Get branch mode and target branch for commit phase.

    Precedence: request-level → project-level → global settings

    Args:
        request: Request dict from database.

    Returns:
        Dict with branch_mode and target_branch keys.
    """
    from ..settings import get_commit_branch_mode, get_commit_branch_name

    # Check request-level override
    branch_override = request.get("reqcommitbranch")
    if branch_override:
        return {
            "branch_mode": "other",
            "target_branch": branch_override,
        }

    # Check project-level override
    prj_mode = request.get("prjcommitbranchmode")
    prj_branch = request.get("prjcommitbranchname")
    if prj_mode:
        if prj_mode == "other":
            return {
                "branch_mode": "other",
                "target_branch": prj_branch or "main",
            }
        else:
            return {
                "branch_mode": "current",
                "target_branch": "<current branch>",
            }

    # Use global settings
    mode = get_commit_branch_mode()
    if mode == "other":
        branch_name = get_commit_branch_name()
        return {
            "branch_mode": "other",
            "target_branch": branch_name or "main",
        }
    else:
        return {
            "branch_mode": "current",
            "target_branch": "<current branch>",
        }


def get_next_phase(current_phase: str, reqid: int | None = None) -> str | None:
    """Get the next phase in the workflow.

    Args:
        current_phase: Current phase name.
        reqid: Optional request ID to check infrastructure for local-only skipping.

    Returns:
        Next phase name, or None if complete.
    """
    next_phase = NEXT_PHASE.get(current_phase)

    # Skip deploy and verify phases for local-only infrastructure
    if reqid is not None and next_phase in ("deploy", "verify"):
        if is_local_only(reqid):
            # Skip deploy -> document, skip verify -> document
            return "document"

    # Skip commit phase if disabled
    if reqid is not None and next_phase == "commit":
        request = queries.get_request(reqid)
        if request:
            # Check request-level override first
            if request.get("reqcommitenabled") == 0:  # Explicitly disabled
                return "complete"
            elif request.get("reqcommitenabled") == 2:  # Force enabled
                return "commit"
            else:  # Check project-level, then global setting
                # Check project-level override
                prj_commit_enabled = request.get("prjcommitenabled")
                if prj_commit_enabled is not None:
                    # Project has explicit setting: 0=disabled, 1=enabled
                    if prj_commit_enabled == 0:
                        return "complete"
                    # If 1, continue to commit phase
                else:
                    # Use global setting
                    from ..settings import get_commit_enabled
                    if not get_commit_enabled():
                        return "complete"

    return next_phase


def get_system_prompt(request: dict) -> str:
    """Generate the system prompt for Claude.

    Args:
        request: Request dict from database.

    Returns:
        System prompt string.
    """
    from ..logging_util import get_logger

    logger = get_logger()
    phase = request["reqphase"]
    project_name = request.get("prjname", "Unknown")

    # Try to load from template file
    system_prompt = None
    try:
        template_path = get_system_template_path()
        if template_path.exists():
            template = template_path.read_text()
            system_prompt = template.format(
                phase=phase.upper(),
                project_name=project_name,
            )
    except Exception as e:
        logger.warning(f"Could not load system template: {e}, using fallback")

    # Try bundled template if not loaded
    if system_prompt is None:
        try:
            bundled_path = get_bundled_system_template_path()
            if bundled_path.exists():
                template = bundled_path.read_text()
                system_prompt = template.format(
                    phase=phase.upper(),
                    project_name=project_name,
                )
        except Exception as e:
            logger.warning(f"Could not load bundled system template: {e}, using hardcoded")

    # Fallback to hardcoded version
    if system_prompt is None:
        system_prompt = f"""You are an AI assistant working on the {project_name} project.

You are currently in the **{phase.upper()}** phase of the development workflow.

## Workflow Context
BentWookie manages development requests through phases:
1. **plan** - Analyze requirements and create implementation plan
2. **dev** - Implement the changes
3. **test** - Run tests and verify quality
4. **deploy** - Deploy to target environment
5. **verify** - Verify deployment success
6. **document** - Update documentation

Your work in this phase will be recorded and used as context for subsequent phases.

## Guidelines
- Focus on completing the current phase's objectives
- Be thorough but efficient
- Report any blockers or issues clearly
- Follow existing code patterns and conventions
"""

    # Append project's claude.md if configured
    claude_md_path = request.get("prjclaudemd")
    if claude_md_path:
        try:
            claude_md_file = Path(claude_md_path).expanduser().resolve()
            if claude_md_file.exists():
                claude_md_content = claude_md_file.read_text()
                system_prompt += f"\n\n## Project-Specific Instructions (claude.md)\n\n{claude_md_content}"
            else:
                logger.warning(f"Project claude.md not found: {claude_md_path}")
        except Exception as e:
            logger.warning(f"Could not load project claude.md: {e}")

    return system_prompt


def save_to_docs(request: dict, content: str) -> str:
    """Save phase output to the docs directory.

    Args:
        request: Request dict.
        content: Content to save.

    Returns:
        Path to the saved file.
    """
    from datetime import datetime

    from ..constants import DEFAULT_DOCS_PATH

    docs_dir = Path(DEFAULT_DOCS_PATH)
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Create filename from request info
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{request['reqid']}_{request['reqphase']}_{timestamp}.md"
    filepath = docs_dir / filename

    # Build document content
    doc_content = f"""# {request['reqname']} - {request['reqphase'].title()} Phase

**Request ID**: {request['reqid']}
**Project**: {request.get('prjname', 'Unknown')}
**Phase**: {request['reqphase']}
**Generated**: {datetime.now().isoformat()}

---

{content}
"""

    filepath.write_text(doc_content)
    return str(filepath)


def cleanup_old_docs(retention_days: int | None = None) -> int:
    """Delete docs older than the retention period.

    Args:
        retention_days: Number of days to retain docs. If None, uses setting.
                       If 0, cleanup is disabled.

    Returns:
        Number of files deleted.
    """
    import time
    from datetime import datetime

    from ..constants import DEFAULT_DOCS_PATH
    from ..logging_util import get_logger
    from ..settings import get_doc_retention_days

    logger = get_logger()

    # Get retention days from setting if not provided
    if retention_days is None:
        retention_days = get_doc_retention_days()

    # If 0, cleanup is disabled
    if retention_days <= 0:
        return 0

    docs_dir = Path(DEFAULT_DOCS_PATH)
    if not docs_dir.exists():
        return 0

    # Calculate cutoff time
    cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
    deleted_count = 0

    # Find and delete old files
    for filepath in docs_dir.glob("*.md"):
        try:
            if filepath.stat().st_mtime < cutoff_time:
                filepath.unlink()
                deleted_count += 1
                logger.debug(f"Deleted old doc: {filepath.name}")
        except OSError as e:
            logger.warning(f"Failed to delete {filepath}: {e}")

    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} doc(s) older than {retention_days} days")

    return deleted_count
