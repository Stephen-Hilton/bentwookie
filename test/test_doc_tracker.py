"""Tests for loop/doc_tracker module."""

import pytest
from pathlib import Path
import tempfile

from bentwookie.loop.doc_tracker import DocTracker
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


@pytest.fixture
def test_request(temp_db):
    """Create a test project and request."""
    prjid = queries.create_project("Test Project", prjcodedir="/tmp/test")
    reqid = queries.create_request(
        prjid, "Test Request", "Do something",
        reqphase="plan", reqstatus="tbd"
    )
    return {"prjid": prjid, "reqid": reqid}


class TestDocTrackerPattern:
    """Tests for DOC_PATTERN regex."""

    def test_pattern_exists(self):
        """Test DOC_PATTERN is defined."""
        assert hasattr(DocTracker, "DOC_PATTERN")
        assert isinstance(DocTracker.DOC_PATTERN, str)

    def test_pattern_matches_basic_format(self):
        """Test pattern matches basic document format."""
        import re
        pattern = re.compile(DocTracker.DOC_PATTERN)
        text = "[DOC:PLAN.md] path: /path/to/PLAN.md"
        match = pattern.search(text)
        assert match is not None
        assert match.group(1) == "PLAN.md"
        assert match.group(2) == "/path/to/PLAN.md"


class TestParseResponse:
    """Tests for parse_response method."""

    def test_parse_empty_response(self):
        """Test parsing empty response returns empty list."""
        tracker = DocTracker()
        result = tracker.parse_response("")
        assert result == []

    def test_parse_none_response(self):
        """Test parsing None response returns empty list."""
        tracker = DocTracker()
        result = tracker.parse_response(None)
        assert result == []

    def test_parse_response_no_docs(self):
        """Test parsing response with no documents."""
        tracker = DocTracker()
        response = "This is a response with no document markers."
        result = tracker.parse_response(response)
        assert result == []

    def test_parse_single_document(self):
        """Test parsing response with single document."""
        tracker = DocTracker()
        response = "[DOC:PLAN.md] path: /path/to/project/PLAN.md"
        result = tracker.parse_response(response)
        
        assert len(result) == 1
        assert result[0]["name"] == "PLAN.md"
        assert result[0]["path"] == "/path/to/project/PLAN.md"

    def test_parse_multiple_documents(self):
        """Test parsing response with multiple documents."""
        tracker = DocTracker()
        response = """
        Here is the output:
        [DOC:PLAN.md] path: /path/to/project/PLAN.md
        Some text in between
        [DOC:custom_output.md] path: /path/to/project/custom_output.md
        More text
        [DOC:test_results.txt] path: /path/to/project/test_results.txt
        """
        result = tracker.parse_response(response)
        
        assert len(result) == 3
        assert result[0]["name"] == "PLAN.md"
        assert result[0]["path"] == "/path/to/project/PLAN.md"
        assert result[1]["name"] == "custom_output.md"
        assert result[1]["path"] == "/path/to/project/custom_output.md"
        assert result[2]["name"] == "test_results.txt"
        assert result[2]["path"] == "/path/to/project/test_results.txt"

    def test_parse_document_with_spaces_in_path(self):
        """Test parsing document with spaces in path."""
        tracker = DocTracker()
        response = "[DOC:report.md] path: /path/to/my project/report.md"
        result = tracker.parse_response(response)
        
        assert len(result) == 1
        assert result[0]["name"] == "report.md"
        assert result[0]["path"] == "/path/to/my project/report.md"

    def test_parse_document_with_special_chars_in_name(self):
        """Test parsing document with special characters in name."""
        tracker = DocTracker()
        response = "[DOC:IP_Output_v2.0.md] path: /path/to/IP_Output_v2.0.md"
        result = tracker.parse_response(response)
        
        assert len(result) == 1
        assert result[0]["name"] == "IP_Output_v2.0.md"
        assert result[0]["path"] == "/path/to/IP_Output_v2.0.md"

    def test_parse_strips_whitespace(self):
        """Test that whitespace is stripped from name and path."""
        tracker = DocTracker()
        response = "[DOC:  PLAN.md  ] path:   /path/to/PLAN.md   "
        result = tracker.parse_response(response)
        
        assert len(result) == 1
        assert result[0]["name"] == "PLAN.md"
        assert result[0]["path"] == "/path/to/PLAN.md"


