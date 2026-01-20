"""Tests for core task management functions."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from bentwookie.config import init_config, reset_config
from bentwookie.constants import (
    STATUS_IN_PROGRESS,
    STATUS_NOT_STARTED,
    STATUS_PLANNING,
    STATUS_READY,
)
from bentwookie.core import (
    Task,
    create_task_file,
    get_all_tasks,
    get_next_stage,
    get_task,
    move_stage,
    save_task,
    task_ready,
    update_status,
    validate_tasks,
)
from bentwookie.exceptions import TaskNotFoundError, TaskParseError


@pytest.fixture
def temp_tasks_dir():
    """Create a temporary tasks directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_path = Path(tmpdir) / "tasks"
        tasks_path.mkdir()

        # Create stage directories
        for stage in ["1plan", "2dev", "3test", "4deploy", "5validate", "9done"]:
            (tasks_path / stage).mkdir()
            resources = tasks_path / stage / ".resources"
            resources.mkdir()

        # Create global directory
        global_dir = tasks_path / "global"
        global_dir.mkdir()

        # Initialize config with temp directory
        reset_config()
        init_config(tasks_path=tasks_path, test_mode=True)

        yield tasks_path

        reset_config()


@pytest.fixture
def sample_task_file(temp_tasks_dir):
    """Create a sample task file."""
    task_content = """--- frontmatter structured data:
name: Test Feature
status: Not Started
change_type: New Feature
project_phase: MVP
priority: 5
stage: 1plan
last_updated: None

file_paths:
- project_root: ./
- tasks: {tasks_path}
- task: None

infrastructure:
- compute: AWS Lambda
- storage: AWS DynamoDB
- queue: None
- access: None

errors: []
---

# Instructions
Test instructions here.

# User Request
This is a test request.
""".format(tasks_path=temp_tasks_dir)

    task_file = temp_tasks_dir / "1plan" / "test-feature.md"
    task_file.write_text(task_content)

    return task_file


class TestGetTask:
    """Tests for get_task function."""

    def test_get_task_success(self, sample_task_file):
        """Test successful task parsing."""
        task = get_task(sample_task_file)

        assert task["name"] == "Test Feature"
        assert task["status"] == "Not Started"
        assert task["change_type"] == "New Feature"
        assert task["project_phase"] == "MVP"
        assert task["priority"] == 5
        assert task["stage"] == "1plan"
        assert "body" in task
        assert "Test instructions here." in task["body"]

    def test_get_task_not_found(self, temp_tasks_dir):
        """Test error when task file doesn't exist."""
        with pytest.raises(TaskNotFoundError):
            get_task(temp_tasks_dir / "nonexistent.md")

    def test_get_task_invalid_yaml(self, temp_tasks_dir):
        """Test error with invalid YAML frontmatter."""
        bad_file = temp_tasks_dir / "1plan" / "bad.md"
        bad_file.write_text("--- invalid yaml\n: bad: format:\n---\ncontent")

        with pytest.raises(TaskParseError):
            get_task(bad_file)


class TestSaveTask:
    """Tests for save_task function."""

    def test_save_task_success(self, sample_task_file):
        """Test successful task saving."""
        task = get_task(sample_task_file)
        task["status"] = "Ready"
        task["priority"] = 8

        saved_path = save_task(task)

        # Re-read and verify
        reloaded = get_task(saved_path)
        assert reloaded["status"] == "Ready"
        assert reloaded["priority"] == 8

    def test_save_task_creates_backup(self, sample_task_file):
        """Test that backup file is created."""
        task = get_task(sample_task_file)
        task["status"] = "Ready"

        save_task(task, create_backup=True)

        backup_path = sample_task_file.with_suffix(".md.bkup")
        assert backup_path.exists()


class TestTaskReady:
    """Tests for task_ready function."""

    def test_ready_status(self, sample_task_file):
        """Test that Ready status is ready."""
        task = get_task(sample_task_file)
        task["status"] = STATUS_READY

        assert task_ready(task) is True

    def test_not_started_status(self, sample_task_file):
        """Test that Not Started status is ready."""
        task = get_task(sample_task_file)
        task["status"] = STATUS_NOT_STARTED

        assert task_ready(task) is True

    def test_in_progress_not_timed_out(self, sample_task_file):
        """Test that recent In Progress is not ready."""
        task = get_task(sample_task_file)
        task["status"] = STATUS_IN_PROGRESS
        task["last_updated"] = datetime.now().isoformat()

        assert task_ready(task) is False

    def test_in_progress_timed_out(self, sample_task_file):
        """Test that old In Progress is ready (timed out)."""
        task = get_task(sample_task_file)
        task["status"] = STATUS_IN_PROGRESS
        old_time = datetime.now() - timedelta(hours=25)
        task["last_updated"] = old_time.isoformat()

        assert task_ready(task) is True

    def test_planning_not_timed_out(self, sample_task_file):
        """Test that recent Planning is not ready."""
        task = get_task(sample_task_file)
        task["status"] = STATUS_PLANNING
        task["last_updated"] = datetime.now().isoformat()

        assert task_ready(task) is False

    def test_planning_timed_out(self, sample_task_file):
        """Test that old Planning is ready (timed out)."""
        task = get_task(sample_task_file)
        task["status"] = STATUS_PLANNING
        old_time = datetime.now() - timedelta(hours=5)
        task["last_updated"] = old_time.isoformat()

        assert task_ready(task) is True


