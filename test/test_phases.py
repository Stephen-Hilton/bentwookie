"""Tests for loop/phases module."""

import pytest
from pathlib import Path
import tempfile
import time

from bentwookie.loop import phases
from bentwookie import constants


class TestGetNextPhase:
    """Tests for get_next_phase function."""

    def test_plan_to_dev(self):
        """Test plan -> dev transition."""
        assert phases.get_next_phase("plan") == "dev"

    def test_dev_to_test(self):
        """Test dev -> test transition."""
        assert phases.get_next_phase("dev") == "test"

    def test_test_to_deploy(self):
        """Test test -> deploy transition."""
        assert phases.get_next_phase("test") == "deploy"

    def test_deploy_to_verify(self):
        """Test deploy -> verify transition."""
        assert phases.get_next_phase("deploy") == "verify"

    def test_verify_to_document(self):
        """Test verify -> document transition."""
        assert phases.get_next_phase("verify") == "document"

    def test_document_to_complete(self):
        """Test document -> complete transition."""
        assert phases.get_next_phase("document") == "complete"

    def test_complete_returns_none(self):
        """Test complete has no next phase."""
        assert phases.get_next_phase("complete") is None

    def test_unknown_phase_returns_none(self):
        """Test unknown phase returns None."""
        assert phases.get_next_phase("unknown") is None


class TestGetPhaseTimeout:
    """Tests for get_phase_timeout function."""

    def test_plan_timeout(self):
        """Test plan phase timeout."""
        timeout = phases.get_phase_timeout("plan")
        assert timeout > 0

    def test_dev_timeout(self):
        """Test dev phase timeout."""
        timeout = phases.get_phase_timeout("dev")
        assert timeout > 0

    def test_test_timeout(self):
        """Test test phase timeout."""
        timeout = phases.get_phase_timeout("test")
        assert timeout > 0

    def test_unknown_phase_default_timeout(self):
        """Test unknown phase gets default timeout."""
        timeout = phases.get_phase_timeout("unknown")
        assert timeout > 0


class TestGetPhaseTools:
    """Tests for get_phase_tools function."""

    def test_plan_tools(self):
        """Test plan phase tools."""
        tools = phases.get_phase_tools("plan")
        assert isinstance(tools, list)
        # Plan phase should have read tools but not edit
        assert "Read" in tools or len(tools) > 0

    def test_dev_tools(self):
        """Test dev phase tools."""
        tools = phases.get_phase_tools("dev")
        assert isinstance(tools, list)
        # Dev phase should have edit/write tools

    def test_unknown_phase_default_tools(self):
        """Test unknown phase gets default tools."""
        tools = phases.get_phase_tools("unknown")
        assert isinstance(tools, list)


class TestSaveToDocs:
    """Tests for save_to_docs function."""

    @pytest.fixture
    def temp_docs_dir(self, monkeypatch):
        """Create a temporary docs directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_path = Path(tmpdir) / "docs"
            monkeypatch.setattr(constants, "DEFAULT_DOCS_PATH", str(docs_path))
            yield docs_path

    def test_save_to_docs_creates_file(self, temp_docs_dir):
        """Test save_to_docs creates a markdown file."""
        request = {
            "reqid": 1,
            "reqname": "Test Request",
            "reqphase": "plan",
            "prjname": "TestProject",
        }

        filepath = phases.save_to_docs(request, "Test content")

        assert Path(filepath).exists()
        assert filepath.endswith(".md")

    def test_save_to_docs_content(self, temp_docs_dir):
        """Test save_to_docs writes correct content."""
        request = {
            "reqid": 42,
            "reqname": "My Request",
            "reqphase": "dev",
            "prjname": "MyProject",
        }

        filepath = phases.save_to_docs(request, "Main content here")
        content = Path(filepath).read_text()

        assert "My Request" in content
        assert "dev" in content.lower()
        assert "MyProject" in content
        assert "Main content here" in content

    def test_save_to_docs_creates_directory(self, temp_docs_dir):
        """Test save_to_docs creates docs directory if it doesn't exist."""
        request = {
            "reqid": 1,
            "reqname": "Test",
            "reqphase": "plan",
        }

        filepath = phases.save_to_docs(request, "Content")

        assert temp_docs_dir.exists()
        assert Path(filepath).exists()

    def test_save_to_docs_filename_format(self, temp_docs_dir):
        """Test save_to_docs uses correct filename format."""
        request = {
            "reqid": 5,
            "reqname": "Test",
            "reqphase": "test",
        }

        filepath = phases.save_to_docs(request, "Content")
        filename = Path(filepath).name

        # Filename should contain reqid and phase
        assert "5_" in filename
        assert "test_" in filename


