"""Planning wizard for creating new BentWookie requests (v2 - SQLite)."""

from typing import Any

import questionary
from questionary import Style

from .constants import (
    ACCESS_OPTIONS,
    COMPUTE_OPTIONS,
    DEFAULT_PRIORITY,
    PRIORITY_MAX,
    PRIORITY_MIN,
    QUEUE_OPTIONS,
    STORAGE_OPTIONS,
    VALID_INFRA_TYPES,
    VALID_PROJECT_PHASES,
    VALID_PROVIDERS,
    VALID_REQUEST_TYPES,
    VALID_VERSIONS,
)
from .db import (
    add_infrastructure,
    add_request_infrastructure,
    create_project,
    create_request,
    get_infra_options_by_type,
    get_project,
    get_project_by_name,
    get_project_infrastructure,
    init_db,
    list_projects,
)


def _get_infra_options(opttype: str) -> list[str]:
    """Get infrastructure options for a type, with fallback to constants.

    Args:
        opttype: Option type (compute, storage, queue, access).

    Returns:
        List of option names.
    """
    # Try to get from database first
    options = get_infra_options_by_type(opttype)
    if options:
        return options

    # Fall back to hardcoded constants
    fallbacks = {
        "compute": COMPUTE_OPTIONS,
        "storage": STORAGE_OPTIONS,
        "queue": QUEUE_OPTIONS,
        "access": ACCESS_OPTIONS,
    }
    return fallbacks.get(opttype, ["Local"])

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
    """Interactive wizard for creating new requests (v2 - SQLite).

    Guides users through a series of questions to create a properly
    structured request in the database.
    """

    def __init__(self, feature_name: str | None = None):
        """Initialize the wizard.

        Args:
            feature_name: Optional pre-set feature name
        """
        # Ensure database is initialized
        init_db()

        self._feature_name = feature_name
        self._answers: dict[str, Any] = {}
        self._is_bugfix = False
        self._project: dict | None = None

    def _ask_project(self) -> dict:
        """Ask to select or create a project.

        Returns:
            Project dict
        """
        projects = list_projects()

        if projects:
            choices = [
                {"name": f"{p['prjname']} ({p['prjversion']})", "value": p["prjid"]}
                for p in projects
            ]
            # Use a special marker value instead of None to avoid confusion
            choices.append({"name": "[Create new project]", "value": "__NEW__"})

            project_id = questionary.select(
                "Select a project:",
                choices=choices,
                style=WIZARD_STYLE,
            ).ask()

            if project_id == "__NEW__":
                # User selected "[Create new project]"
                return self._create_project()
            elif project_id is not None:
                self._project = get_project(project_id)
                return self._project  # type: ignore
            else:
                # User cancelled (Ctrl+C or Escape)
                raise ValueError("Project selection cancelled")
        else:
            print("\nNo projects found. Let's create one.")
            return self._create_project()

    def _create_project(self) -> dict:
        """Create a new project interactively.

        Returns:
            Created project dict
        """
        name = questionary.text(
            "Project name:",
            style=WIZARD_STYLE,
        ).ask()

        if not name:
            raise ValueError("Project name is required")

        version = questionary.select(
            "Project version:",
            choices=VALID_VERSIONS,
            style=WIZARD_STYLE,
        ).ask()

        phase = questionary.select(
            "Project phase:",
            choices=VALID_PROJECT_PHASES,
            style=WIZARD_STYLE,
        ).ask()

        desc = questionary.text(
            "Project description (optional):",
            style=WIZARD_STYLE,
        ).ask()

        codedir = questionary.text(
            "Code directory (optional, press Enter to skip):",
            default="",
            style=WIZARD_STYLE,
        ).ask()

        prjid = create_project(
            prjname=name,
            prjversion=version or "poc",
            prjphase=phase or "dev",
            prjdesc=desc or None,
            prjcodedir=codedir or None,
        )

        self._project = get_project(prjid)
        print(f"\nProject '{name}' created (ID: {prjid})")

        return self._project  # type: ignore

    def _ask_name(self) -> str:
        """Ask for the request name.

        Returns:
            Request name
        """
        default = self._feature_name or ""

        name = questionary.text(
            "Request name:",
            default=default,
            style=WIZARD_STYLE,
        ).ask()

        if not name:
            raise ValueError("Request name is required")

        self._answers["name"] = name
        return name

    def _ask_change_type(self) -> str:
        """Ask for change type.

        Returns:
            Change type
        """
        type_choices = [
            {"name": "New Feature", "value": "new_feature"},
            {"name": "Bug Fix", "value": "bug_fix"},
            {"name": "Enhancement", "value": "enhancement"},
        ]

        change_type = questionary.select(
            "What type of change is this?",
            choices=type_choices,
            style=WIZARD_STYLE,
        ).ask()

        if not change_type:
            change_type = "new_feature"

        self._answers["change_type"] = change_type
        self._is_bugfix = change_type == "bug_fix"
        return change_type

    def _ask_priority(self) -> int:
        """Ask for priority.

        Returns:
            Priority (1-10)
        """
        priority_str = questionary.text(
            f"Priority ({PRIORITY_MIN}-{PRIORITY_MAX}, {PRIORITY_MIN}=lowest, {PRIORITY_MAX}=critical):",
            default=str(DEFAULT_PRIORITY),
            style=WIZARD_STYLE,
        ).ask()

        try:
            priority = int(priority_str)
            priority = max(PRIORITY_MIN, min(PRIORITY_MAX, priority))
        except (ValueError, TypeError):
            priority = DEFAULT_PRIORITY

        self._answers["priority"] = priority
        return priority

    def _ask_codedir(self) -> str | None:
        """Ask for code directory (request-level override).

        Returns:
            Code directory path or None
        """
        # Show project's codedir as context
        project_codedir = self._project.get("prjcodedir") if self._project else None
        if project_codedir:
            print(f"\n(Project default code dir: {project_codedir})")

        codedir = questionary.text(
            "Code directory override (optional, Enter to use project default):",
            default="",
            style=WIZARD_STYLE,
        ).ask()

        self._answers["codedir"] = codedir or None
        return codedir or None

    def _ask_infrastructure(self, category: str, options: list[str], prompt: str) -> dict | None:
        """Ask for infrastructure preference.

        Args:
            category: Infrastructure category (compute, storage, queue, access)
            options: List of options to choose from
            prompt: Question prompt

        Returns:
            Infrastructure dict or None if skipped
        """
        choices = options + ["Don't Care", "Other"]

        choice = questionary.select(
            prompt,
            choices=choices,
            style=WIZARD_STYLE,
        ).ask()

        if choice == "Don't Care" or not choice:
            return None

        if choice == "Other":
            choice = questionary.text(
                f"Enter {category} option:",
                style=WIZARD_STYLE,
            ).ask()
            if not choice:
                return None

        # Determine provider from choice
        provider = "local"
        if "AWS" in choice or "aws" in choice.lower():
            provider = "aws"
        elif "GCP" in choice or "gcp" in choice.lower() or "Google" in choice:
            provider = "gcp"
        elif "Azure" in choice or "azure" in choice.lower():
            provider = "azure"
        elif "Container" in choice or "Docker" in choice or "container" in choice.lower():
            provider = "container"

        return {
            "inftype": category,
            "infprovider": provider,
            "infval": choice,
            "infnote": None,
        }

    def _ask_all_infrastructure(self) -> list[dict]:
        """Ask for all infrastructure preferences.

        Returns:
            List of infrastructure dicts
        """
        print("\n--- Infrastructure Preferences ---")
        print("(Skip infrastructure questions for bug fixes)")

        infrastructure = []

        compute = self._ask_infrastructure(
            "compute",
            _get_infra_options("compute"),
            "What COMPUTE stack do you want?",
        )
        if compute:
            infrastructure.append(compute)

        storage = self._ask_infrastructure(
            "storage",
            _get_infra_options("storage"),
            "What STORAGE stack do you want?",
        )
        if storage:
            infrastructure.append(storage)

        queue = self._ask_infrastructure(
            "queue",
            _get_infra_options("queue"),
            "What QUEUE stack do you want?",
        )
        if queue:
            infrastructure.append(queue)

        access = self._ask_infrastructure(
            "access",
            _get_infra_options("access"),
            "What ACCESS path do you want?",
        )
        if access:
            infrastructure.append(access)

        self._answers["infrastructure"] = infrastructure
        return infrastructure

    def _ask_description(self) -> str:
        """Ask for request description/prompt.

        Returns:
            Description text
        """
        print("\n--- Request Description ---")
        print("Describe what you want done. Be specific about the changes needed.")
        print("This will be used as the prompt for the AI to work on.\n")

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
        print(f"\n- Project:    {self._project['prjname']}")
        print(f"- Request:    {self._answers.get('name', 'N/A')}")
        print(f"- Type:       {self._answers.get('change_type', 'N/A')}")
        print(f"- Priority:   {self._answers.get('priority', 5)} (out of 10)")

        codedir = self._answers.get("codedir")
        if codedir:
            print(f"- Code Dir:   {codedir}")
        elif self._project.get("prjcodedir"):
            print(f"- Code Dir:   {self._project['prjcodedir']} (from project)")

        infrastructure = self._answers.get("infrastructure", [])
        if infrastructure:
            print("- Infrastructure:")
            for inf in infrastructure:
                print(f"    - {inf['inftype']}: {inf['infval']} ({inf['infprovider']})")

        print("\n- Description:")
        desc = self._answers.get("description", "N/A")
        for line in desc.split("\n")[:5]:  # Show first 5 lines
            print(f"    {line[:60]}...")

        print("\n" + "=" * 60)

        return questionary.confirm(
            "Create this request?",
            default=True,
            style=WIZARD_STYLE,
        ).ask()

    def _create_request(self) -> int:
        """Create the request in the database.

        Returns:
            New request ID
        """
        reqid = create_request(
            prjid=self._project["prjid"],
            reqname=self._answers["name"],
            reqprompt=self._answers["description"],
            reqtype=self._answers.get("change_type", "new_feature"),
            reqpriority=self._answers.get("priority", DEFAULT_PRIORITY),
            reqcodedir=self._answers.get("codedir"),
        )

        # Add request-level infrastructure overrides
        for inf in self._answers.get("infrastructure", []):
            add_request_infrastructure(
                reqid=reqid,
                inftype=inf["inftype"],
                infprovider=inf["infprovider"],
                infval=inf["infval"],
                infnote=inf.get("infnote"),
            )

        return reqid

    def _show_next_steps(self, reqid: int) -> None:
        """Show next steps after request creation.

        Args:
            reqid: Created request ID
        """
        print("\n" + "=" * 60)
        print("Request created successfully!")
        print("=" * 60)
        print(f"\nRequest ID: {reqid}")
        print(f"Project:    {self._project['prjname']}")
        print(f"Name:       {self._answers['name']}")
        print("\nIf you have a BW loop already running, it will pick up this request!")
        print("\nTo start the daemon:")
        print("  bw loop start")
        print("\nTo check status:")
        print("  bw loop status")
        print("  bw request show", reqid)
        print("\nTo view in web UI:")
        print("  bw web")
        print("\nThanks for using BentWookie!")

    def run(self) -> int | None:
        """Run the planning wizard.

        Returns:
            Created request ID, or None if cancelled
        """
        try:
            print("\n" + "=" * 60)
            print("BentWookie Planning Wizard (v0.2.0)")
            print("=" * 60 + "\n")

            # Step 1: Select or create project
            self._ask_project()

            # Step 2: Request name
            self._ask_name()

            # Step 3: Change type
            self._ask_change_type()

            # Step 4: Priority
            self._ask_priority()

            # Step 5: Code directory override
            self._ask_codedir()

            # Step 6: Infrastructure (skip for bug fixes)
            if not self._is_bugfix:
                self._ask_all_infrastructure()

            # Step 7: Description
            self._ask_description()

            # Confirmation
            if not self._show_confirmation():
                print("\nWizard cancelled.")
                return None

            # Create the request
            reqid = self._create_request()

            # Show next steps
            self._show_next_steps(reqid)

            return reqid

        except KeyboardInterrupt:
            print("\n\nWizard cancelled by user.")
            return None
        except ValueError as e:
            print(f"\nWizard error: {e}")
            return None


def wizard(feature_name: str | None = None) -> int | None:
    """Run the planning wizard.

    This is the main entry point for creating new requests.

    Args:
        feature_name: Optional pre-set feature name

    Returns:
        Created request ID, or None if cancelled
    """
    w = PlanningWizard(feature_name)
    return w.run()


# Alias for backwards compatibility
plan = wizard
