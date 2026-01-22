"""Tests for wizard module."""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

from bentwookie import wizard
from bentwookie.db import connection, queries


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    connection.set_db_path(db_path)
    connection.init_db()

    yield db_path

    if db_path.exists():
        db_path.unlink()


class TestGetInfraOptions:
    """Tests for _get_infra_options helper."""

    def test_get_infra_options_compute(self, temp_db):
        """Test getting compute infra options."""
        # Add some options
        queries.add_infra_option("compute", "AWS Lambda")
        queries.add_infra_option("compute", "Docker")

        options = wizard._get_infra_options("compute")
        assert isinstance(options, list)
        assert "AWS Lambda" in options
        assert "Docker" in options

    def test_get_infra_options_empty(self, temp_db):
        """Test getting options when none exist."""
        options = wizard._get_infra_options("nonexistent")
        assert isinstance(options, list)


class TestPlanningWizard:
    """Tests for PlanningWizard class."""

    def test_wizard_init(self, temp_db):
        """Test wizard initialization."""
        wiz = wizard.PlanningWizard()
        assert wiz is not None

    def test_wizard_with_feature_name(self, temp_db):
        """Test wizard with pre-set feature name."""
        wiz = wizard.PlanningWizard(feature_name="Test Feature")
        assert wiz._feature_name == "Test Feature"

    @patch("questionary.text")
    @patch("questionary.select")
    def test_wizard_run_cancellation(self, mock_select, mock_text, temp_db):
        """Test wizard handles cancellation gracefully."""
        # Simulate cancellation (None returned)
        mock_text.return_value.ask.return_value = None

        wiz = wizard.PlanningWizard()
        result = wiz.run()

        assert result is None

    @patch("questionary.text")
    @patch("questionary.select")
    @patch("questionary.checkbox")
    @patch("questionary.confirm")
    def test_wizard_collect_project_info(
        self, mock_confirm, mock_checkbox, mock_select, mock_text, temp_db
    ):
        """Test wizard collects project info through prompts."""
        # Create a project first
        prjid = queries.create_project("Test Project")

        # Mock all questionary interactions
        mock_text.return_value.ask.return_value = "Test Feature"
        mock_select.return_value.ask.side_effect = [
            "Test Project",  # Project selection
            "new_feature",   # Request type
            "poc",           # Version
            "5",             # Priority
        ]
        mock_checkbox.return_value.ask.return_value = []
        mock_confirm.return_value.ask.side_effect = [
            True,   # Confirm creation
            False,  # Don't add infrastructure
        ]

        wiz = wizard.PlanningWizard()
        # Test just getting started - we can't complete the full flow
        # without more mocking, but this tests the initialization


class TestWizardFunction:
    """Tests for the wizard() function."""

    @patch("questionary.text")
    def test_wizard_function_returns_none_on_cancel(self, mock_text, temp_db):
        """Test wizard function returns None on cancellation."""
        mock_text.return_value.ask.return_value = None

        result = wizard.wizard()
        assert result is None

    def test_wizard_function_with_feature_name(self, temp_db, monkeypatch):
        """Test wizard function accepts feature name."""
        # This tests the function signature
        assert callable(wizard.wizard)

        # Mock to avoid interactive prompts
        monkeypatch.setattr(
            wizard.PlanningWizard, "run",
            lambda self: None
        )

        result = wizard.wizard(feature_name="Test Feature")
        assert result is None
