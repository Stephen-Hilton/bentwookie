"""Whitespace functions for BentWookie.

These functions execute actual maintenance tasks when no prioritized
tasks are in the queue. They perform real work and return results
that can be included in prompts for AI review.
"""

import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from .config import get_config
from .constants import LEARNINGS_FILE, STAGES
from .logging_util import get_logger


# Type alias for whitespace function
WhitespaceFunc = Callable[[], str]


def clean_temp_files() -> str:
    """Find and list temporary files that could be cleaned up.

    Returns:
        Summary of temp files found
    """
    logger = get_logger()
    config = get_config()

    temp_patterns = [
        "*.tmp", "*.temp", "*.bak", "*.swp", "*.swo",
        "*~", "*.pyc", "__pycache__", ".DS_Store",
        "*.log.old", "*.backup", ".*.swp",
    ]

    found_files: list[str] = []
    search_root = config.tasks_path.parent  # Project root

    for pattern in temp_patterns:
        for path in search_root.rglob(pattern):
            if path.is_file():
                found_files.append(str(path.relative_to(search_root)))

    if not found_files:
        logger.info("No temporary files found")
        return "No temporary files found in project directory."

    logger.info(f"Found {len(found_files)} temporary files")

    result = f"Found {len(found_files)} temporary file(s):\n"
    for f in found_files[:20]:  # Limit to 20 files
        result += f"  - {f}\n"
    if len(found_files) > 20:
        result += f"  ... and {len(found_files) - 20} more\n"

    return result


def check_log_errors() -> str:
    """Scan log files for errors and warnings.

    Returns:
        Summary of errors/warnings found
    """
    logger = get_logger()
    config = get_config()

    log_dir = config.tasks_path.parent / "logs"
    if not log_dir.exists():
        return "No logs directory found."

    error_patterns = [
        (r"\bERROR\b", "ERROR"),
        (r"\bWARNING\b", "WARNING"),
        (r"\bFAILED\b", "FAILED"),
        (r"\bException\b", "Exception"),
        (r"\bTraceback\b", "Traceback"),
    ]

    findings: dict[str, list[str]] = {p[1]: [] for p in error_patterns}

    # Check logs from last 24 hours
    cutoff = datetime.now() - timedelta(hours=24)

    for log_file in log_dir.glob("*.log"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                continue

            content = log_file.read_text(encoding="utf-8", errors="ignore")
            for pattern, label in error_patterns:
                matches = re.findall(f".*{pattern}.*", content, re.IGNORECASE)
                findings[label].extend(matches[:5])  # Max 5 per pattern per file
        except OSError:
            continue

    total_issues = sum(len(v) for v in findings.values())

    if total_issues == 0:
        logger.info("No log errors found in last 24 hours")
        return "No errors or warnings found in logs from the last 24 hours."

    logger.info(f"Found {total_issues} log issues")

    result = f"Found {total_issues} issue(s) in recent logs:\n\n"
    for label, matches in findings.items():
        if matches:
            result += f"**{label}** ({len(matches)} occurrences):\n"
            for m in matches[:3]:
                result += f"  {m[:100]}...\n" if len(m) > 100 else f"  {m}\n"
            result += "\n"

    return result


def deduplicate_learnings() -> str:
    """Find duplicate entries in learnings.md files.

    Returns:
        Summary of duplicates found
    """
    logger = get_logger()
    config = get_config()

    learnings_files: list[Path] = []

    # Global learnings
    global_learnings = config.global_dir / LEARNINGS_FILE
    if global_learnings.exists():
        learnings_files.append(global_learnings)

    # Stage learnings
    for stage in STAGES:
        stage_learnings = config.tasks_path / stage / ".resources" / LEARNINGS_FILE
        if stage_learnings.exists():
            learnings_files.append(stage_learnings)

    if not learnings_files:
        return "No learnings.md files found."

    all_duplicates: dict[str, list[tuple[str, int]]] = {}

    for lf in learnings_files:
        try:
            lines = lf.read_text(encoding="utf-8").splitlines()
            bullet_lines = [
                (i, line.strip())
                for i, line in enumerate(lines, 1)
                if line.strip().startswith("- ")
            ]

            # Find duplicates
            seen: dict[str, list[int]] = {}
            for line_num, line in bullet_lines:
                normalized = line.lower().strip()
                if normalized not in seen:
                    seen[normalized] = []
                seen[normalized].append(line_num)

            for line, nums in seen.items():
                if len(nums) > 1:
                    rel_path = str(lf.relative_to(config.tasks_path))
                    if rel_path not in all_duplicates:
                        all_duplicates[rel_path] = []
                    all_duplicates[rel_path].append((line[:60], len(nums)))
        except OSError:
            continue

    if not all_duplicates:
        logger.info("No duplicate learnings found")
        return "No duplicate entries found in learnings.md files."

    logger.info(f"Found duplicates in {len(all_duplicates)} files")

    result = "Found duplicate entries in learnings files:\n\n"
    for filepath, dups in all_duplicates.items():
        result += f"**{filepath}**:\n"
        for text, count in dups[:5]:
            result += f"  - \"{text}...\" appears {count} times\n"
        result += "\n"

    return result


def check_outdated_deps() -> str:
    """Check for potentially outdated dependencies.

    Returns:
        Summary of dependency status
    """
    logger = get_logger()
    config = get_config()
    project_root = config.tasks_path.parent

    findings: list[str] = []

    # Check pyproject.toml
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")
            # Extract dependency versions
            deps = re.findall(r'^\s*"?([a-zA-Z0-9_-]+)\s*[><=]+\s*([\d.]+)"?,?\s*$',
                            content, re.MULTILINE)
            if deps:
                findings.append(f"pyproject.toml has {len(deps)} pinned dependencies")
        except OSError:
            pass

    # Check requirements.txt
    requirements = project_root / "requirements.txt"
    if requirements.exists():
        try:
            content = requirements.read_text(encoding="utf-8")
            lines = [l for l in content.splitlines() if l.strip() and not l.startswith("#")]
            pinned = [l for l in lines if "==" in l]
            findings.append(f"requirements.txt: {len(pinned)} pinned, {len(lines) - len(pinned)} unpinned")
        except OSError:
            pass

    # Check package.json
    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            import json
            content = json.loads(package_json.read_text(encoding="utf-8"))
            deps_count = len(content.get("dependencies", {}))
            dev_deps_count = len(content.get("devDependencies", {}))
            findings.append(f"package.json: {deps_count} deps, {dev_deps_count} devDeps")
        except (OSError, json.JSONDecodeError):
            pass

    if not findings:
        logger.info("No dependency files found")
        return "No dependency configuration files found (pyproject.toml, requirements.txt, package.json)."

    logger.info(f"Checked {len(findings)} dependency files")

    result = "Dependency file analysis:\n"
    for f in findings:
        result += f"  - {f}\n"
    result += "\nNote: Run appropriate tools (pip-audit, npm audit) for security checks."

    return result


def summarize_todos() -> str:
    """Find and summarize TODO comments in the codebase.

    Returns:
        Summary of TODO comments found
    """
    logger = get_logger()
    config = get_config()

    code_dir = config.tasks_path.parent / "code"
    src_dir = config.tasks_path.parent / "src"

    search_dirs = [d for d in [code_dir, src_dir] if d.exists()]

    if not search_dirs:
        # Fall back to project root
        search_dirs = [config.tasks_path.parent]

    code_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".cpp", ".c", ".h"}

    todos: list[tuple[str, int, str]] = []  # (file, line, content)

    for search_dir in search_dirs:
        for path in search_dir.rglob("*"):
            if path.suffix not in code_extensions:
                continue
            if "__pycache__" in str(path) or "node_modules" in str(path):
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(r"\bTODO\b|\bFIXME\b|\bHACK\b|\bXXX\b", line, re.IGNORECASE):
                        rel_path = str(path.relative_to(config.tasks_path.parent))
                        todos.append((rel_path, i, line.strip()[:80]))
            except OSError:
                continue

    if not todos:
        logger.info("No TODO comments found")
        return "No TODO/FIXME/HACK comments found in codebase."

    logger.info(f"Found {len(todos)} TODO comments")

    result = f"Found {len(todos)} TODO/FIXME comment(s):\n\n"
    for filepath, line, content in todos[:15]:
        result += f"  {filepath}:{line}: {content}\n"
    if len(todos) > 15:
        result += f"\n  ... and {len(todos) - 15} more\n"

    return result


