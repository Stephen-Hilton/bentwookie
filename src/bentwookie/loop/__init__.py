"""Loop module for BentWookie daemon and request processing."""

from .daemon import BentWookieDaemon, start_daemon, stop_daemon
from .phases import (
    get_next_phase,
    get_phase_prompt,
    get_phase_timeout,
    get_phase_tools,
    get_system_prompt,
    load_phase_template,
)
from .processor import process_request

__all__ = [
    # Daemon
    "BentWookieDaemon",
    "start_daemon",
    "stop_daemon",
    # Processor
    "process_request",
    # Phases
    "get_phase_prompt",
    "get_phase_tools",
    "get_phase_timeout",
    "get_system_prompt",
    "get_next_phase",
    "load_phase_template",
]
