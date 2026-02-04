"""Tests for database queries module."""

import pytest
from pathlib import Path
import tempfile

from bentwookie.db import connection, queries


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    connection.set_db_path(db_path)
    connection.init_db()

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


class TestProjectOperations:
    """Tests for project CRUD operations."""

    def test_create_project(self, temp_db):
        """Test creating a project."""
        prjid = queries.create_project("test_project", prjdesc="Test description")
        assert prjid is not None
        assert prjid > 0

    def test_create_project_with_all_fields(self, temp_db):
        """Test creating a project with all optional fields."""
        prjid = queries.create_project(
            prjname="full_project",
            prjversion="mvp",
            prjpriority=3,
            prjphase="qa",
            prjdesc="Full description",
            prjcodedir="/path/to/code",
        )

        project = queries.get_project(prjid)
        assert project["prjname"] == "full_project"
        assert project["prjversion"] == "mvp"
        assert project["prjpriority"] == 3
        assert project["prjphase"] == "qa"
        assert project["prjdesc"] == "Full description"
        assert project["prjcodedir"] == "/path/to/code"

    def test_get_project(self, temp_db):
        """Test getting a project by ID."""
        prjid = queries.create_project("get_test")
        project = queries.get_project(prjid)

        assert project is not None
        assert project["prjname"] == "get_test"

    def test_get_project_not_found(self, temp_db):
        """Test getting a non-existent project."""
        project = queries.get_project(99999)
        assert project is None

    def test_get_project_by_name(self, temp_db):
        """Test getting a project by name."""
        queries.create_project("named_project")
        project = queries.get_project_by_name("named_project")

        assert project is not None
        assert project["prjname"] == "named_project"

    def test_get_project_by_name_not_found(self, temp_db):
        """Test getting a non-existent project by name."""
        project = queries.get_project_by_name("nonexistent")
        assert project is None

    def test_list_projects(self, temp_db):
        """Test listing all projects."""
        queries.create_project("proj1", prjpriority=1)
        queries.create_project("proj2", prjpriority=2)
        queries.create_project("proj3", prjpriority=3)

        projects = queries.list_projects()
        assert len(projects) == 3

    def test_list_projects_by_phase(self, temp_db):
        """Test listing projects filtered by phase."""
        queries.create_project("dev_proj", prjphase="dev")
        queries.create_project("qa_proj", prjphase="qa")

        dev_projects = queries.list_projects(phase="dev")
        assert len(dev_projects) == 1
        assert dev_projects[0]["prjname"] == "dev_proj"

    def test_update_project(self, temp_db):
        """Test updating a project."""
        prjid = queries.create_project("original")

        result = queries.update_project(prjid, prjname="updated", prjpriority=1)
        assert result is True

        project = queries.get_project(prjid)
        assert project["prjname"] == "updated"
        assert project["prjpriority"] == 1

    def test_update_project_no_changes(self, temp_db):
        """Test updating a project with no fields."""
        prjid = queries.create_project("no_change")
        result = queries.update_project(prjid)
        assert result is False

    def test_update_project_not_found(self, temp_db):
        """Test updating a non-existent project."""
        result = queries.update_project(99999, prjname="new")
        assert result is False

    def test_delete_project(self, temp_db):
        """Test deleting a project."""
        prjid = queries.create_project("to_delete")

        result = queries.delete_project(prjid)
        assert result is True

        project = queries.get_project(prjid)
        assert project is None

    def test_delete_project_not_found(self, temp_db):
        """Test deleting a non-existent project."""
        result = queries.delete_project(99999)
        assert result is False

    def test_delete_project_cascades(self, temp_db):
        """Test that deleting a project deletes related records."""
        prjid = queries.create_project("cascade_test")
        reqid = queries.create_request(prjid, "req", "prompt")
        queries.add_infrastructure(prjid, "compute")
        queries.add_learning(prjid, "test learning")

        queries.delete_project(prjid)

        # All related records should be deleted
        assert queries.get_request(reqid) is None


