"""Custom exceptions for BentWookie package."""


class BentWookieError(Exception):
    """Base exception for all BentWookie errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class TaskParseError(BentWookieError):
    """Raised when a task file cannot be parsed."""

    def __init__(self, file_path: str, reason: str):
        super().__init__(
            f"Failed to parse task file: {reason}",
            {"file_path": file_path, "reason": reason},
        )
        self.file_path = file_path
        self.reason = reason


class TaskValidationError(BentWookieError):
    """Raised when a task fails validation."""

    def __init__(self, task_name: str, field: str, reason: str):
        super().__init__(
            f"Task validation failed for '{task_name}': {reason}",
            {"task_name": task_name, "field": field, "reason": reason},
        )
        self.task_name = task_name
        self.field = field
        self.reason = reason


class TaskNotFoundError(BentWookieError):
    """Raised when a requested task cannot be found."""

    def __init__(self, task_identifier: str):
        super().__init__(
            f"Task not found: {task_identifier}",
            {"task_identifier": task_identifier},
        )
        self.task_identifier = task_identifier


class StageError(BentWookieError):
    """Raised when there's an error with stage operations."""

    def __init__(self, stage: str, operation: str, reason: str):
        super().__init__(
            f"Stage operation failed: {operation} on stage '{stage}': {reason}",
            {"stage": stage, "operation": operation, "reason": reason},
        )
        self.stage = stage
        self.operation = operation
        self.reason = reason


class ConfigurationError(BentWookieError):
    """Raised when there's a configuration error."""

    def __init__(self, config_key: str, reason: str):
        super().__init__(
            f"Configuration error for '{config_key}': {reason}",
            {"config_key": config_key, "reason": reason},
        )
        self.config_key = config_key
        self.reason = reason


class TemplateError(BentWookieError):
    """Raised when there's an error with templates."""

    def __init__(self, template_path: str, reason: str):
        super().__init__(
            f"Template error at '{template_path}': {reason}",
            {"template_path": template_path, "reason": reason},
        )
        self.template_path = template_path
        self.reason = reason


class RaceConditionError(BentWookieError):
    """Raised when a race condition is detected."""

    def __init__(self, task_name: str, expected_status: str, actual_status: str):
        super().__init__(
            f"Race condition detected for task '{task_name}': "
            f"expected status '{expected_status}', found '{actual_status}'",
            {
                "task_name": task_name,
                "expected_status": expected_status,
                "actual_status": actual_status,
            },
        )
        self.task_name = task_name
        self.expected_status = expected_status
        self.actual_status = actual_status


class WizardError(BentWookieError):
    """Raised when there's an error in the planning wizard."""

    def __init__(self, step: str, reason: str):
        super().__init__(
            f"Wizard error at step '{step}': {reason}",
            {"step": step, "reason": reason},
        )
        self.step = step
        self.reason = reason
