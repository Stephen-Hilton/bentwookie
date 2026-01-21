"""Flask application for BentWookie web UI."""

from flask import Flask, flash, redirect, render_template, request, url_for

from ..constants import (
    DEFAULT_PRIORITY,
    PHASE_NAMES,
    PHASES,
    STATUS_NAMES,
    TYPE_NAMES,
    V2_STATUSES,
    VALID_PROJECT_PHASES,
    VALID_REQUEST_TYPES,
    VALID_VERSIONS,
)
from ..db import (
    create_project,
    create_request,
    delete_project,
    delete_request,
    get_project,
    get_request,
    init_db,
    list_projects,
    list_requests,
    update_request_phase,
    update_request_status,
)


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Configured Flask app.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    app.secret_key = "bentwookie-secret-key-change-in-production"

    # Ensure database is initialized
    init_db()

    # Register routes
    register_routes(app)

    # Add template context
    @app.context_processor
    def inject_constants():
        return {
            "STATUS_NAMES": STATUS_NAMES,
            "TYPE_NAMES": TYPE_NAMES,
            "PHASE_NAMES": PHASE_NAMES,
            "VALID_VERSIONS": VALID_VERSIONS,
            "VALID_PROJECT_PHASES": VALID_PROJECT_PHASES,
            "VALID_REQUEST_TYPES": VALID_REQUEST_TYPES,
            "V2_STATUSES": V2_STATUSES,
            "PHASES": PHASES,
        }

    return app