class TestRequestOperations:
    """Tests for request CRUD operations."""

    def test_create_request(self, temp_db):
        """Test creating a request."""
        prjid = queries.create_project("req_project")
        reqid = queries.create_request(prjid, "test_request", "test prompt")

        assert reqid is not None
        assert reqid > 0

    def test_create_request_with_all_fields(self, temp_db):
        """Test creating a request with all optional fields."""
        prjid = queries.create_project("full_req_project")
        reqid = queries.create_request(
            prjid=prjid,
            reqname="full_request",
            reqprompt="detailed prompt",
            reqtype="bug_fix",
            reqstatus="wip",
            reqphase="dev",
            reqpriority=2,
            reqcodedir="/code/dir",
        )

        request = queries.get_request(reqid)
        assert request["reqname"] == "full_request"
        assert request["reqtype"] == "bug_fix"
        assert request["reqstatus"] == "wip"
        assert request["reqphase"] == "dev"
        assert request["reqpriority"] == 2

    def test_get_request(self, temp_db):
        """Test getting a request by ID."""
        prjid = queries.create_project("get_req_project")
        reqid = queries.create_request(prjid, "get_test", "prompt")

        request = queries.get_request(reqid)
        assert request is not None
        assert request["reqname"] == "get_test"

    def test_get_request_not_found(self, temp_db):
        """Test getting a non-existent request."""
        request = queries.get_request(99999)
        assert request is None

    def test_get_next_request(self, temp_db):
        """Test getting the next request to process."""
        prjid = queries.create_project("next_project")
        queries.create_request(prjid, "low_priority", "prompt", reqpriority=10)
        queries.create_request(prjid, "high_priority", "prompt", reqpriority=1)

        next_req = queries.get_next_request()
        assert next_req is not None
        assert next_req["reqname"] == "high_priority"

    def test_get_next_request_none_pending(self, temp_db):
        """Test getting next request when none are pending."""
        prjid = queries.create_project("no_pending")
        queries.create_request(prjid, "done_req", "prompt", reqstatus="done")

        next_req = queries.get_next_request()
        assert next_req is None

    def test_list_requests(self, temp_db):
        """Test listing all requests."""
        prjid = queries.create_project("list_project")
        queries.create_request(prjid, "req1", "prompt1")
        queries.create_request(prjid, "req2", "prompt2")

        requests = queries.list_requests()
        assert len(requests) == 2

    def test_list_requests_by_project(self, temp_db):
        """Test listing requests filtered by project."""
        prjid1 = queries.create_project("proj1")
        prjid2 = queries.create_project("proj2")
        queries.create_request(prjid1, "req1", "prompt1")
        queries.create_request(prjid2, "req2", "prompt2")

        requests = queries.list_requests(prjid=prjid1)
        assert len(requests) == 1
        assert requests[0]["reqname"] == "req1"

    def test_list_requests_by_status(self, temp_db):
        """Test listing requests filtered by status."""
        prjid = queries.create_project("status_project")
        queries.create_request(prjid, "pending", "prompt", reqstatus="tbd")
        queries.create_request(prjid, "done", "prompt", reqstatus="done")

        requests = queries.list_requests(status="tbd")
        assert len(requests) == 1
        assert requests[0]["reqname"] == "pending"

    def test_list_requests_by_phase(self, temp_db):
        """Test listing requests filtered by phase."""
        prjid = queries.create_project("phase_project")
        queries.create_request(prjid, "plan_req", "prompt", reqphase="plan")
        queries.create_request(prjid, "dev_req", "prompt", reqphase="dev")

        requests = queries.list_requests(phase="plan")
        assert len(requests) == 1
        assert requests[0]["reqname"] == "plan_req"

    def test_update_request_status(self, temp_db):
        """Test updating a request's status."""
        prjid = queries.create_project("status_update")
        reqid = queries.create_request(prjid, "req", "prompt")

        result = queries.update_request_status(reqid, "wip")
        assert result is True

        request = queries.get_request(reqid)
        assert request["reqstatus"] == "wip"

    def test_update_request_phase(self, temp_db):
        """Test updating a request's phase."""
        prjid = queries.create_project("phase_update")
        reqid = queries.create_request(prjid, "req", "prompt")

        result = queries.update_request_phase(reqid, "dev")
        assert result is True

        request = queries.get_request(reqid)
        assert request["reqphase"] == "dev"

    def test_update_request_error(self, temp_db):
        """Test updating a request's error message."""
        prjid = queries.create_project("error_update")
        reqid = queries.create_request(prjid, "req", "prompt")

        result = queries.update_request_error(reqid, "Test error message")
        assert result is True

        request = queries.get_request(reqid)
        assert request["reqerror"] == "Test error message"

    def test_update_request_error_clear(self, temp_db):
        """Test clearing a request's error message."""
        prjid = queries.create_project("error_clear")
        reqid = queries.create_request(prjid, "req", "prompt")
        queries.update_request_error(reqid, "Error")

        result = queries.update_request_error(reqid, None)
        assert result is True

        request = queries.get_request(reqid)
        assert request["reqerror"] is None

    def test_update_request_docpath(self, temp_db):
        """Test updating a request's doc path."""
        prjid = queries.create_project("docpath_update")
        reqid = queries.create_request(prjid, "req", "prompt")

        result = queries.update_request_docpath(reqid, "/path/to/doc.md")
        assert result is True

        request = queries.get_request(reqid)
        assert request["reqdocpath"] == "/path/to/doc.md"

    def test_update_request_codedir(self, temp_db):
        """Test updating a request's code directory."""
        prjid = queries.create_project("codedir_update")
        reqid = queries.create_request(prjid, "req", "prompt")

        result = queries.update_request_codedir(reqid, "/path/to/code")
        assert result is True

        request = queries.get_request(reqid)
        assert request["reqcodedir"] == "/path/to/code"

    def test_update_request_planpath(self, temp_db):
        """Test updating a request's plan path."""
        prjid = queries.create_project("planpath_update")
        reqid = queries.create_request(prjid, "req", "prompt")

        result = queries.update_request_planpath(reqid, "/path/to/plan.md")
        assert result is True

        request = queries.get_request(reqid)
        assert request["reqplanpath"] == "/path/to/plan.md"

    def test_update_request_testplanpath(self, temp_db):
        """Test updating a request's test plan path."""
        prjid = queries.create_project("testplan_update")
        reqid = queries.create_request(prjid, "req", "prompt")

        result = queries.update_request_testplanpath(reqid, "/path/to/testplan.md")
        assert result is True

        request = queries.get_request(reqid)
        assert request["reqtestplanpath"] == "/path/to/testplan.md"

    def test_increment_request_test_retries(self, temp_db):
        """Test incrementing a request's test retries."""
        prjid = queries.create_project("retry_project")
        reqid = queries.create_request(prjid, "req", "prompt")

        count = queries.increment_request_test_retries(reqid)
        assert count == 1

        count = queries.increment_request_test_retries(reqid)
        assert count == 2

    def test_reset_request_test_retries(self, temp_db):
        """Test resetting a request's test retries."""
        prjid = queries.create_project("reset_retry")
        reqid = queries.create_request(prjid, "req", "prompt")
        queries.increment_request_test_retries(reqid)
        queries.increment_request_test_retries(reqid)

        result = queries.reset_request_test_retries(reqid)
        assert result is True

        request = queries.get_request(reqid)
        assert request["reqtestretries"] == 0

    def test_update_request(self, temp_db):
        """Test full request update."""
        prjid = queries.create_project("full_update")
        reqid = queries.create_request(prjid, "original", "original prompt")

        result = queries.update_request(
            reqid,
            reqname="updated",
            reqprompt="new prompt",
            reqtype="enhancement",
            reqpriority=1,
        )
        assert result is True

        request = queries.get_request(reqid)
        assert request["reqname"] == "updated"
        assert request["reqprompt"] == "new prompt"
        assert request["reqtype"] == "enhancement"
        assert request["reqpriority"] == 1

    def test_delete_request(self, temp_db):
        """Test deleting a request."""
        prjid = queries.create_project("delete_project")
        reqid = queries.create_request(prjid, "to_delete", "prompt")

        result = queries.delete_request(reqid)
        assert result is True

        request = queries.get_request(reqid)
        assert request is None


