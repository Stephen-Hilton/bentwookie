"""Planning wizard for creating new BentWookie tasks."""

from typing import Any

import questionary
from questionary import Style

from .config import get_config
from .constants import (
    DEFAULT_PRIORITY,
    PRIORITY_MAX,
    PRIORITY_MIN,
    PROJECT_PHASES,
    VALID_CHANGE_TYPES,
)
from .core import Task, create_task_file, get_stage_resources
from .exceptions import WizardError

# Custom style for the wizard
WIZARD_STYLE = Style([
    ("qmark", "fg:yellow bold"),
    ("question", "bold"),
    ("answer", "fg:cyan bold"),
    ("pointer", "fg:yellow bold"),
    ("highlighted", "fg:yellow bold"),
    ("selected", "fg:green"),
    ("separator", "fg:gray"),
    ("instruction", "fg:gray"),
])


class PlanningWizard:
    """Interactive wizard for creating new task plans.

    Guides users through a series of questions to create a properly
    formatted task file in the 1plan/ directory.
    """

    def __init__(self, feature_name: str | None = None):
        """Initialize the wizard.

        Args:
            feature_name: Optional pre-set feature name
        """
        self.config = get_config()
        self._feature_name = feature_name
        self._answers: dict[str, Any] = {}
        self._is_bugfix = False

    def _get_options(self, category: str, setting_key: str) -> list[str]:
        """Get options for a category, with last-selected first.

        Args:
            category: Options category (e.g., 'change_type', 'phase')
            setting_key: Key in settings.yaml

        Returns:
            List of options, with most recent first
        """
        settings = self.config.load_settings()

        # Get options from settings
        options = settings.get(category, [])
        if not options:
            # Use defaults
            if category == "change_type":
                options = VALID_CHANGE_TYPES.copy()
            elif category == "phase":
                options = PROJECT_PHASES.copy()

        # Get last selected
        last_selected = self.config.get_last_selected(setting_key)

        # Reorder to put last selected first
        if last_selected and last_selected in options:
            options = [last_selected] + [o for o in options if o != last_selected]

        # Limit to 9 options + Other
        if len(options) > 9:
            options = options[:9]

        return options

    def _get_infrastructure_options(self, category: str) -> list[str]:
        """Get infrastructure options for a category.

        Args:
            category: Infrastructure category (compute, storage, queue, access)

        Returns:
            List of options
        """
        options = self.config.get_infrastructure_options(category)

        if not options:
            # Use defaults from constants
            from .constants import (
                ACCESS_OPTIONS,
                COMPUTE_OPTIONS,
                QUEUE_OPTIONS,
                STORAGE_OPTIONS,
            )
            defaults = {
                "compute": COMPUTE_OPTIONS,
                "storage": STORAGE_OPTIONS,
                "queue": QUEUE_OPTIONS,
                "access": ACCESS_OPTIONS,
            }
            options = defaults.get(category, ["Don't Care"])

        # Get last selected
        last_selected = self.config.get_last_selected(f"infrastructure.{category}")

        # Reorder to put last selected first
        if last_selected and last_selected in options:
            options = [last_selected] + [o for o in options if o != last_selected]

        # Limit to 9 options
        if len(options) > 9:
            options = options[:9]

        return options

    def _ask_name(self) -> str:
        """Ask for the feature name (Q1).

        Returns:
            Feature name
        """
        default = self._feature_name or ""

        name = questionary.text(
            "Confirm the name of your change:",
            default=default,
            style=WIZARD_STYLE,
        ).ask()

        if not name:
            raise WizardError("name", "Feature name is required")

        self._answers["name"] = name
        return name

    def _ask_source_location(self) -> str:
        """Ask for source code location (Q1.1).

        Returns:
            Source code path
        """
        last_selected = self.config.get_last_selected("project_code_rootpath")
        default = last_selected or "./"

        location = questionary.text(
            "Confirm the location of the source code to modify:",
            default=default,
            style=WIZARD_STYLE,
        ).ask()

        if not location:
            location = "./"

        self._answers["project_root"] = location
        self.config.set_last_selected("project_code_rootpath", location)
        return location

    def _ask_change_type(self) -> str:
        """Ask for change type (Q2).

        Returns:
            Change type
        """
        options = self._get_options("change_type", "change_type")
        options.append("Other")

        change_type = questionary.select(
            "Is this request a...",
            choices=options,
            style=WIZARD_STYLE,
        ).ask()

        if change_type == "Other":
            change_type = questionary.text(
                "Enter the change type:",
                style=WIZARD_STYLE,
            ).ask()
            if change_type:
                # Save to settings for future use
                settings = self.config.load_settings()
                types = settings.get("change_type", [])
                if change_type not in types:
                    types.append(change_type)
                    settings["change_type"] = types
                    self.config.save_settings(settings)

        if not change_type:
            raise WizardError("change_type", "Change type is required")

        self._answers["change_type"] = change_type
        self._is_bugfix = change_type.lower() == "bug-fix"
        self.config.set_last_selected("change_type", change_type)
        return change_type

    def _ask_project_phase(self) -> str:
        """Ask for project phase (Q3).

        Returns:
            Project phase
        """
        options = self._get_options("phase", "phase")
        options.append("Other")

        phase = questionary.select(
            "Project phase is...",
            choices=options,
            style=WIZARD_STYLE,
        ).ask()

        if phase == "Other":
            phase = questionary.text(
                "Enter the project phase:",
                style=WIZARD_STYLE,
            ).ask()
            if phase:
                # Save to settings
                settings = self.config.load_settings()
                phases = settings.get("phase", [])
                if phase not in phases:
                    phases.append(phase)
                    settings["phase"] = phases
                    self.config.save_settings(settings)

        if not phase:
            phase = "MVP"

        self._answers["project_phase"] = phase
        self.config.set_last_selected("phase", phase)
        return phase

    def _ask_priority(self) -> int:
        """Ask for priority (Q4).

        Returns:
            Priority (1-10)
        """
        last_selected = self.config.get_last_selected("priority")
        default = str(last_selected) if last_selected else str(DEFAULT_PRIORITY)

        priority_str = questionary.text(
            f"Between {PRIORITY_MIN} and {PRIORITY_MAX}, what is the priority? "
            f"({PRIORITY_MIN}=lowest, {PRIORITY_MAX}=critical):",
            default=default,
            style=WIZARD_STYLE,
        ).ask()

        try:
            priority = int(priority_str)
            priority = max(PRIORITY_MIN, min(PRIORITY_MAX, priority))
        except (ValueError, TypeError):
            priority = DEFAULT_PRIORITY

        self._answers["priority"] = priority
        self.config.set_last_selected("priority", priority)
        return priority

    def _ask_compute(self) -> str:
        """Ask for compute infrastructure (Q5).

        Returns:
            Compute option
        """
        options = self._get_infrastructure_options("compute")
        options.append("Other")

        compute = questionary.select(
            "Infrastructure: What COMPUTE stack do you want?",
            choices=options,
            style=WIZARD_STYLE,
        ).ask()

        if compute == "Other":
            compute = questionary.text(
                "Enter the compute option:",
                style=WIZARD_STYLE,
            ).ask()
            if compute:
                self._add_infrastructure_option("compute", compute)

        self._answers.setdefault("infrastructure", {})["compute"] = compute
        self.config.set_last_selected("infrastructure.compute", compute)
        return compute or "Don't Care"

    def _ask_storage(self) -> str:
        """Ask for storage infrastructure (Q6).

        Returns:
            Storage option
        """
        options = self._get_infrastructure_options("storage")
        options.append("Other")

        storage = questionary.select(
            "Infrastructure: What STORAGE stack do you want?",
            choices=options,
            style=WIZARD_STYLE,
        ).ask()

        if storage == "Other":
            storage = questionary.text(
                "Enter the storage option:",
                style=WIZARD_STYLE,
            ).ask()
            if storage:
                self._add_infrastructure_option("storage", storage)

        self._answers.setdefault("infrastructure", {})["storage"] = storage
        self.config.set_last_selected("infrastructure.storage", storage)
        return storage or "Don't Care"

    def _ask_queue(self) -> str:
        """Ask for queue infrastructure (Q7).

        Returns:
            Queue option
        """
        options = self._get_infrastructure_options("queue")
        options.append("Other")

        queue = questionary.select(
            "Infrastructure: What QUEUE stack do you want?",
            choices=options,
            style=WIZARD_STYLE,
        ).ask()

        if queue == "Other":
            queue = questionary.text(
                "Enter the queue option:",
                style=WIZARD_STYLE,
            ).ask()
            if queue:
                self._add_infrastructure_option("queue", queue)

        self._answers.setdefault("infrastructure", {})["queue"] = queue
        self.config.set_last_selected("infrastructure.queue", queue)
        return queue or "Don't Care"

    def _ask_access(self) -> str:
        """Ask for access infrastructure (Q8).

        Returns:
            Access option
        """
        options = self._get_infrastructure_options("access")
        options.append("Other")

        access = questionary.select(
            "Infrastructure: What ACCESS path do you want?",
            choices=options,
            style=WIZARD_STYLE,
        ).ask()

        if access == "Other":
            access = questionary.text(
                "Enter the access option:",
                style=WIZARD_STYLE,
            ).ask()
            if access:
                self._add_infrastructure_option("access", access)

        self._answers.setdefault("infrastructure", {})["access"] = access
        self.config.set_last_selected("infrastructure.access", access)
        return access or "Don't Care"

    def _add_infrastructure_option(self, category: str, option: str) -> None:
        """Add a new infrastructure option to settings.

        Args:
            category: Infrastructure category
            option: New option to add
        """
        settings = self.config.load_settings()
        infra = settings.get("infrastructure", {})
        options = infra.get(category, [])
        if option not in options:
            options.append(option)
            infra[category] = options
            settings["infrastructure"] = infra
            self.config.save_settings(settings)

    def _ask_description(self) -> str:
        """Ask for task description (Q9).

        Returns:
            Task description
        """
        print("\nLast Step! Type a few sentences describing this request.")
        print("For example: 'There is a bug in feature X that returns 1 more than expected.'")
        print("\nThis information will be handed off to the Claude Code Planning Agent.\n")

        description = questionary.text(
            "Description:",
            multiline=True,
            style=WIZARD_STYLE,
        ).ask()

        if not description:
            description = "No description provided."

        self._answers["description"] = description
        return description

    def _show_confirmation(self) -> bool:
        """Show confirmation screen and get user approval.

        Returns:
            True if confirmed, False otherwise
        """
        print("\n" + "=" * 60)
        print("Let's verify everything looks right!")
        print("=" * 60)
        print(f"\n- Name:     {self._answers.get('name', 'N/A')}")
        print(f"- Type:     {self._answers.get('change_type', 'N/A')}")
        print(f"- Phase:    {self._answers.get('project_phase', 'N/A')}")
        print(f"- Priority: {self._answers.get('priority', 5)} (out of 10)")
        print(f"- Code Found at: {self._answers.get('project_root', './')}")

        if not self._is_bugfix:
            infra = self._answers.get("infrastructure", {})
            print("- Infrastructure Preferences:")
            print(f"  - Compute: {infra.get('compute', 'N/A')}")
            print(f"  - Storage: {infra.get('storage', 'N/A')}")
            print(f"  - Queue:   {infra.get('queue', 'N/A')}")
            print(f"  - Access:  {infra.get('access', 'N/A')}")

        print("\n- Instructions:")
        desc = self._answers.get("description", "N/A")
        for line in desc.split("\n"):
            print(f"  > {line}")

        print("\n" + "=" * 60)

        return questionary.confirm(
            "Press Enter to Accept, or 'n' to cancel:",
            default=True,
            style=WIZARD_STYLE,
        ).ask()

    def _show_next_steps(self, task_path: str) -> None:
        """Show next steps after task creation.

        Args:
            task_path: Path to the created task file
        """
        print("\n" + "=" * 60)
        print("Congratulations! Task created successfully!")
        print("=" * 60)
        print(f"\nTask file: {task_path}")
        print("\nIf you have a BW loop already running, nothing more to do!")
        print("Simply monitor and wait for the job to be completed.")
        print("\nTo start a new BentWookie loop:")
        print('```bash')
        print('while :; do bw --next_prompt "loop name" | claude ; done')
        print('```')
        print("\nThanks for playing!")

    def _build_body(self) -> str:
        """Build the markdown body for the task.

        Returns:
            Markdown body content
        """
        # Load the template for instructions placeholder
        resources = get_stage_resources("1plan")
        template_instructions = resources.get("instructions", "{instructions}")

        body = f"""# Instructions
{{instructions}}


# Learnings
{{learnings}}


# User Request
{self._answers.get('description', '')}


# Implementation Plan
(To be filled by AI during planning phase)
"""
        return body

    def run(self) -> Task | None:
        """Run the planning wizard.

        Returns:
            Created task dictionary, or None if cancelled
        """
        try:
            print("\n" + "=" * 60)
            print("BentWookie Planning Wizard")
            print("=" * 60 + "\n")

            # Q1: Feature name
            self._ask_name()

            # Q1.1: Source location
            self._ask_source_location()

            # Q2: Change type
            self._ask_change_type()

            # Q3: Project phase
            self._ask_project_phase()

            # Q4: Priority
            self._ask_priority()

            # Q5-Q8: Infrastructure (skip for bug fixes)
            if not self._is_bugfix:
                self._ask_compute()
                self._ask_storage()
                self._ask_queue()
                self._ask_access()
            else:
                self._answers["infrastructure"] = {
                    "compute": None,
                    "storage": None,
                    "queue": None,
                    "access": None,
                }

            # Q9: Description
            self._ask_description()

            # Confirmation
            if not self._show_confirmation():
                print("\nWizard cancelled.")
                return None

            # Create the task
            body = self._build_body()
            task = create_task_file(
                name=self._answers["name"],
                stage="1plan",
                body=body,
                change_type=self._answers.get("change_type", "New Feature"),
                project_phase=self._answers.get("project_phase", "MVP"),
                priority=self._answers.get("priority", 5),
                project_root=self._answers.get("project_root", "./"),
                infrastructure=self._answers.get("infrastructure", {}),
            )

            # Show next steps
            self._show_next_steps(task.get("file_path", ""))

            return task

        except KeyboardInterrupt:
            print("\n\nWizard cancelled by user.")
            return None
        except WizardError as e:
            print(f"\nWizard error: {e}")
            return None


def plan(feature_name: str | None = None) -> Task | None:
    """Run the planning wizard.

    This is the main entry point for creating new task plans.

    Args:
        feature_name: Optional pre-set feature name

    Returns:
        Created task dictionary, or None if cancelled
    """
    wizard = PlanningWizard(feature_name)
    return wizard.run()
