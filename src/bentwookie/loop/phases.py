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
    return Path(__file__).parent.parent / "templates" / "phases"


def load_phase_template(phase: str) -> str:
    """Load the template for a given phase.

    Args:
        phase: Phase name (plan, dev, test, deploy, verify, document).

    Returns:
        Template content as string.

    Raises:
        FileNotFoundError: If template doesn't exist.
    """
    template_path = get_templates_dir() / f"{phase}.md"
    return template_path.read_text()


def get_phase_prompt(request: dict) -> str:
    """Build the complete prompt for processing a request in its current phase.

    Args:
        request: Request dict from database (includes joined project fields).

    Returns:
        Formatted prompt string.
    """
    phase = request["reqphase"]
    template = load_phase_template(phase)

    # Get project infrastructure for deploy phase
    infrastructure = ""
    if phase == "deploy":
        infra_list = queries.get_project_infrastructure(request["prjid"])
        if infra_list:
            infrastructure = "\n".join(
                f"- **{i['inftype']}**: {i['infprovider']} ({i['infval'] or 'default'})"
                for i in infra_list
            )
        else:
            infrastructure = "- Local development environment"

    # Get project learnings for context
    learnings = queries.get_project_learnings(request["prjid"])
    learnings_text = ""
    if learnings:
        learnings_text = "\n\n## Project Learnings\n" + "\n".join(
            f"- {l['lrndesc']}" for l in learnings[:10]  # Limit to recent 10
        )

    # Format the template
    prompt = template.format(
        project_name=request.get("prjname", "Unknown"),
        project_version=request.get("prjversion", "poc"),
        project_phase=request.get("project_phase", "dev"),
        request_name=request["reqname"],
        request_type=TYPE_NAMES.get(request["reqtype"], request["reqtype"]),
        request_prompt=request["reqprompt"],
        code_dir=request.get("reqcodedir") or ".",
        infrastructure=infrastructure,
    )

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


def get_next_phase(current_phase: str) -> str | None:
    """Get the next phase in the workflow.

    Args:
        current_phase: Current phase name.

    Returns:
        Next phase name, or None if complete.
    """
    return NEXT_PHASE.get(current_phase)


def get_system_prompt(request: dict) -> str:
    """Generate the system prompt for Claude.

    Args:
        request: Request dict from database.

    Returns:
        System prompt string.
    """
    phase = request["reqphase"]
    project_name = request.get("prjname", "Unknown")

    return f"""You are an AI assistant working on the {project_name} project.

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