class TestInfrastructureOperations:
    """Tests for infrastructure CRUD operations."""

    def test_add_infrastructure(self, temp_db):
        """Test adding infrastructure."""
        prjid = queries.create_project("infra_project")
        infid = queries.add_infrastructure(prjid, "compute", "aws", "t2.micro")

        assert infid is not None
        assert infid > 0

    def test_get_project_infrastructure(self, temp_db):
        """Test getting project infrastructure."""
        prjid = queries.create_project("get_infra")
        queries.add_infrastructure(prjid, "compute", "aws")
        queries.add_infrastructure(prjid, "storage", "local")

        infra = queries.get_project_infrastructure(prjid)
        assert len(infra) == 2

    def test_delete_infrastructure(self, temp_db):
        """Test deleting infrastructure."""
        prjid = queries.create_project("del_infra")
        infid = queries.add_infrastructure(prjid, "compute")

        result = queries.delete_infrastructure(infid)
        assert result is True

        infra = queries.get_project_infrastructure(prjid)
        assert len(infra) == 0

    def test_update_infrastructure(self, temp_db):
        """Test updating infrastructure."""
        prjid = queries.create_project("upd_infra")
        infid = queries.add_infrastructure(prjid, "compute", "local")

        result = queries.update_infrastructure(infid, infprovider="aws", infval="t2.micro")
        assert result is True