def review_git_history() -> str:
    """Summarize recent git activity.

    Returns:
        Summary of recent commits
    """
    logger = get_logger()
    config = get_config()
    project_root = config.tasks_path.parent

    # Check if git repo
    git_dir = project_root / ".git"
    if not git_dir.exists():
        return "Not a git repository."

    try:
        # Get recent commits
        result = subprocess.run(
            ["git", "log", "--oneline", "-n", "10", "--since=7.days.ago"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        commits = result.stdout.strip()

        # Get status summary
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        status_lines = status_result.stdout.strip().splitlines()

        modified = len([l for l in status_lines if l.startswith(" M") or l.startswith("M ")])
        untracked = len([l for l in status_lines if l.startswith("??")])
        staged = len([l for l in status_lines if l[0] in "AMDRC"])

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return "Unable to access git history."

    logger.info("Retrieved git history")

    output = "Git repository status:\n\n"
    output += f"Working directory: {modified} modified, {untracked} untracked, {staged} staged\n\n"

    if commits:
        output += "Recent commits (last 7 days):\n"
        for line in commits.splitlines()[:10]:
            output += f"  {line}\n"
    else:
        output += "No commits in the last 7 days.\n"

    return output


def check_test_coverage() -> str:
    """Check for test files and coverage gaps.

    Returns:
        Summary of test coverage
    """
    logger = get_logger()
    config = get_config()
    project_root = config.tasks_path.parent

    # Find source files
    src_dir = project_root / "src"
    code_dir = project_root / "code"
    source_dirs = [d for d in [src_dir, code_dir] if d.exists()]

    # Find test files
    test_dir = project_root / "test"
    tests_dir = project_root / "tests"
    test_dirs = [d for d in [test_dir, tests_dir] if d.exists()]

    source_files: set[str] = set()
    for src in source_dirs:
        for path in src.rglob("*.py"):
            if "__pycache__" not in str(path):
                source_files.add(path.stem)

    test_files: set[str] = set()
    for tdir in test_dirs:
        for path in tdir.rglob("test_*.py"):
            # Extract module name being tested
            name = path.stem.replace("test_", "")
            test_files.add(name)

    if not source_files:
        return "No source files found to analyze."

    # Find untested modules
    untested = source_files - test_files - {"__init__", "__main__"}

    logger.info(f"Found {len(source_files)} source files, {len(test_files)} test files")

    result = f"Test coverage analysis:\n"
    result += f"  Source modules: {len(source_files)}\n"
    result += f"  Test files: {len(test_files)}\n"

    if untested:
        result += f"\nModules without dedicated tests:\n"
        for mod in sorted(untested)[:10]:
            result += f"  - {mod}\n"
        if len(untested) > 10:
            result += f"  ... and {len(untested) - 10} more\n"
    else:
        result += "\nAll modules appear to have test coverage.\n"

    return result


def check_code_style() -> str:
    """Basic code style consistency check.

    Returns:
        Summary of style observations
    """
    logger = get_logger()
    config = get_config()
    project_root = config.tasks_path.parent

    observations: list[str] = []

    # Check for style configs
    style_configs = [
        ("pyproject.toml", "Python project config"),
        (".flake8", "Flake8 config"),
        ("setup.cfg", "Setup config"),
        (".prettierrc", "Prettier config"),
        (".eslintrc.js", "ESLint config"),
        (".eslintrc.json", "ESLint config"),
        ("ruff.toml", "Ruff config"),
    ]

    found_configs = []
    for filename, desc in style_configs:
        if (project_root / filename).exists():
            found_configs.append(desc)

    if found_configs:
        observations.append(f"Style configs found: {', '.join(found_configs)}")
    else:
        observations.append("No style configuration files found")

    # Sample check: line lengths in Python files
    long_lines = 0
    files_checked = 0

    for src_dir in [project_root / "src", project_root / "code"]:
        if not src_dir.exists():
            continue
        for path in src_dir.rglob("*.py"):
            if "__pycache__" in str(path):
                continue
            try:
                files_checked += 1
                content = path.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    if len(line) > 120:
                        long_lines += 1
            except OSError:
                continue

    if files_checked > 0:
        observations.append(f"Checked {files_checked} Python files, found {long_lines} lines > 120 chars")

    logger.info("Completed code style check")

    result = "Code style observations:\n"
    for obs in observations:
        result += f"  - {obs}\n"

    return result


def do_nothing() -> str:
    """A no-op whitespace function for when idle time is desired.

    Returns:
        Simple acknowledgment message
    """
    return "Taking a brief pause. No maintenance action needed."


# Registry of all whitespace functions with descriptions
WHITESPACE_FUNCTIONS: dict[str, tuple[WhitespaceFunc, str]] = {
    "clean_temp_files": (clean_temp_files, "Find temporary files that could be cleaned up"),
    "check_log_errors": (check_log_errors, "Scan recent logs for errors and warnings"),
    "deduplicate_learnings": (deduplicate_learnings, "Find duplicate entries in learnings files"),
    "check_outdated_deps": (check_outdated_deps, "Analyze dependency configuration files"),
    "summarize_todos": (summarize_todos, "Find TODO/FIXME comments in codebase"),
    "review_git_history": (review_git_history, "Summarize recent git activity"),
    "check_test_coverage": (check_test_coverage, "Analyze test coverage gaps"),
    "check_code_style": (check_code_style, "Basic code style consistency check"),
    "do_nothing": (do_nothing, "Take a brief pause, no action needed"),
}


def get_whitespace_function_names() -> list[str]:
    """Get list of available whitespace function names.

    Returns:
        List of function names
    """
    return list(WHITESPACE_FUNCTIONS.keys())


def run_whitespace_function(name: str) -> str:
    """Run a specific whitespace function by name.

    Args:
        name: Function name from WHITESPACE_FUNCTIONS

    Returns:
        Function result string

    Raises:
        KeyError: If function name not found
    """
    if name not in WHITESPACE_FUNCTIONS:
        raise KeyError(f"Unknown whitespace function: {name}")

    func, _ = WHITESPACE_FUNCTIONS[name]
    return func()


def run_random_whitespace_function() -> tuple[str, str]:
    """Run a random whitespace function.

    Returns:
        Tuple of (function_name, result_string)
    """
    import random

    name = random.choice(list(WHITESPACE_FUNCTIONS.keys()))
    func, _ = WHITESPACE_FUNCTIONS[name]

    return name, func()


def run_all_whitespace_functions() -> dict[str, str]:
    """Run all whitespace functions and collect results.

    Returns:
        Dictionary mapping function names to their results
    """
    results = {}
    for name, (func, _) in WHITESPACE_FUNCTIONS.items():
        try:
            results[name] = func()
        except Exception as e:
            results[name] = f"Error: {e}"

    return results
