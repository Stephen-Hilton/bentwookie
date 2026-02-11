"""BentWookie CLI — Click-based entry point."""

import logging
import re
import shutil
import sys
from pathlib import Path

import click

from bw.lib.config import get_bw_path, get_package_lib_path, load_config
from bw.lib.docker_manager import (
    build_image,
    ensure_credential_volume,
    run_interactive_login,
)
from bw.lib.engine import get_status, run_loop
from bw.lib.workitem import create_workitem_from_instructions, generate_workitem_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bw")


@click.group()
@click.version_option(version="0.3.0", prog_name="bentwookie")
def main():
    """BentWookie — AI auto-coding framework."""


@main.command()
def init():
    """Scaffold the bw/ directory, build Docker image, create credential volumes."""
    try:
        cwd = Path.cwd()
    except FileNotFoundError:
        click.echo("Error: Current directory no longer exists. Please cd into a valid directory.", err=True)
        sys.exit(1)
    bw_path = cwd / "bw"
    pkg_lib = get_package_lib_path()  # installed bw/lib/ with default files

    # 1. Create bw/lib/ structure
    lib_path = bw_path / "lib"
    lib_path.mkdir(parents=True, exist_ok=True)
    click.echo(f"  Directory ready: {lib_path}")

    # 2. Copy default files if they don't already exist
    defaults = {
        "config.yaml": pkg_lib / "config.yaml",
        "prompt_snippets.yaml": pkg_lib / "prompt_snippets.yaml",
        "Dockerfile": pkg_lib / "Dockerfile",
    }
    for name, src in defaults.items():
        dest = lib_path / name
        if not dest.exists():
            shutil.copy2(src, dest)
            click.echo(f"  Created: {dest}")
        else:
            click.echo(f"  Exists:  {dest}")

    # 3. Copy templates directory
    templates_dest = lib_path / "templates"
    templates_src = pkg_lib / "templates"
    if templates_src.is_dir():
        if not templates_dest.exists():
            shutil.copytree(templates_src, templates_dest)
            click.echo(f"  Created: {templates_dest}/")
        else:
            click.echo(f"  Exists:  {templates_dest}/")

    # 4. Create work directories
    for subdir in ["queue", "wip", "done", "error", "review"]:
        d = bw_path / "work" / subdir
        d.mkdir(parents=True, exist_ok=True)
        click.echo(f"  Directory ready: {d}")

    # 5. Load config (now that bw/lib/config.yaml exists)
    config = load_config(bw_path)

    # 6. Build Docker image (Dockerfile lives inside bw/lib/)
    dockerfile = lib_path / "Dockerfile"
    if dockerfile.exists():
        click.echo(f"\nBuilding Docker image '{config.image.name}'...")
        if build_image(dockerfile, config.image.name):
            click.echo("  Image built successfully.")
        else:
            click.echo("  Image build FAILED. Check Docker output above.", err=True)
    else:
        click.echo("\nWarning: No Dockerfile found at {dockerfile}. Skipping image build.", err=True)

    # 8. Create credential volumes for all containers
    click.echo("\nCreating credential volumes...")
    for container in config.containers:
        if ensure_credential_volume(container.name):
            click.echo(f"  Volume ready: bw-creds-{container.name}")

    click.echo("\nBW init complete.")


def _parse_instructions_metadata(text: str) -> tuple[str | None, str | None]:
    """Extract workitem_name and code_path from an instructions file's frontmatter."""
    from bw.lib.workitem import parse_frontmatter
    fm, _ = parse_frontmatter(text)
    name = fm.get("workitem_name")
    code_path = fm.get("code_path")
    # Treat placeholder values as missing
    if name and name.lower() in ("xxx", ""):
        name = None
    if code_path and code_path in ("/some/path/", ""):
        code_path = None
    return name, code_path


@main.command()
@click.option("--name", "-n", default=None, help="Name for the workitem")
@click.option("--code", "-c", default=None, type=click.Path(exists=True, file_okay=False),
              help="Path to the code directory")