class TestRequestInfrastructureOperations:
    """Tests for request infrastructure operations."""

    def test_add_request_infrastructure(self, temp_db):
        """Test adding request infrastructure override."""
        prjid = queries.create_project("req_infra_proj")
        reqid = queries.create_request(prjid, "req", "prompt")
        rinfid = queries.add_request_infrastructure(reqid, "compute", "aws")

        assert rinfid is not None

    def test_get_request_infrastructure(self, temp_db):
        """Test getting request infrastructure."""
        prjid = queries.create_project("get_req_infra")
        reqid = queries.create_request(prjid, "req", "prompt")
        queries.add_request_infrastructure(reqid, "compute")

        infra = queries.get_request_infrastructure(reqid)
        assert len(infra) == 1

    def test_get_effective_infrastructure(self, temp_db):
        """Test getting merged infrastructure (project + request)."""
        prjid = queries.create_project("eff_infra")
        queries.add_infrastructure(prjid, "compute", "local")
        queries.add_infrastructure(prjid, "storage", "local")

        reqid = queries.create_request(prjid, "req", "prompt")
        queries.add_request_infrastructure(reqid, "compute", "aws")  # Override

        effective = queries.get_effective_infrastructure(reqid)

        assert "compute" in effective
        assert effective["compute"]["infprovider"] == "aws"  # Request override
        assert effective["compute"]["source"] == "request"

        assert "storage" in effective
        assert effective["storage"]["infprovider"] == "local"  # From project
        assert effective["storage"]["source"] == "project"


