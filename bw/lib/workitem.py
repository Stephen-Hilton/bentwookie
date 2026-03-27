"""Workitem parsing, validation, creation, and next-step extraction."""

import logging
import re
from datetime import datetime
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

_FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from text.

    Returns (frontmatter_dict, body_after_frontmatter).
    """
    match = _FM_PATTERN.match(text)
    if not match:
        return {}, text
    fm = yaml.safe_load(match.group(1)) or {}
    body = text[match.end():]
    return fm, body


def serialize_frontmatter(fm: dict, body: str) -> str:
    """Serialize frontmatter dict + body back into a workitem string."""
    fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False).rstrip()
    return f"---\n{fm_yaml}\n---\n{body}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_frontmatter(fm: dict) -> list[str]:
    """Validate required frontmatter fields. Returns list of error messages."""
    errors = []
    code_path = fm.get("code_path")
    if not code_path:
        errors.append("code_path is required in frontmatter")
    elif not Path(str(code_path)).is_dir():
        errors.append(f"code_path does not exist or is not a directory: {code_path}")
    return errors


def fill_optional_frontmatter(fm: dict, container_name: str, version: str) -> dict:
    """Fill in optional frontmatter fields with defaults."""
    fm.setdefault("status", "queued")
    fm.setdefault("container_name", container_name)
    fm.setdefault("bwversion", version)
    fm.setdefault("started_at", "")
    fm.setdefault("complete_at", "")
    return fm


# ---------------------------------------------------------------------------
# Section injection
# ---------------------------------------------------------------------------

def has_section(text: str, heading: str) -> bool:
    """Check whether a markdown heading already exists in text."""
    pattern = rf"^# {re.escape(heading)}\s*$"
    return bool(re.search(pattern, text, re.MULTILINE))


def inject_preamble(body: str, preamble: str) -> str:
    """Replace the {PREAMBLE} placeholder or inject the preamble section.

    Idempotent — skips if preamble content is already present.
    """
    if "{PREAMBLE}" in body:
        return body.replace("{PREAMBLE}", preamble)
    if has_section(body, "PREAMBLE"):
        return body
    return f"# PREAMBLE\n{preamble}\n\n---\n\n{body}"


def inject_final_tasks(body: str, final_tasks: str) -> str:
    """Replace the {FINAL_TASKS} placeholder or inject the final tasks section.

    Idempotent — skips if already present.
    """
    if "{FINAL_TASKS}" in body:
        return body.replace("{FINAL_TASKS}", final_tasks)
    if has_section(body, "FINAL TASKS"):
        return body
    return f"{body}\n\n---\n\n# FINAL TASKS\n{final_tasks}\n"


# ---------------------------------------------------------------------------
# Prompt snippets
# ---------------------------------------------------------------------------

def load_prompt_snippets(bw_path: Path) -> dict:
    """Load prompt_snippets.yaml from the bw/lib directory."""
    snippets_file = bw_path / "lib" / "prompt_snippets.yaml"
    if not snippets_file.exists():
        log.warning("prompt_snippets.yaml not found at %s", snippets_file)
        return {}
    return yaml.safe_load(snippets_file.read_text()) or {}


# ---------------------------------------------------------------------------
# Workitem creation
# ---------------------------------------------------------------------------

def generate_workitem_filename(name: str) -> str:
    """Generate a timestamped, slugified filename for a workitem.

    Format: YYYYMMDD_HHMMSS_slugified-name.md
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Slugify: lowercase, replace non-alnum with hyphens, collapse multiples
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug = slug[:60]  # cap length
    return f"{timestamp}_{slug}.md"


def create_workitem_from_instructions(
    bw_path: Path,
    name: str,
    code_path: str,
    instructions_text: str,
    filename: str,
    container_name: str = "dev",
    version: str = "0.3.0",
) -> str:
    """Create a clean workitem file: frontmatter + instructions only.

    PREAMBLE and FINAL TASKS are NOT included in the file — they are
    sent as separate prompts by the Docker runner at execution time.
    This keeps the workitem file as a clean record of work requested
    and (after processing) work completed.

    Args:
        filename: The exact filename this workitem will be saved as.
    """
    fm = {
        "workitem_name": name,
        "container_name": container_name,
        "bwversion": version,
        "status": "queued",
        "code_path": code_path,
        "started_at": "",
        "complete_at": "",
    }

    body = f"""# INSTRUCTIONS
{instructions_text}

"""

    return serialize_frontmatter(fm, body)


# ---------------------------------------------------------------------------
# Next-step parsing
# ---------------------------------------------------------------------------

_NEXTSTEP_PATTERN = re.compile(
    r"```nextstep\s*\n(.*?)```",
    re.DOTALL,
)


def parse_next_steps(text: str) -> list[dict]:
    """Parse ```nextstep fenced blocks from workitem text.

    Each block should contain YAML with at least an 'instructions' field.
    Returns a list of parsed dicts.
    """
    steps = []
    for match in _NEXTSTEP_PATTERN.finditer(text):
        block = match.group(1).strip()
        try:
            parsed = yaml.safe_load(block)
            if isinstance(parsed, dict):
                steps.append(parsed)
            else:
                log.warning("nextstep block is not a dict: %s", block[:100])
        except yaml.YAMLError as e:
            log.debug("Skipping unparseable nextstep block: %s", e)
    return steps


def _classify_step(step: dict, text: str) -> str:
    """Determine if a step is 'required' or 'recommended'.

    Checks context from the NEXT STEPS section headings.
    """
    # If the step dict has an explicit type, use it
    if step.get("type") in ("required", "recommended"):
        return step["type"]

    # Try to figure it out from which section it appeared in
    name = step.get("workitem_name", "")
    req_match = re.search(r"## Required.*?" + re.escape(name), text, re.DOTALL)
    if req_match:
        return "required"
    return "recommended"


def create_next_step_workitems(
    workitem_text: str,
    bw_path: Path,
    config_version: str = "0.3.0",
) -> list[Path]:
    """Parse next steps from a completed workitem and create new workitem files.

    Required steps → queue/, Recommended steps → review/.
    code_path is always inherited from the parent workitem's frontmatter.
    Returns list of created file paths.
    """
    steps = parse_next_steps(workitem_text)
    if not steps:
        return []

    # Inherit code_path from parent workitem
    parent_fm, _ = parse_frontmatter(workitem_text)
    parent_code_path = parent_fm.get("code_path", "")

    created = []
    for step in steps:
        name = step.get("workitem_name", "untitled-nextstep")
        code_path = parent_code_path
        instructions = step.get("instructions", "")
        step_type = _classify_step(step, workitem_text)

        if not instructions:
            log.warning("Skipping nextstep with no instructions: %s", name)
            continue

        filename = generate_workitem_filename(name)

        content = create_workitem_from_instructions(
            bw_path=bw_path,
            name=name,
            code_path=code_path,
            instructions_text=instructions,
            filename=filename,
            version=config_version,
        )
        if step_type == "required":
            dest = bw_path / "work" / "queue" / filename
        else:
            dest = bw_path / "work" / "review" / filename

        dest.write_text(content)
        log.info("Created %s workitem: %s", step_type, dest)
        created.append(dest)

    return created