def new(name, code):
    """Create a new instructions file from the workitem template.

    Fills in whatever is provided. Omitted fields are left as placeholders.
    """
    try:
        bw_path = get_bw_path()
    except FileNotFoundError:
        bw_path = None

    # Determine the template source
    pkg_lib = get_package_lib_path()
    template_src = None
    if bw_path:
        candidate = bw_path / "lib" / "templates" / "workitem.md"
        if candidate.exists():
            template_src = candidate
    if not template_src:
        candidate = pkg_lib / "templates" / "workitem.md"
        if candidate.exists():
            template_src = candidate

    if not template_src:
        click.echo("Error: Could not find workitem.md template.", err=True)
        sys.exit(1)

    text = template_src.read_text()

    # Fill in provided values
    if name:
        text = text.replace("workitem_name: xxx", f"workitem_name: {name}")
    if code:
        code_path = str(Path(code).resolve())
        text = text.replace("code_path: /some/path/", f"code_path: {code_path}")

    slug = re.sub(r"[^a-z0-9]+", "-", (name or "instructions").lower()).strip("-")[:60]
    dest = Path.cwd() / f"{slug}.md"
    if dest.exists():
        click.echo(f"File already exists: {dest}")
        return
    dest.write_text(text)
    click.echo(f"Created: {dest}")


@main.command()
@click.option("--instructions", "-i", required=True, type=click.Path(exists=True, dir_okay=False),
              help="Path to the instructions file")
@click.option("--container", default=None, help="Container name (defaults to active_container)")
def queue(instructions, container):
    """Add an instructions file to the work queue."""
    from bw.lib.workitem import parse_frontmatter

    instr_text = Path(instructions).read_text()
    file_name, file_code = _parse_instructions_metadata(instr_text)

    if not file_name:
        click.echo("Error: No 'workitem_name' found in frontmatter.", err=True)
        sys.exit(1)
    if not file_code:
        click.echo("Error: No 'code_path' found in frontmatter.", err=True)
        sys.exit(1)

    code_path = str(Path(file_code).resolve())
    if not Path(code_path).is_dir():
        click.echo(f"Error: code_path is not a valid directory: {file_code}", err=True)
        sys.exit(1)

    try:
        bw_path = get_bw_path()
    except FileNotFoundError:
        click.echo("Error: Could not find a bw/ directory. Run `bw init` first.", err=True)
        sys.exit(1)

    config = load_config(bw_path)
    container_name = container or config.active_container

    # Strip frontmatter and any # INSTRUCTIONS heading — only pass the body content
    _, instr_body = parse_frontmatter(instr_text)
    # Remove leading "# INSTRUCTIONS" heading if present (template already has it)
    instr_body = re.sub(r"^\s*#\s+INSTRUCTIONS\s*\n", "", instr_body)

    content = create_workitem_from_instructions(
        bw_path=bw_path,
        name=file_name,
        code_path=code_path,
        instructions_text=instr_body.strip(),
        container_name=container_name,
        version=config.version,
    )

    filename = generate_workitem_filename(file_name)
    queue_dir = bw_path / "work" / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    dest = queue_dir / filename
    dest.write_text(content)

    click.echo(f"Workitem queued: {dest}")


@main.command()
@click.option("--instructions", "-i", required=True, type=click.Path(dir_okay=False),
              help="Path to the instructions markdown file to validate")