class TestLearningOperations:
    """Tests for learning CRUD operations."""

    def test_add_learning(self, temp_db):
        """Test adding a learning."""
        prjid = queries.create_project("learn_project")
        lrnid = queries.add_learning(prjid, "Test learning")

        assert lrnid is not None

    def test_add_global_learning(self, temp_db):
        """Test adding a global learning (prjid=-1)."""
        lrnid = queries.add_learning(-1, "Global learning")

        assert lrnid is not None

    def test_get_project_learnings(self, temp_db):
        """Test getting project learnings."""
        prjid = queries.create_project("get_learn")
        queries.add_learning(prjid, "Learning 1")
        queries.add_learning(prjid, "Learning 2")

        learnings = queries.get_project_learnings(prjid)
        assert len(learnings) == 2

    def test_get_learnings_with_global(self, temp_db):
        """Test getting learnings including global ones."""
        prjid = queries.create_project("learn_with_global")
        queries.add_learning(prjid, "Project learning")
        queries.add_learning(-1, "Global learning")

        learnings = queries.get_learnings_with_global(prjid)
        assert len(learnings) == 2

    def test_delete_learning(self, temp_db):
        """Test deleting a learning."""
        prjid = queries.create_project("del_learn")
        lrnid = queries.add_learning(prjid, "To delete")

        result = queries.delete_learning(lrnid)
        assert result is True

    def test_get_learning(self, temp_db):
        """Test getting a learning by ID."""
        prjid = queries.create_project("get_single_learn")
        lrnid = queries.add_learning(prjid, "Test")

        learning = queries.get_learning(lrnid)
        assert learning is not None
        assert learning["lrndesc"] == "Test"

    def test_update_learning(self, temp_db):
        """Test updating a learning."""
        prjid = queries.create_project("upd_learn")
        lrnid = queries.add_learning(prjid, "Original")

        result = queries.update_learning(lrnid, "Updated")
        assert result is True

        learning = queries.get_learning(lrnid)
        assert learning["lrndesc"] == "Updated"

    def test_list_all_learnings(self, temp_db):
        """Test listing all learnings."""
        prjid1 = queries.create_project("learn_proj1")
        prjid2 = queries.create_project("learn_proj2")
        queries.add_learning(prjid1, "L1")
        queries.add_learning(prjid2, "L2")

        all_learnings = queries.list_all_learnings()
        assert len(all_learnings) == 2


class TestInfraOptionOperations:
    """Tests for infrastructure option operations."""

    def test_add_infra_option(self, temp_db):
        """Test adding an infra option."""
        optid = queries.add_infra_option("compute", "Test Option", "aws")
        assert optid is not None

    def test_get_infra_options(self, temp_db):
        """Test getting infra options."""
        queries.add_infra_option("compute", "Opt1")
        queries.add_infra_option("storage", "Opt2")

        all_opts = queries.get_infra_options()
        assert len(all_opts) == 2

        compute_opts = queries.get_infra_options("compute")
        assert len(compute_opts) == 1

    def test_get_infra_options_by_type(self, temp_db):
        """Test getting infra option names by type."""
        queries.add_infra_option("compute", "Lambda")
        queries.add_infra_option("compute", "EC2")

        names = queries.get_infra_options_by_type("compute")
        assert "Lambda" in names
        assert "EC2" in names

    def test_delete_infra_option(self, temp_db):
        """Test deleting an infra option."""
        queries.add_infra_option("compute", "ToDelete")

        result = queries.delete_infra_option("compute", "ToDelete")
        assert result is True

    def test_delete_infra_option_by_id(self, temp_db):
        """Test deleting an infra option by ID."""
        optid = queries.add_infra_option("compute", "ToDeleteById")

        result = queries.delete_infra_option_by_id(optid)
        assert result is True