class TestCleanupOldDocs:
    """Tests for cleanup_old_docs function."""

    @pytest.fixture
    def temp_docs_with_files(self, monkeypatch):
        """Create a temporary docs directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_path = Path(tmpdir) / "docs"
            docs_path.mkdir()
            monkeypatch.setattr(constants, "DEFAULT_DOCS_PATH", str(docs_path))

            # Create some test files
            old_file = docs_path / "old_doc.md"
            old_file.write_text("Old content")

            new_file = docs_path / "new_doc.md"
            new_file.write_text("New content")

            # Make old_file appear old (modify timestamp)
            old_time = time.time() - (60 * 24 * 60 * 60)  # 60 days ago
            import os
            os.utime(old_file, (old_time, old_time))

            yield docs_path, old_file, new_file

    def test_cleanup_deletes_old_files(self, temp_docs_with_files, monkeypatch):
        """Test cleanup_old_docs deletes files older than retention period."""
        docs_path, old_file, new_file = temp_docs_with_files

        # Mock settings to return 30 days retention
        from bentwookie import settings
        monkeypatch.setattr(settings, "get_doc_retention_days", lambda: 30)

        deleted = phases.cleanup_old_docs()

        assert deleted == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_cleanup_respects_retention_days(self, temp_docs_with_files, monkeypatch):
        """Test cleanup respects the retention days setting."""
        docs_path, old_file, new_file = temp_docs_with_files

        # Set retention to 90 days (old_file is 60 days old)
        from bentwookie import settings
        monkeypatch.setattr(settings, "get_doc_retention_days", lambda: 90)

        deleted = phases.cleanup_old_docs()

        assert deleted == 0
        assert old_file.exists()

    def test_cleanup_disabled_when_zero(self, temp_docs_with_files, monkeypatch):
        """Test cleanup is disabled when retention is 0."""
        docs_path, old_file, new_file = temp_docs_with_files

        from bentwookie import settings
        monkeypatch.setattr(settings, "get_doc_retention_days", lambda: 0)

        deleted = phases.cleanup_old_docs()

        assert deleted == 0
        assert old_file.exists()

    def test_cleanup_with_explicit_retention(self, temp_docs_with_files, monkeypatch):
        """Test cleanup with explicitly passed retention days."""
        docs_path, old_file, new_file = temp_docs_with_files

        deleted = phases.cleanup_old_docs(retention_days=30)

        assert deleted == 1
        assert not old_file.exists()

    def test_cleanup_nonexistent_directory(self, monkeypatch):
        """Test cleanup handles nonexistent docs directory."""
        monkeypatch.setattr(constants, "DEFAULT_DOCS_PATH", "/nonexistent/path")

        deleted = phases.cleanup_old_docs(retention_days=30)
        assert deleted == 0

    def test_cleanup_only_deletes_md_files(self, monkeypatch):
        """Test cleanup only deletes .md files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_path = Path(tmpdir) / "docs"
            docs_path.mkdir()
            monkeypatch.setattr(constants, "DEFAULT_DOCS_PATH", str(docs_path))

            # Create old .md and .txt files
            md_file = docs_path / "old.md"
            md_file.write_text("md content")

            txt_file = docs_path / "old.txt"
            txt_file.write_text("txt content")

            # Make both old
            old_time = time.time() - (60 * 24 * 60 * 60)
            import os
            os.utime(md_file, (old_time, old_time))
            os.utime(txt_file, (old_time, old_time))

            deleted = phases.cleanup_old_docs(retention_days=30)

            assert deleted == 1
            assert not md_file.exists()
            assert txt_file.exists()  # .txt files not deleted


class TestGetSystemPrompt:
    """Tests for get_system_prompt function."""

    def test_get_system_prompt_returns_string(self):
        """Test get_system_prompt returns a non-empty string."""
        request = {
            "reqid": 1,
            "reqname": "Test",
            "reqphase": "plan",
            "prjname": "Project",
        }
        prompt = phases.get_system_prompt(request)
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestGetPhasePrompt:
    """Tests for get_phase_prompt function."""

    @pytest.fixture
    def temp_db_phases(self, monkeypatch):
        """Create a temporary database for phase tests."""
        from bentwookie.db import connection, queries
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        connection.set_db_path(db_path)
        connection.init_db()

        # Create a project and request
        prjid = queries.create_project("Test Project", prjversion="poc", prjcodedir="/code")
        reqid = queries.create_request(prjid, "Test Request", "Do something", reqphase="plan")

        yield {"prjid": prjid, "reqid": reqid, "db_path": db_path}

        if db_path.exists():
            db_path.unlink()

    def test_get_phase_prompt_plan(self, temp_db_phases):
        """Test getting plan phase prompt."""
        from bentwookie.db import queries

        # Use the actual request from the database
        request = queries.get_request(temp_db_phases["reqid"])

        prompt = phases.get_phase_prompt(request)

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_phase_prompt_dev(self, temp_db_phases):
        """Test getting dev phase prompt."""
        from bentwookie.db import queries

        # Update request to dev phase
        queries.update_request_phase(temp_db_phases["reqid"], "dev")
        request = queries.get_request(temp_db_phases["reqid"])

        prompt = phases.get_phase_prompt(request)

        assert isinstance(prompt, str)

    def test_get_phase_prompt_test(self, temp_db_phases):
        """Test getting test phase prompt."""
        from bentwookie.db import queries

        # Update request to test phase
        queries.update_request_phase(temp_db_phases["reqid"], "test")
        request = queries.get_request(temp_db_phases["reqid"])

        prompt = phases.get_phase_prompt(request)

        assert isinstance(prompt, str)