class TestSaveDocs:
    """Tests for save_docs method."""

    def test_save_empty_docs(self, temp_db, test_request):
        """Test saving empty docs list returns 0."""
        tracker = DocTracker()
        result = tracker.save_docs(test_request["reqid"], [], "plan")
        assert result == 0

    def test_save_single_doc(self, temp_db, test_request):
        """Test saving single document."""
        tracker = DocTracker()
        docs = [{"name": "PLAN.md", "path": "/path/to/PLAN.md"}]
        result = tracker.save_docs(test_request["reqid"], docs, "plan")
        
        assert result == 1
        
        # Verify document was saved
        saved_docs = queries.get_request_docs(test_request["reqid"])
        assert len(saved_docs) == 1
        assert saved_docs[0]["doc_name"] == "PLAN.md"
        assert saved_docs[0]["doc_path"] == "/path/to/PLAN.md"
        assert saved_docs[0]["doc_phase"] == "plan"

    def test_save_multiple_docs(self, temp_db, test_request):
        """Test saving multiple documents."""
        tracker = DocTracker()
        docs = [
            {"name": "PLAN.md", "path": "/path/to/PLAN.md"},
            {"name": "DEV.md", "path": "/path/to/DEV.md"},
            {"name": "TEST.md", "path": "/path/to/TEST.md"},
        ]
        result = tracker.save_docs(test_request["reqid"], docs, "dev")
        
        assert result == 3
        
        # Verify documents were saved
        saved_docs = queries.get_request_docs(test_request["reqid"])
        assert len(saved_docs) == 3

    def test_save_docs_with_different_phases(self, temp_db, test_request):
        """Test saving documents with different phases."""
        tracker = DocTracker()
        
        # Save plan phase doc
        docs1 = [{"name": "PLAN.md", "path": "/path/to/PLAN.md"}]
        tracker.save_docs(test_request["reqid"], docs1, "plan")
        
        # Save dev phase doc
        docs2 = [{"name": "DEV.md", "path": "/path/to/DEV.md"}]
        tracker.save_docs(test_request["reqid"], docs2, "dev")
        
        # Verify both were saved with correct phases
        saved_docs = queries.get_request_docs(test_request["reqid"])
        assert len(saved_docs) == 2
        
        phases = {doc["doc_phase"] for doc in saved_docs}
        assert phases == {"plan", "dev"}

    def test_save_docs_skips_invalid_entries(self, temp_db, test_request):
        """Test that invalid entries (missing name or path) are skipped."""
        tracker = DocTracker()
        docs = [
            {"name": "valid.md", "path": "/path/to/valid.md"},
            {"name": "", "path": "/path/to/empty_name.md"},  # Empty name
            {"name": "no_path.md", "path": ""},  # Empty path
            {"name": None, "path": "/path/to/none_name.md"},  # None name
            {"path": "/path/to/missing_name.md"},  # Missing name key
        ]
        result = tracker.save_docs(test_request["reqid"], docs, "test")
        
        # Only the first valid entry should be saved
        assert result == 1
        
        saved_docs = queries.get_request_docs(test_request["reqid"])
        assert len(saved_docs) == 1
        assert saved_docs[0]["doc_name"] == "valid.md"


class TestIntegration:
    """Integration tests for DocTracker."""

    def test_parse_and_save_workflow(self, temp_db, test_request):
        """Test complete workflow: parse response and save docs."""
        tracker = DocTracker()
        
        response = """
        I have created the following documents:
        [DOC:PLAN.md] path: /project/PLAN.md
        [DOC:architecture.md] path: /project/docs/architecture.md
        
        The implementation is complete.
        """
        
        # Parse the response
        docs = tracker.parse_response(response)
        assert len(docs) == 2
        
        # Save the documents
        saved_count = tracker.save_docs(test_request["reqid"], docs, "plan")
        assert saved_count == 2
        
        # Verify in database
        saved_docs = queries.get_request_docs(test_request["reqid"])
        assert len(saved_docs) == 2
        
        doc_names = {doc["doc_name"] for doc in saved_docs}
        assert doc_names == {"PLAN.md", "architecture.md"}

    def test_handles_no_documents_gracefully(self, temp_db, test_request):
        """Test that no-document responses are handled without error."""
        tracker = DocTracker()
        
        response = "Task completed successfully. No documents were created."
        
        docs = tracker.parse_response(response)
        assert docs == []
        
        saved_count = tracker.save_docs(test_request["reqid"], docs, "dev")
        assert saved_count == 0
        
        # Verify no documents in database
        saved_docs = queries.get_request_docs(test_request["reqid"])
        assert len(saved_docs) == 0