class TestValidateTasks:
    """Tests for validate_tasks function."""

    def test_filters_non_ready_tasks(self, temp_tasks_dir):
        """Test that non-ready tasks are filtered out."""
        # Create ready task
        ready_task = create_task_file(
            name="Ready Task",
            stage="1plan",
            body="Test",
            status=STATUS_READY,
        )

        # Create in-progress task (not timed out)
        in_progress_task = create_task_file(
            name="In Progress Task",
            stage="1plan",
            body="Test",
            status=STATUS_IN_PROGRESS,
        )
        # Update with recent timestamp
        task = get_task(in_progress_task["file_path"])
        task["last_updated"] = datetime.now().isoformat()
        save_task(task)

        all_tasks = get_all_tasks()
        ready_tasks = validate_tasks(all_tasks)

        assert len(ready_tasks) == 1
        assert ready_tasks[0]["name"] == "Ready Task"

    def test_sorts_by_stage_then_priority(self, temp_tasks_dir):
        """Test that tasks are sorted correctly."""
        # Create tasks in different stages with different priorities
        create_task_file(
            name="Low Priority Plan",
            stage="1plan",
            body="Test",
            priority=2,
            status=STATUS_READY,
        )
        create_task_file(
            name="High Priority Plan",
            stage="1plan",
            body="Test",
            priority=8,
            status=STATUS_READY,
        )
        create_task_file(
            name="Dev Task",
            stage="2dev",
            body="Test",
            priority=5,
            status=STATUS_READY,
        )

        all_tasks = get_all_tasks()
        sorted_tasks = validate_tasks(all_tasks)

        # 2dev should come first (higher stage number)
        assert sorted_tasks[0]["name"] == "Dev Task"
        # Then high priority 1plan
        assert sorted_tasks[1]["name"] == "High Priority Plan"
        # Then low priority 1plan
        assert sorted_tasks[2]["name"] == "Low Priority Plan"


class TestGetNextStage:
    """Tests for get_next_stage function."""

    def test_plan_to_dev(self, sample_task_file):
        """Test 1plan -> 2dev."""
        task = get_task(sample_task_file)
        task["stage"] = "1plan"

        assert get_next_stage(task) == "2dev"

    def test_dev_to_test(self, sample_task_file):
        """Test 2dev -> 3test."""
        task = get_task(sample_task_file)
        task["stage"] = "2dev"

        assert get_next_stage(task) == "3test"

    def test_done_returns_none(self, sample_task_file):
        """Test 9done returns None."""
        task = get_task(sample_task_file)
        task["stage"] = "9done"

        assert get_next_stage(task) is None


class TestMoveStage:
    """Tests for move_stage function."""

    def test_move_stage_in_test_mode(self, sample_task_file):
        """Test that test mode only updates stage, doesn't move file."""
        task = get_task(sample_task_file)
        original_path = task["file_path"]

        task = move_stage(task, "2dev")

        # File should still be in original location (test mode)
        assert Path(original_path).exists()
        assert task["stage"] == "2dev"


class TestUpdateStatus:
    """Tests for update_status function."""

    def test_update_status_success(self, sample_task_file):
        """Test successful status update."""
        task = get_task(sample_task_file)

        task = update_status(task, STATUS_READY)

        reloaded = get_task(sample_task_file)
        assert reloaded["status"] == STATUS_READY


class TestCreateTaskFile:
    """Tests for create_task_file function."""

    def test_create_task_file(self, temp_tasks_dir):
        """Test creating a new task file."""
        task = create_task_file(
            name="New Feature",
            stage="1plan",
            body="# Test\nThis is a test.",
            priority=7,
            change_type="Bug-Fix",
        )

        assert task["name"] == "New Feature"
        assert task["priority"] == 7
        assert task["change_type"] == "Bug-Fix"
        assert Path(task["file_path"]).exists()

    def test_create_task_generates_safe_filename(self, temp_tasks_dir):
        """Test that filename is generated safely."""
        task = create_task_file(
            name="My Feature with Spaces & Symbols!",
            stage="1plan",
            body="Test",
        )

        file_path = Path(task["file_path"])
        assert " " not in file_path.name
        assert "&" not in file_path.name
        assert "!" not in file_path.name
