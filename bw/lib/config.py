"""Typed configuration loading for BentWookie."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ContainerConfig:
    name: str
    dangerously_skip_permissions: bool = True
    sleep_seconds: int = 120
    model: str = "sonnet"
    weekly_tokens_consumed: str = ""


@dataclass
class WorkDirs:
    queue: str = "./bw/work/queue/"
    wip: str = "./bw/work/wip/"
    done: str = "./bw/work/done/"
    error: str = "./bw/work/error/"
    review: str = "./bw/work/review/"


@dataclass
class ImageConfig:
    name: str = "bw:0.3.0"
    volumes: list[str] = field(default_factory=lambda: ["./bw:/app/bw"])


@dataclass
class NotificationsConfig:
    enabled: bool = False
    type: str = "stub"


@dataclass
class BWConfig:
    version: str = "0.3.0"
    active_container: str = "dev"
    image: ImageConfig = field(default_factory=ImageConfig)
    containers: list[ContainerConfig] = field(default_factory=list)
    work_dirs: WorkDirs = field(default_factory=WorkDirs)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    init_files: list[str] = field(default_factory=list)

    def get_active_container(self) -> ContainerConfig:
        """Return the container config matching active_container name."""
        for c in self.containers:
            if c.name == self.active_container:
                return c
        raise ValueError(f"No container named '{self.active_container}' in config")


def get_bw_path(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) to find the directory containing a 'bw/' child.

    Returns the path to the 'bw/' directory itself.
    """
    current = start or Path.cwd()
    # Check if current dir IS the bw dir
    if current.name == "bw" and (current / "lib").is_dir():
        return current
    # Walk up looking for a child named 'bw'
    for parent in [current, *current.parents]:
        candidate = parent / "bw"
        if candidate.is_dir() and (candidate / "lib").is_dir():
            return candidate
    raise FileNotFoundError("Could not find a 'bw/' directory with 'lib/' inside it")


def load_config(bw_path: Path | None = None) -> BWConfig:
    """Read config.yaml and return a typed BWConfig. Re-reads every call."""
    if bw_path is None:
        bw_path = get_bw_path()
    config_file = bw_path / "lib" / "config.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    raw = yaml.safe_load(config_file.read_text())

    # Parse bentwookie top-level
    bw_section = raw.get("bentwookie", {})
    version = str(bw_section.get("version", "0.3.0"))
    active = bw_section.get("active_container", "dev")

    # Parse image
    img_raw = raw.get("image", {})
    image = ImageConfig(
        name=img_raw.get("name", "bw:0.3.0"),
        volumes=img_raw.get("volumes", ["./bw:/app/bw"]),
    )

    # Parse containers
    containers = []
    for c in raw.get("containers", []):
        containers.append(ContainerConfig(
            name=c.get("name", "unnamed"),
            dangerously_skip_permissions=c.get("dangerously_skip_permissions",
                                               c.get("dangerously-skip-permissions", True)),
            sleep_seconds=int(c.get("sleep_seconds", 120)),
            model=c.get("model", "sonnet"),
            weekly_tokens_consumed=str(c.get("weekly_tokens_consumed", "")),
        ))

    # Parse work_dirs
    wd_raw = raw.get("work_dirs", {})
    work_dirs = WorkDirs(
        queue=wd_raw.get("queue", "./bw/work/queue/"),
        wip=wd_raw.get("wip", "./bw/work/wip/"),
        done=wd_raw.get("done", "./bw/work/done/"),
        error=wd_raw.get("error", "./bw/work/error/"),
        review=wd_raw.get("review", "./bw/work/review/"),
    )

    # Parse notifications
    notif_raw = raw.get("notifications", {})
    notifications = NotificationsConfig(
        enabled=notif_raw.get("enabled", False),
        type=notif_raw.get("type", "stub"),
    )

    # Init files
    init_files = raw.get("init_files", [])

    return BWConfig(
        version=version,
        active_container=active,
        image=image,
        containers=containers,
        work_dirs=work_dirs,
        notifications=notifications,
        init_files=init_files,
    )