class TestDaemonStateOperations:
    """Tests for daemon state operations."""

    def test_set_daemon_pid(self, temp_db):
        """Test setting daemon PID."""
        queries.set_daemon_pid(12345, "test_loop")

        pid = queries.get_daemon_pid()
        assert pid == 12345

    def test_get_daemon_pid_not_set(self, temp_db):
        """Test getting daemon PID when not set."""
        pid = queries.get_daemon_pid()
        assert pid is None

    def test_get_daemon_info(self, temp_db):
        """Test getting full daemon info."""
        queries.set_daemon_pid(12345, "test_loop")

        info = queries.get_daemon_info()
        assert info is not None
        assert info["pid"] == 12345
        assert info["loop_name"] == "test_loop"
        assert info["started_at"] is not None

    def test_get_daemon_info_not_set(self, temp_db):
        """Test getting daemon info when not set."""
        info = queries.get_daemon_info()
        assert info is None

    def test_clear_daemon_pid(self, temp_db):
        """Test clearing daemon PID."""
        queries.set_daemon_pid(12345, "test_loop")
        assert queries.get_daemon_pid() == 12345

        queries.clear_daemon_pid()
        assert queries.get_daemon_pid() is None

    def test_update_daemon_heartbeat(self, temp_db):
        """Test updating daemon heartbeat."""
        queries.set_daemon_pid(12345, "test_loop")
        info1 = queries.get_daemon_info()

        import time
        time.sleep(0.1)

        queries.update_daemon_heartbeat()
        info2 = queries.get_daemon_info()

        # Heartbeat should be updated
        assert info2["updated_at"] >= info1["updated_at"]

    def test_set_daemon_pid_overwrites(self, temp_db):
        """Test that setting PID overwrites previous value."""
        queries.set_daemon_pid(11111, "loop1")
        queries.set_daemon_pid(22222, "loop2")

        pid = queries.get_daemon_pid()
        assert pid == 22222

        info = queries.get_daemon_info()
        assert info["loop_name"] == "loop2"