def register_routes(app: Flask) -> None:
    """Register all routes for the application.

    Args:
        app: Flask application instance.
    """

    @app.route("/")
    def index():
        """Dashboard page."""
        projects = list_projects()
        requests = list_requests()

        # Calculate stats
        stats = {
            "projects": len(projects),
            "requests": len(requests),
            "pending": sum(1 for r in requests if r["reqstatus"] == "tbd"),
            "in_progress": sum(1 for r in requests if r["reqstatus"] == "wip"),
            "done": sum(1 for r in requests if r["reqstatus"] == "done"),
            "errors": sum(1 for r in requests if r["reqstatus"] in ("err", "tmout")),
        }

        # Recent requests
        recent_requests = sorted(requests, key=lambda r: r.get("reqtouchts", ""), reverse=True)[:5]

        return render_template(
            "base.html",
            page="dashboard",
            stats=stats,
            recent_requests=recent_requests,
        )

    @app.route("/projects")
    def projects_list():
        """List all projects."""
        projects = list_projects()

        # Add request counts
        for p in projects:
            reqs = list_requests(prjid=p["prjid"])
            p["request_count"] = len(reqs)
            p["pending_count"] = sum(1 for r in reqs if r["reqstatus"] == "tbd")

        return render_template("projects.html", projects=projects)

    @app.route("/projects/new", methods=["GET", "POST"])
    def project_new():
        """Create a new project."""
        if request.method == "POST":
            try:
                prjid = create_project(
                    prjname=request.form["name"],
                    prjversion=request.form.get("version", "poc"),
                    prjpriority=int(request.form.get("priority", DEFAULT_PRIORITY)),
                    prjphase=request.form.get("phase", "dev"),
                    prjdesc=request.form.get("desc"),
                )
                flash(f"Project created successfully (ID: {prjid})", "success")
                return redirect(url_for("projects_list"))
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    flash("A project with that name already exists", "error")
                else:
                    flash(f"Error creating project: {e}", "error")

        return render_template("project_form.html", project=None)

    @app.route("/projects/<int:prjid>")
    def project_view(prjid: int):
        """View a project."""
        project = get_project(prjid)
        if not project:
            flash("Project not found", "error")
            return redirect(url_for("projects_list"))

        requests = list_requests(prjid=prjid)

        return render_template("project_view.html", project=project, requests=requests)

    @app.route("/projects/<int:prjid>/delete", methods=["POST"])
    def project_delete_route(prjid: int):
        """Delete a project."""
        project = get_project(prjid)
        if not project:
            flash("Project not found", "error")
            return redirect(url_for("projects_list"))

        delete_project(prjid)
        flash(f"Project '{project['prjname']}' deleted", "success")
        return redirect(url_for("projects_list"))

    @app.route("/requests")
    def requests_list():
        """List all requests."""
        # Get filter parameters
        project_id = request.args.get("project", type=int)
        status = request.args.get("status")
        phase = request.args.get("phase")

        requests_data = list_requests(prjid=project_id, status=status, phase=phase)
        projects = list_projects()

        return render_template(
            "requests.html",
            requests=requests_data,
            projects=projects,
            filter_project=project_id,
            filter_status=status,
            filter_phase=phase,
        )

    @app.route("/requests/new", methods=["GET", "POST"])
    def request_new():
        """Create a new request."""
        projects = list_projects()

        if request.method == "POST":
            try:
                reqid = create_request(
                    prjid=int(request.form["project"]),
                    reqname=request.form["name"],
                    reqprompt=request.form["prompt"],
                    reqtype=request.form.get("type", "new_feature"),
                    reqpriority=int(request.form.get("priority", DEFAULT_PRIORITY)),
                    reqcodedir=request.form.get("codedir") or None,
                )
                flash(f"Request created successfully (ID: {reqid})", "success")
                return redirect(url_for("requests_list"))
            except Exception as e:
                flash(f"Error creating request: {e}", "error")

        return render_template("request_form.html", req=None, projects=projects)

    @app.route("/requests/<int:reqid>")
    def request_view(reqid: int):
        """View a request."""
        req = get_request(reqid)
        if not req:
            flash("Request not found", "error")
            return redirect(url_for("requests_list"))

        project = get_project(req["prjid"])

        return render_template("request_view.html", req=req, project=project)

    @app.route("/requests/<int:reqid>/update", methods=["POST"])
    def request_update_route(reqid: int):
        """Update a request's status or phase."""
        req = get_request(reqid)
        if not req:
            flash("Request not found", "error")
            return redirect(url_for("requests_list"))

        new_status = request.form.get("status")
        new_phase = request.form.get("phase")

        if new_status and new_status != req["reqstatus"]:
            update_request_status(reqid, new_status)
            flash(f"Status updated to {STATUS_NAMES.get(new_status, new_status)}", "success")

        if new_phase and new_phase != req["reqphase"]:
            update_request_phase(reqid, new_phase)
            flash(f"Phase updated to {PHASE_NAMES.get(new_phase, new_phase)}", "success")

        return redirect(url_for("request_view", reqid=reqid))

    @app.route("/requests/<int:reqid>/delete", methods=["POST"])
    def request_delete_route(reqid: int):
        """Delete a request."""
        req = get_request(reqid)
        if not req:
            flash("Request not found", "error")
            return redirect(url_for("requests_list"))

        delete_request(reqid)
        flash(f"Request '{req['reqname']}' deleted", "success")
        return redirect(url_for("requests_list"))

    @app.route("/status")
    def status_page():
        """Status page showing daemon and system state."""
        from ..loop.daemon import is_daemon_running, read_pid_file

        daemon_running = is_daemon_running()
        daemon_pid = read_pid_file() if daemon_running else None

        projects = list_projects()
        requests = list_requests()

        # Calculate status breakdown
        status_counts = {}
        for r in requests:
            s = r["reqstatus"]
            status_counts[s] = status_counts.get(s, 0) + 1

        # Calculate phase breakdown
        phase_counts = {}
        for r in requests:
            p = r["reqphase"]
            phase_counts[p] = phase_counts.get(p, 0) + 1

        return render_template(
            "status.html",
            daemon_running=daemon_running,
            daemon_pid=daemon_pid,
            project_count=len(projects),
            request_count=len(requests),
            status_counts=status_counts,
            phase_counts=phase_counts,
        )