@click.option("--fix", is_flag=True, help="Auto-fix correctable issues in place")
def validate(instructions, fix):
    """Validate (and optionally fix) an instructions file before queuing."""
    from bw.lib.workitem import parse_frontmatter, serialize_frontmatter

    path = Path(instructions)
    if not path.exists():
        click.echo(f"FAIL: File not found: {path}", err=True)
        sys.exit(1)

    text = path.read_text()
    warnings = []   # (message, fixed:bool) tuples

    # 1. Check: non-empty
    if not text.strip():
        click.echo(f"FAIL: File is empty: {path}", err=True)
        sys.exit(1)

    # 2. Check: has frontmatter
    fm, body = parse_frontmatter(text)
    if not fm:
        fixed = False
        if fix:
            fm = {
                "workitem_name": path.stem.replace("-", " ").replace("_", " ").title(),
                "code_path": "/some/path/",
                "status": "TBD",
            }
            text = serialize_frontmatter(fm, "\n" + text)
            fm, body = parse_frontmatter(text)
            fixed = True
        warnings.append(("Missing YAML frontmatter (--- delimited block)", fixed))

    # 3. Check: workitem_name
    name = fm.get("workitem_name")
    if not name or str(name).lower() in ("xxx", ""):
        fixed = False
        if fix and not name:
            fm["workitem_name"] = path.stem.replace("-", " ").replace("_", " ").title()
            fixed = True
        warnings.append(("'workitem_name' is missing or still a placeholder (xxx)", fixed))

    # 4. Check: code_path
    code_path = fm.get("code_path")
    if not code_path or str(code_path) in ("/some/path/", ""):
        warnings.append(("'code_path' is missing or still a placeholder (/some/path/)", False))
    elif not Path(str(code_path)).is_dir():
        warnings.append((f"code_path directory does not exist: {code_path}", False))

    # 5. Check: {USER_INSTRUCTIONS} placeholder still present
    if "{USER_INSTRUCTIONS}" in body:
        warnings.append(("Body still contains {USER_INSTRUCTIONS} placeholder — replace with actual instructions", False))

    # 6. Check: body has real content beyond placeholders
    real_content = [
        line.strip() for line in body.splitlines()
        if line.strip()
        and not line.strip().startswith("#")
        and not line.strip().startswith("---")
        and not line.strip().startswith("{")
    ]
    if not real_content:
        warnings.append(("No instruction content found in body", False))

    # Write fixes
    any_fixed = any(fixed for _, fixed in warnings)
    if any_fixed:
        text = serialize_frontmatter(fm, body)
        path.write_text(text)

    # Report
    for msg, fixed in warnings:
        label = "FIXED" if fixed else "WARN"
        click.echo(f"  {label}:  {msg}")

    unfixed = [(msg, f) for msg, f in warnings if not f]
    if unfixed:
        critical = [msg for msg, _ in unfixed if "placeholder" in msg.lower() or "missing" in msg.lower()
                    or "does not exist" in msg.lower() or "USER_INSTRUCTIONS" in msg or "No instruction content" in msg]
        if critical:
            click.echo(f"\n{path.name}: {len(unfixed)} issue(s) remaining")
            sys.exit(1)
        else:
            click.echo(f"\n{path.name}: OK (with warnings)")
    elif any_fixed:
        click.echo(f"\n{path.name}: OK (after fixes)")
    else:
        click.echo(f"{path.name}: OK")


@main.command()
def status():
    """Show queue/wip/done/error/review counts and container info."""
    try:
        bw_path = get_bw_path()
    except FileNotFoundError:
        click.echo("Error: Could not find a bw/ directory.", err=True)
        sys.exit(1)

    config = load_config(bw_path)
    s = get_status(bw_path)

    click.echo(f"BentWookie v{config.version}")
    click.echo(f"Active container: {config.active_container}\n")
    click.echo("Work items:")
    click.echo(f"  Queue:  {s['queue']}")
    click.echo(f"  WIP:    {s['wip']}")
    click.echo(f"  Done:   {s['done']}")
    click.echo(f"  Error:  {s['error']}")
    click.echo(f"  Review: {s['review']}")
    click.echo(f"\nContainers:\n  {s['containers']}")


@main.command()
@click.argument("mode", default="once")
def run(mode):
    """Process workitems. MODE: 'once' (1 item), a number, or 'loop' (infinite)."""
    try:
        bw_path = get_bw_path()
    except FileNotFoundError:
        click.echo("Error: Could not find a bw/ directory.", err=True)
        sys.exit(1)

    if mode == "once":
        max_iter = 1
    elif mode == "loop":
        max_iter = 0
    else:
        try:
            max_iter = int(mode)
        except ValueError:
            click.echo(f"Invalid mode: '{mode}'. Use 'once', a number, or 'loop'.", err=True)
            sys.exit(1)

    click.echo(f"Starting BW engine (max_iterations={max_iter or 'infinite'})...")
    run_loop(bw_path, max_iterations=max_iter)
    click.echo("Engine stopped.")


@main.command()
@click.argument("container_name")
def login(container_name):
    """Run interactive `claude login` in a container for credential setup."""
    try:
        bw_path = get_bw_path()
    except FileNotFoundError:
        click.echo("Error: Could not find a bw/ directory.", err=True)
        sys.exit(1)

    config = load_config(bw_path)

    # Validate container name
    valid_names = [c.name for c in config.containers]
    if container_name not in valid_names:
        click.echo(f"Unknown container '{container_name}'. Valid: {', '.join(valid_names)}", err=True)
        sys.exit(1)

    click.echo(f"Launching interactive login for '{container_name}'...")
    run_interactive_login(container_name, config.image.name)


if __name__ == "__main__":
    main()