class TestRequestDocOperations:
    """Tests for request document CRUD operations."""

    def test_create_request_doc(self, temp_db):
        """Test creating a request document."""
        prjid = queries.create_project("doc_project")
        reqid = queries.create_request(prjid, "doc_request", "prompt")
        docid = queries.create_request_doc(reqid, "PLAN.md", "/path/to/PLAN.md", "plan")

        assert docid is not None
        assert docid > 0

    def test_create_request_doc_without_phase(self, temp_db):
        """Test creating a request document without a phase."""
        prjid = queries.create_project("doc_project_no_phase")
        reqid = queries.create_request(prjid, "doc_request", "prompt")
        docid = queries.create_request_doc(reqid, "custom.md", "/path/to/custom.md")

        assert docid is not None
        doc = queries.get_request_doc(docid)
        assert doc["doc_phase"] is None

    def test_get_request_doc(self, temp_db):
        """Test getting a single document by ID."""
        prjid = queries.create_project("get_doc_project")
        reqid = queries.create_request(prjid, "get_doc_request", "prompt")
        docid = queries.create_request_doc(reqid, "TEST.md", "/path/to/TEST.md", "test")

        doc = queries.get_request_doc(docid)
        assert doc is not None
        assert doc["docid"] == docid
        assert doc["reqid"] == reqid
        assert doc["doc_name"] == "TEST.md"
        assert doc["doc_path"] == "/path/to/TEST.md"
        assert doc["doc_phase"] == "test"
        assert doc["created_at"] is not None

    def test_get_request_doc_not_found(self, temp_db):
        """Test getting a non-existent document."""
        doc = queries.get_request_doc(99999)
        assert doc is None

    def test_get_request_docs(self, temp_db):
        """Test getting all documents for a request."""
        prjid = queries.create_project("get_docs_project")
        reqid = queries.create_request(prjid, "get_docs_request", "prompt")
        queries.create_request_doc(reqid, "PLAN.md", "/path/to/PLAN.md", "plan")
        queries.create_request_doc(reqid, "DEV.md", "/path/to/DEV.md", "dev")
        queries.create_request_doc(reqid, "TEST.md", "/path/to/TEST.md", "test")

        docs = queries.get_request_docs(reqid)
        assert len(docs) == 3

    def test_get_request_docs_empty(self, temp_db):
        """Test getting documents for a request with no documents."""
        prjid = queries.create_project("empty_docs_project")
        reqid = queries.create_request(prjid, "empty_docs_request", "prompt")

        docs = queries.get_request_docs(reqid)
        assert docs == []

    def test_get_request_docs_returns_all_docs(self, temp_db):
        """Test that get_request_docs returns all documents for a request."""
        prjid = queries.create_project("ordered_docs_project")
        reqid = queries.create_request(prjid, "ordered_docs_request", "prompt")
        
        # Create multiple documents
        queries.create_request_doc(reqid, "first.md", "/path/first.md", "plan")
        queries.create_request_doc(reqid, "second.md", "/path/second.md", "dev")
        queries.create_request_doc(reqid, "third.md", "/path/third.md", "test")

        docs = queries.get_request_docs(reqid)
        # All documents should be returned
        assert len(docs) == 3
        doc_names = {d["doc_name"] for d in docs}
        assert doc_names == {"first.md", "second.md", "third.md"}

    def test_delete_request_docs(self, temp_db):
        """Test deleting all documents for a request."""
        prjid = queries.create_project("del_docs_project")
        reqid = queries.create_request(prjid, "del_docs_request", "prompt")
        queries.create_request_doc(reqid, "doc1.md", "/path/doc1.md", "plan")
        queries.create_request_doc(reqid, "doc2.md", "/path/doc2.md", "dev")

        count = queries.delete_request_docs(reqid)
        assert count == 2

        docs = queries.get_request_docs(reqid)
        assert docs == []

    def test_delete_request_docs_returns_zero_when_none(self, temp_db):
        """Test that delete returns 0 when no documents exist."""
        prjid = queries.create_project("no_docs_project")
        reqid = queries.create_request(prjid, "no_docs_request", "prompt")

        count = queries.delete_request_docs(reqid)
        assert count == 0

    def test_multiple_requests_have_separate_docs(self, temp_db):
        """Test that documents are correctly associated with their requests."""
        prjid = queries.create_project("multi_req_project")
        reqid1 = queries.create_request(prjid, "request1", "prompt1")
        reqid2 = queries.create_request(prjid, "request2", "prompt2")

        queries.create_request_doc(reqid1, "req1_doc.md", "/path/req1_doc.md", "plan")
        queries.create_request_doc(reqid2, "req2_doc.md", "/path/req2_doc.md", "dev")

        docs1 = queries.get_request_docs(reqid1)
        docs2 = queries.get_request_docs(reqid2)

        assert len(docs1) == 1
        assert len(docs2) == 1
        assert docs1[0]["doc_name"] == "req1_doc.md"
        assert docs2[0]["doc_name"] == "req2_doc.md"

    def test_create_request_doc_with_arbitrary_names(self, temp_db):
        """Test creating documents with arbitrary names including phase names and custom names."""
        prjid = queries.create_project("arbitrary_names_project")
        reqid = queries.create_request(prjid, "arbitrary_names_request", "prompt")

        # Phase names
        docid1 = queries.create_request_doc(reqid, "plan", "/path/plan.md", "plan")
        docid2 = queries.create_request_doc(reqid, "dev", "/path/dev.md", "dev")
        docid3 = queries.create_request_doc(reqid, "test", "/path/test.md", "test")
        docid4 = queries.create_request_doc(reqid, "document", "/path/document.md", "document")

        # Custom names
        docid5 = queries.create_request_doc(reqid, "IP_Output.md", "/path/IP_Output.md", "dev")
        docid6 = queries.create_request_doc(reqid, "custom_report.txt", "/path/custom_report.txt")

        docs = queries.get_request_docs(reqid)
        assert len(docs) == 6

        doc_names = [d["doc_name"] for d in docs]
        assert "plan" in doc_names
        assert "dev" in doc_names
        assert "test" in doc_names
        assert "document" in doc_names
        assert "IP_Output.md" in doc_names
        assert "custom_report.txt" in doc_names
