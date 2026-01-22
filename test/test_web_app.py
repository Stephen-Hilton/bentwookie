"""Tests for web/app.py Flask application."""

import pytest
from pathlib import Path
import tempfile
import json

from bentwookie.web.app import create_app
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
def app(temp_db):
    """Create a Flask test app."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestIndexRoute:
    """Tests for index route."""

    def test_index_returns_ok(self, client):
        """Test index returns OK (may render or redirect)."""
        response = client.get("/")
        # Index may render directly or redirect
        assert response.status_code in (200, 302)


class TestProjectRoutes:
    """Tests for project routes."""

    def test_projects_list_empty(self, client):
        """Test projects list when empty."""
        response = client.get("/projects")
        assert response.status_code == 200
        assert b"Projects" in response.data

    def test_projects_list_with_data(self, client, temp_db):
        """Test projects list with data."""
        queries.create_project("Test Project")

        response = client.get("/projects")
        assert response.status_code == 200
        assert b"Test Project" in response.data

    def test_project_new_form(self, client):
        """Test project creation form."""
        response = client.get("/projects/new")
        assert response.status_code == 200
        assert b"Create Project" in response.data or b"New Project" in response.data

    def test_project_create(self, client):
        """Test creating a project."""
        response = client.post("/projects/new", data={
            "prjname": "New Project",
            "prjversion": "poc",
            "prjpriority": 5,
            "prjphase": "dev",
            "prjdesc": "Description",
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should redirect to projects list
        assert b"New Project" in response.data

    def test_project_view(self, client, temp_db):
        """Test viewing a project."""
        prjid = queries.create_project("View Test")

        response = client.get(f"/projects/{prjid}")
        assert response.status_code == 200
        assert b"View Test" in response.data

    def test_project_view_not_found(self, client):
        """Test viewing non-existent project."""
        response = client.get("/projects/99999")
        assert response.status_code == 302  # Redirects

    def test_project_edit_form(self, client, temp_db):
        """Test project edit form."""
        prjid = queries.create_project("Edit Test")

        response = client.get(f"/projects/{prjid}/edit")
        assert response.status_code == 200
        assert b"Edit Test" in response.data

    def test_project_update(self, client, temp_db):
        """Test updating a project."""
        prjid = queries.create_project("Original")

        response = client.post(f"/projects/{prjid}/edit", data={
            "name": "Updated",
            "version": "mvp",
            "priority": 3,
            "phase": "qa",
            "desc": "Updated desc",
        }, follow_redirects=True)

        assert response.status_code == 200
        project = queries.get_project(prjid)
        assert project["prjname"] == "Updated"

    def test_project_delete(self, client, temp_db):
        """Test deleting a project."""
        prjid = queries.create_project("To Delete")

        response = client.post(f"/projects/{prjid}/delete", follow_redirects=True)
        assert response.status_code == 200

        project = queries.get_project(prjid)
        assert project is None


class TestRequestRoutes:
    """Tests for request routes."""

    def test_requests_list_empty(self, client):
        """Test requests list when empty."""
        response = client.get("/requests")
        assert response.status_code == 200
        assert b"Requests" in response.data

    def test_requests_list_with_data(self, client, temp_db):
        """Test requests list with data."""
        prjid = queries.create_project("Req Project")
        queries.create_request(prjid, "Test Request", "Test prompt")

        response = client.get("/requests")
        assert response.status_code == 200
        assert b"Test Request" in response.data

    def test_requests_list_filtered(self, client, temp_db):
        """Test requests list with filters."""
        prjid = queries.create_project("Filter Project")
        queries.create_request(prjid, "Pending", "Prompt", reqstatus="tbd")
        queries.create_request(prjid, "Done", "Prompt", reqstatus="done")

        response = client.get("/requests?status=tbd")
        assert response.status_code == 200
        assert b"Pending" in response.data

    def test_request_new_form(self, client, temp_db):
        """Test request creation form."""
        queries.create_project("Form Project")

        response = client.get("/requests/new")
        assert response.status_code == 200

    def test_request_create(self, client, temp_db):
        """Test creating a request."""
        prjid = queries.create_project("Create Req Project")

        response = client.post("/requests/new", data={
            "prjid": prjid,
            "reqname": "New Request",
            "reqprompt": "Do something",
            "reqtype": "new_feature",
            "reqpriority": 5,
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_request_view(self, client, temp_db):
        """Test viewing a request."""
        prjid = queries.create_project("View Req Project")
        reqid = queries.create_request(prjid, "View Test", "Prompt")

        response = client.get(f"/requests/{reqid}")
        assert response.status_code == 200
        assert b"View Test" in response.data

    def test_request_view_with_error(self, client, temp_db):
        """Test viewing a request with error."""
        prjid = queries.create_project("Error Project")
        reqid = queries.create_request(prjid, "Error Test", "Prompt")
        queries.update_request_error(reqid, "Test error message")
        queries.update_request_status(reqid, "err")

        response = client.get(f"/requests/{reqid}")
        assert response.status_code == 200
        assert b"Test error message" in response.data

    def test_request_update_status(self, client, temp_db):
        """Test updating request status."""
        prjid = queries.create_project("Update Project")
        reqid = queries.create_request(prjid, "Update Test", "Prompt")

        response = client.post(f"/requests/{reqid}/update", data={
            "status": "wip",
        }, follow_redirects=True)

        assert response.status_code == 200
        request = queries.get_request(reqid)
        assert request["reqstatus"] == "wip"

    def test_request_delete(self, client, temp_db):
        """Test deleting a request."""
        prjid = queries.create_project("Delete Req Project")
        reqid = queries.create_request(prjid, "To Delete", "Prompt")

        response = client.post(f"/requests/{reqid}/delete", follow_redirects=True)
        assert response.status_code == 200

        request = queries.get_request(reqid)
        assert request is None


class TestStatusRoute:
    """Tests for status route."""

    def test_status_page(self, client, monkeypatch):
        """Test status page."""
        from bentwookie.loop import daemon

        monkeypatch.setattr(daemon, "is_daemon_running", lambda: False)
        monkeypatch.setattr(daemon, "read_pid_file", lambda: None)

        response = client.get("/status")
        assert response.status_code == 200
        assert b"Status" in response.data

    def test_status_page_with_daemon(self, client, monkeypatch):
        """Test status page when daemon is running."""
        from bentwookie.loop import daemon

        monkeypatch.setattr(daemon, "is_daemon_running", lambda: True)
        monkeypatch.setattr(daemon, "read_pid_file", lambda: 12345)

        response = client.get("/status")
        assert response.status_code == 200
        assert b"12345" in response.data


class TestAPIRoutes:
    """Tests for API routes."""

    def test_api_loop_pause(self, client, temp_db, monkeypatch):
        """Test pausing the loop via API."""
        from bentwookie import settings
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            monkeypatch.setattr(settings, "DEFAULT_SETTINGS_PATH", settings_path)

            response = client.post("/api/loop/pause")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["paused"] is True

    def test_api_loop_resume(self, client, temp_db, monkeypatch):
        """Test resuming the loop via API."""
        from bentwookie import settings
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            monkeypatch.setattr(settings, "DEFAULT_SETTINGS_PATH", settings_path)

            # First pause
            client.post("/api/loop/pause")

            # Then resume
            response = client.post("/api/loop/resume")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["paused"] is False

    def test_api_loop_settings_get(self, client, temp_db, monkeypatch):
        """Test getting loop settings via API."""
        from bentwookie import settings
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            monkeypatch.setattr(settings, "DEFAULT_SETTINGS_PATH", settings_path)

            response = client.get("/api/loop/settings")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert "loop_paused" in data
            assert "poll_interval" in data
            assert "doc_retention_days" in data

    def test_api_loop_settings_post(self, client, temp_db, monkeypatch):
        """Test updating loop settings via API."""
        from bentwookie import settings
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            monkeypatch.setattr(settings, "DEFAULT_SETTINGS_PATH", settings_path)

            response = client.post("/api/loop/settings",
                json={
                    "poll_interval": 60,
                    "max_iterations": 10,
                    "doc_retention_days": 45,
                },
                content_type="application/json"
            )
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["poll_interval"] == 60
            assert data["max_iterations"] == 10
            assert data["doc_retention_days"] == 45


class TestInfrastructureRoutes:
    """Tests for infrastructure routes."""

    def test_add_project_infrastructure(self, client, temp_db):
        """Test adding infrastructure to a project."""
        prjid = queries.create_project("Infra Project")

        response = client.post(f"/projects/{prjid}/infrastructure/add", data={
            "inftype": "compute",
            "infprovider": "aws",
            "infval": "t2.micro",
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_delete_project_infrastructure(self, client, temp_db):
        """Test deleting project infrastructure."""
        prjid = queries.create_project("Del Infra Project")
        infid = queries.add_infrastructure(prjid, "compute")

        response = client.post(f"/infrastructure/{infid}/delete", data={
            "prjid": prjid,
        }, follow_redirects=True)

        assert response.status_code == 200
