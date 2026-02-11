"""Flask application for BentWookie V2 web UI."""

import json
import re
import time
from collections.abc import Generator

import markdown as md
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from markupsafe import Markup

from ..constants import (
    AGENT_ROLES,
    AGENT_STATUSES,
    AGENT_STATUS_NAMES,
    BUILD_TASK_STATUS_NAMES,
    BUILD_TASK_STATUSES,
    BUILD_TASK_TYPE_NAMES,
    BUILD_TASK_TYPES,
    COMPONENT_LEVELS,
    COMPONENT_STATUSES,
    COMPONENT_STATUS_NAMES,
    DEFAULT_PRIORITY,
    INTERVIEW_STATUSES,
    INTERVIEW_TYPE_NAMES,
    INTERVIEW_TYPES,
    LEVEL_NAMES,
    MESSAGE_TYPES,
    NEXT_PHASE,
    PHASE_NAMES,
    PHASES,
    ROLE_NAMES,
    VALID_MODELS,
    generate_agent_name,
)
from ..db import (
    count_agents_by_role,
    count_pending_messages,
    create_component,
    create_interview,
    create_interview_message,
    create_message,
    create_project,
    create_system_log,
    delete_project,
    get_build_progress,
    get_component,
    get_component_ancestors,
    get_component_children,
    get_component_tree,
    get_component_with_stats,
    get_connections_for_component,
    get_daemon_state,
    get_dashboard_stats,
    get_dependencies,
    get_dependency_graph,
    get_document,
    get_interview,
    get_interview_messages,
    update_interview,
    get_project,
    get_project_stats,
    init_db,
    list_agents,
    list_agent_settings,
    list_build_tasks,
    list_components,
    list_documents,
    list_interviews,
    list_messages,
    list_projects,
    list_test_specs,
    update_agent,
    update_project,
)

def render_markdown(text: str) -> str:
    """Convert markdown text to HTML.

    Strips javascript: URLs for basic XSS prevention.
    """
    if not text:
        return ""

    html = md.markdown(
        text,
        extensions=["fenced_code", "tables"],
    )

    # Strip javascript: URLs
    html = re.sub(
        r'href\s*=\s*["\']javascript:[^"\']*["\']',
        'href="#"',
        html,
        flags=re.IGNORECASE,
    )
    return html


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    app.secret_key = "bentwookie-secret-key-change-in-production"

    init_db()
    register_routes(app)

    @app.context_processor
    def inject_constants():
        return {
            "PHASE_NAMES": PHASE_NAMES,
            "PHASES": PHASES,
            "NEXT_PHASE": NEXT_PHASE,
            "COMPONENT_LEVELS": COMPONENT_LEVELS,
            "LEVEL_NAMES": LEVEL_NAMES,
            "AGENT_ROLES": AGENT_ROLES,
            "ROLE_NAMES": ROLE_NAMES,
            "AGENT_STATUSES": AGENT_STATUSES,
            "AGENT_STATUS_NAMES": AGENT_STATUS_NAMES,
            "COMPONENT_STATUSES": COMPONENT_STATUSES,
            "COMPONENT_STATUS_NAMES": COMPONENT_STATUS_NAMES,
            "BUILD_TASK_STATUSES": BUILD_TASK_STATUSES,
            "BUILD_TASK_STATUS_NAMES": BUILD_TASK_STATUS_NAMES,
            "BUILD_TASK_TYPES": BUILD_TASK_TYPES,
            "BUILD_TASK_TYPE_NAMES": BUILD_TASK_TYPE_NAMES,
            "INTERVIEW_TYPES": INTERVIEW_TYPES,
            "INTERVIEW_TYPE_NAMES": INTERVIEW_TYPE_NAMES,
            "INTERVIEW_STATUSES": INTERVIEW_STATUSES,
            "MESSAGE_TYPES": MESSAGE_TYPES,
            "VALID_MODELS": VALID_MODELS,
            "DEFAULT_PRIORITY": DEFAULT_PRIORITY,
        }

    @app.context_processor
    def inject_agent_counts():
        counts = count_agents_by_role()
        return {
            "agent_role_counts": counts,
        }

    @app.template_filter("markdown")
    def markdown_filter(text: str) -> Markup:
        return Markup(render_markdown(text))

    return app


def register_routes(app: Flask) -> None:
    """Register all routes for the application."""

    # =========================================================================
    # Health Check
    # =========================================================================

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "bentwookie", "version": "0.4.2"})

    # =========================================================================
    # Workspace (Primary Work Screen)
    # =========================================================================

    @app.route("/workspace")
    @app.route("/workspace/<int:prjid>")
    def workspace(prjid: int | None = None):
        projects = list_projects()
        if not projects:
            flash("No projects yet. Create one first.", "info")
            return redirect(url_for("project_new"))

        if prjid is None:
            prjid = projects[0]["prjid"]

        current_project = get_project(prjid)
        if not current_project:
            flash("Project not found", "error")
            return redirect(url_for("projects_list"))

        # Build nested hierarchy: services -> components -> functions
        all_components = list_components(prjid=prjid)
        services = _build_hierarchy_tree(all_components, prjid=prjid)

        # Project-level stats
        stats = get_project_stats(prjid)
        total = stats["total_components"]
        built = stats["component_counts"].get("built", 0) + stats["component_counts"].get("tested", 0)
        stats["progress_pct"] = int(built / total * 100) if total else 0

        # Count by level
        level_counts: dict[str, int] = {}
        for c in all_components:
            lv = c.get("cmplevel", "unknown")
            level_counts[lv] = level_counts.get(lv, 0) + 1
        stats["component_counts"].update(level_counts)

        return render_template(
            "workspace.html",
            page="workspace",
            projects=projects,
            current_project=current_project,
            services=services,
            project_stats=stats,
        )

    # =========================================================================
    # Settings
    # =========================================================================

    @app.route("/settings")
    def settings_page():
        from ..settings import load_settings

        settings = load_settings()
        return render_template(
            "settings.html",
            page="settings",
            settings=settings,
        )

    # =========================================================================
    # Dashboard
    # =========================================================================

    @app.route("/")
    def index():
        stats = get_dashboard_stats()
        projects = list_projects()
        agents = list_agents()
        daemon_state = get_daemon_state()
        urgent = list_messages(msgtype="urgent", status="queued", limit=5)

        # Enrich projects with counts
        for p in projects:
            cmps = list_components(prjid=p["prjid"])
            p["component_count"] = len(cmps)
            p_agents = [a for a in agents if a["prjid"] == p["prjid"]]
            p["agent_count"] = len(p_agents)

        return render_template(
            "dashboard.html",
            page="dashboard",
            stats=stats,
            projects=projects,
            agents=[a for a in agents if a["agtstatus"] not in ("terminated",)],
            urgent_messages=urgent,
            daemon_state=daemon_state,
        )

    # =========================================================================
    # Projects
    # =========================================================================

    @app.route("/projects")
    def projects_list():
        phase = request.args.get("phase")
        search = request.args.get("search")

        projects = list_projects(phase=phase)

        if search:
            projects = [p for p in projects if search.lower() in p["prjname"].lower()]

        for p in projects:
            cmps = list_components(prjid=p["prjid"])
            p["component_count"] = len(cmps)
            total = len(cmps)
            built = sum(1 for c in cmps if c["cmpstatus"] in ("built", "tested"))
            p["progress"] = int(built / total * 100) if total else 0

        return render_template(
            "projects.html",
            page="projects",
            projects=projects,
            filter_phase=phase,
            filter_search=search,
        )

    @app.route("/projects/new", methods=["GET", "POST"])
    def project_new():
        if request.method == "POST":
            try:
                prjid = create_project(
                    prjname=request.form["name"],
                    prjcodedir=request.form.get("codedir") or None,
                )
                # Auto-create business_owner interview and redirect
                itvid = create_interview(prjid, "business_owner")
                flash(f"Project created (ID: {prjid})", "success")
                return redirect(url_for("interview_session", itvid=itvid))
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    flash("A project with that name already exists", "error")
                else:
                    flash(f"Error creating project: {e}", "error")

        return render_template("project_form.html", page="projects", project=None)

    @app.route("/projects/<int:prjid>/edit", methods=["GET", "POST"])
    def project_edit(prjid: int):
        project = get_project(prjid)
        if not project:
            flash("Project not found", "error")
            return redirect(url_for("projects_list"))

        if request.method == "POST":
            try:
                priority = request.form.get("priority")
                update_project(
                    prjid=prjid,
                    prjname=request.form["name"],
                    prjdesc=request.form.get("desc") or None,
                    prjcodedir=request.form.get("codedir") or None,
                    prjpriority=int(priority) if priority else None,
                )
                flash("Project updated", "success")
                return redirect(url_for("project_view", prjid=prjid))
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    flash("A project with that name already exists", "error")
                else:
                    flash(f"Error updating project: {e}", "error")

        return render_template("project_form.html", page="projects", project=project)

    @app.route("/projects/<int:prjid>")
    def project_view(prjid: int):
        project = get_project(prjid)
        if not project:
            flash("Project not found", "error")
            return redirect(url_for("projects_list"))

        components = get_component_tree(prjid)
        graph = get_dependency_graph(prjid)
        test_specs = list_test_specs(prjid=prjid)
        documents = list_documents(prjid=prjid)

        return render_template(
            "project_view.html",
            page="projects",
            project=project,
            components=components,
            components_json=json.dumps(components),
            graph_json=json.dumps(graph),
            test_specs=test_specs,
            documents=documents,
        )

    @app.route("/projects/<int:prjid>/delete", methods=["POST"])
    def project_delete_route(prjid: int):
        project = get_project(prjid)
        if not project:
            flash("Project not found", "error")
            return redirect(url_for("projects_list"))

        delete_project(prjid)
        flash(f"Project '{project['prjname']}' deleted", "success")
        return redirect(url_for("projects_list"))

    # =========================================================================
    # Components
    # =========================================================================

    @app.route("/components/<int:cmpid>")
    def component_view(cmpid: int):
        component = get_component(cmpid)
        if not component:
            flash("Component not found", "error")
            return redirect(url_for("projects_list"))

        ancestors = get_component_ancestors(cmpid)
        children = get_component_children(cmpid)
        test_specs = list_test_specs(cmpid=cmpid)
        connections = get_connections_for_component(cmpid)
        dependencies = get_dependencies(cmpid)

        return render_template(
            "component_view.html",
            page="projects",
            component=component,
            ancestors=ancestors,
            children=children,
            test_specs=test_specs,
            connections=connections,
            dependencies=dependencies,
        )

    # =========================================================================
    # Interviews
    # =========================================================================

    @app.route("/interviews")
    def interviews_list():
        interviews = list_interviews()
        return render_template(
            "interviews.html",
            page="interviews",
            interviews=interviews,
        )

    @app.route("/interviews/<int:itvid>")
    def interview_session(itvid: int):
        interview = get_interview(itvid)
        if not interview:
            flash("Interview not found", "error")
            return redirect(url_for("interviews_list"))

        messages = get_interview_messages(itvid)

        return render_template(
            "interview_session.html",
            page="interviews",
            interview=interview,
            messages=messages,
        )

    # =========================================================================
    # Agents
    # =========================================================================

    @app.route("/agents")
    def agents_page():
        role_filter = request.args.get("role")
        agents = list_agents(role=role_filter) if role_filter else list_agents()
        # Filter out terminated agents entirely
        agents = [a for a in agents if a.get("agtstatus") != "terminated"]
        pending = count_pending_messages()
        projects = list_projects()
        messages = list_messages(limit=50)

        # Group agents by role for tree view
        agents_by_role: dict[str, list[dict]] = {}
        for role in AGENT_ROLES:
            agents_by_role[role] = []
        for agent in agents:
            role = agent.get("agtrole", "coding_agent")
            if role not in agents_by_role:
                agents_by_role[role] = []
            agents_by_role[role].append(agent)

        return render_template(
            "agents.html",
            page="agents",
            agents=agents,
            agents_by_role=agents_by_role,
            pending_messages=pending,
            filter_role=role_filter,
            projects=projects,
            messages=messages,
        )

    # =========================================================================
    # Build Progress
    # =========================================================================

    @app.route("/build")
    def build_page():
        filter_project = request.args.get("project", type=int)
        projects = list_projects()

        progress = {"total": 0, "complete": 0, "in_progress": 0, "pending": 0, "blocked": 0, "error": 0}
        build_tasks = []
        graph = {"nodes": [], "edges": []}

        if filter_project:
            progress = get_build_progress(filter_project)
            build_tasks = list_build_tasks(prjid=filter_project)
            graph = get_dependency_graph(filter_project)
        elif projects:
            # Aggregate across all projects
            all_tasks = list_build_tasks()
            build_tasks = all_tasks
            for p in projects:
                p_progress = get_build_progress(p["prjid"])
                for key in ("total", "complete", "in_progress", "pending", "blocked", "error"):
                    progress[key] += p_progress.get(key, 0)

            if len(projects) == 1:
                graph = get_dependency_graph(projects[0]["prjid"])

        return render_template(
            "build_progress.html",
            page="build",
            projects=projects,
            filter_project=filter_project,
            progress=progress,
            build_tasks=build_tasks,
            graph_json=json.dumps(graph),
        )

    # =========================================================================
    # Messages
    # =========================================================================

    @app.route("/messages")
    def messages_page():
        filter_type = request.args.get("type")
        filter_status = request.args.get("status")

        msgs = list_messages(
            msgtype=filter_type if filter_type else None,
            status=filter_status if filter_status else None,
        )

        return render_template(
            "messages.html",
            page="messages",
            messages=msgs,
            filter_type=filter_type,
            filter_status=filter_status,
        )

    # =========================================================================
    # System
    # =========================================================================

    @app.route("/system")
    def system_page():
        from ..settings import load_settings

        daemon_state = get_daemon_state()
        settings = load_settings()
        stats = get_dashboard_stats()

        return render_template(
            "system.html",
            page="system",
            daemon_state=daemon_state,
            settings=settings,
            project_count=stats["projects"],
            agent_counts=stats["agent_counts"],
            pending_messages=stats["pending_messages"],
        )

    # =========================================================================
    # Document Viewer
    # =========================================================================

    @app.route("/docs/<int:doc_id>")
    def view_document(doc_id: int):
        from pathlib import Path

        doc = get_document(doc_id)
        if not doc:
            flash("Document not found", "error")
            return redirect(url_for("projects_list"))

        doc_path = Path(doc["docpath"])
        content = ""
        error = None

        if doc_path.exists():
            try:
                content = doc_path.read_text(encoding="utf-8")
            except Exception as e:
                error = f"Error reading file: {e}"
        else:
            error = f"File not found: {doc_path}"

        return render_template(
            "document_view.html",
            page="projects",
            doc=doc,
            content=content,
            error=error,
        )

    # =========================================================================
    # API: SSE Events
    # =========================================================================

    @app.route("/api/events")
    def api_events():
        def event_stream() -> Generator[str, None, None]:
            while True:
                # Emit stats_update with agent role counts
                role_counts = count_agents_by_role()
                agents = list_agents()
                active = sum(1 for a in agents if a.get("agtstatus") == "working")
                idle = sum(1 for a in agents if a.get("agtstatus") == "idle")
                error = sum(1 for a in agents if a.get("agtstatus") == "error")
                pending = count_pending_messages()

                yield f"event: stats_update\ndata: {json.dumps({'type': 'stats_update', 'role_counts': role_counts, 'active_agents': active, 'idle_agents': idle, 'error_agents': error, 'pending_messages': pending})}\n\n"
                time.sleep(15)

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # =========================================================================
    # API: Interviews
    # =========================================================================

    @app.route("/api/interviews", methods=["GET"])
    def api_interviews_list():
        interviews = list_interviews()
        return jsonify(interviews)

    @app.route("/api/interviews", methods=["POST"])
    def api_interviews_create():
        data = request.get_json()
        if not data or "prjid" not in data or "itvtype" not in data:
            return jsonify({"error": "prjid and itvtype required"}), 400

        # Gate: EA interview requires a completed BA interview first
        if data["itvtype"] == "enterprise_architect":
            existing = list_interviews(prjid=data["prjid"])
            ba_complete = any(
                i["itvtype"] == "business_owner" and i["itvstatus"] == "complete"
                for i in existing
            )
            if not ba_complete:
                return jsonify({
                    "error": "Business Owner interview must be completed before starting Enterprise Architect interview"
                }), 400

        itvid = create_interview(data["prjid"], data["itvtype"])
        return jsonify({"itvid": itvid}), 201

    @app.route("/api/interviews/<int:itvid>")
    def api_interview_get(itvid: int):
        interview = get_interview(itvid)
        if not interview:
            return jsonify({"error": "Not found"}), 404

        messages = get_interview_messages(itvid)
        return jsonify({"interview": interview, "messages": messages})

    @app.route("/api/interviews/<int:itvid>/message", methods=["POST"])
    def api_interview_message(itvid: int):
        interview = get_interview(itvid)
        if not interview:
            return jsonify({"error": "Not found"}), 404

        data = request.get_json()
        if not data or "content" not in data:
            return jsonify({"error": "content required"}), 400

        # Save user message
        imsgid = create_interview_message(itvid, "user", data["content"])

        # Update interview status to active if pending
        if interview.get("itvstatus") == "pending":
            update_interview(itvid, itvstatus="active")

        # Generate AI response
        ai_response = _generate_interview_response(interview, data["content"])
        ai_imsgid = create_interview_message(itvid, "agent", ai_response)

        return jsonify({
            "imsgid": imsgid,
            "response": {
                "imsgid": ai_imsgid,
                "content": ai_response,
                "sender": "agent",
            },
        }), 201

    @app.route("/api/interviews/<int:itvid>/complete", methods=["POST"])
    def api_interview_complete(itvid: int):
        interview = get_interview(itvid)
        if not interview:
            return jsonify({"error": "Not found"}), 404
        if interview.get("itvstatus") != "active":
            return jsonify({"error": "Interview is not active"}), 400

        # Ask AI to produce a summary
        summary_prompt = (
            "Please summarize our entire conversation into a structured summary "
            "of all decisions and requirements discussed. Use clear headings and "
            "bullet points."
        )
        summary = _generate_interview_response(interview, summary_prompt)

        # Save summary as final message and update status
        create_interview_message(itvid, "agent", summary)
        update_interview(itvid, itvstatus="complete", itvsummary=summary)

        # Check if both BA and EA are done for this project
        prjid = interview["prjid"]
        all_interviews = list_interviews(prjid=prjid)
        ba_done = any(
            i["itvtype"] == "business_owner" and i["itvstatus"] == "complete"
            for i in all_interviews
        )
        ea_done = any(
            i["itvtype"] == "enterprise_architect" and i["itvstatus"] == "complete"
            for i in all_interviews
        )

        phase_advanced = False
        if ba_done and ea_done:
            project = get_project(prjid)
            if project and project.get("prjphase") == "define":
                update_project(prjid, prjphase="design")
                phase_advanced = True

        # Determine next step
        next_step = None
        if not ea_done and interview["itvtype"] == "business_owner":
            next_step = "ea"  # EA interview unlocked
        elif phase_advanced:
            next_step = "design"  # Both done, moving to design

        return jsonify({
            "summary": summary,
            "next_step": next_step,
            "phase_advanced": phase_advanced,
        })

    # =========================================================================
    # API: Agents
    # =========================================================================

    @app.route("/api/components/<int:cmpid>")
    def api_component_get(cmpid: int):
        component = get_component_with_stats(cmpid)
        if not component:
            return jsonify({"error": "Not found"}), 404
        return jsonify(component)

    @app.route("/api/agents")
    def api_agents_list():
        agents = list_agents()
        return jsonify(agents)

    @app.route("/api/agents/<int:agtid>")
    def api_agent_get(agtid: int):
        from ..db import get_agent
        agent = get_agent(agtid)
        if not agent:
            return jsonify({"error": "Not found"}), 404
        return jsonify(agent)

    @app.route("/api/agents/<int:agtid>/output")
    def api_agent_output(agtid: int):
        # Output is managed by the agent manager; return placeholder
        return jsonify({"agtid": agtid, "output": ""})

    @app.route("/api/agents/<int:agtid>/message", methods=["POST"])
    def api_agent_message(agtid: int):
        data = request.get_json()
        if not data or "body" not in data:
            return jsonify({"error": "body required"}), 400

        msgid = create_message(
            to_agtid=agtid,
            msgbody=data["body"],
            msgtype=data.get("type", "normal"),
        )
        return jsonify({"msgid": msgid}), 201

    @app.route("/api/agents/pause-all", methods=["POST"])
    def api_agents_pause_all():
        agents = list_agents(status="working")
        for a in agents:
            update_agent(a["agtid"], agtstatus="waiting")
        return jsonify({"status": "ok", "paused": len(agents)})

    @app.route("/api/agents/resume-all", methods=["POST"])
    def api_agents_resume_all():
        agents = list_agents(status="waiting")
        for a in agents:
            update_agent(a["agtid"], agtstatus="working")
        return jsonify({"status": "ok", "resumed": len(agents)})

    # =========================================================================
    # API: Build Progress
    # =========================================================================

    @app.route("/api/projects/<int:prjid>")
    def api_project_detail(prjid: int):
        project = get_project(prjid)
        if not project:
            return jsonify({"error": "Not found"}), 404
        stats = get_project_stats(prjid)
        total = stats["total_components"]
        built = stats["component_counts"].get("built", 0) + stats["component_counts"].get("tested", 0)
        stats["progress_pct"] = int(built / total * 100) if total else 0
        # Count by level
        all_components = list_components(prjid=prjid)
        level_counts: dict[str, int] = {}
        for c in all_components:
            lv = c.get("cmplevel", "unknown")
            level_counts[lv] = level_counts.get(lv, 0) + 1
        stats["component_counts"].update(level_counts)
        return jsonify({"project": project, "stats": stats})

    @app.route("/api/projects/<int:prjid>/hierarchy")
    def api_project_hierarchy(prjid: int):
        tree = get_component_tree(prjid)
        return jsonify(tree)

    @app.route("/api/projects/<int:prjid>/dependency-graph")
    def api_project_dependency_graph(prjid: int):
        graph = get_dependency_graph(prjid)
        return jsonify(graph)

    @app.route("/api/projects/<int:prjid>/build-progress")
    def api_project_build_progress(prjid: int):
        progress = get_build_progress(prjid)
        return jsonify(progress)

    # =========================================================================
    # API: Messages
    # =========================================================================

    @app.route("/api/messages")
    def api_messages_list():
        msgtype = request.args.get("type")
        status = request.args.get("status")
        limit = request.args.get("limit", 100, type=int)
        msgs = list_messages(msgtype=msgtype, status=status, limit=limit)
        return jsonify(msgs)

    # =========================================================================
    # API: Daemon Control
    # =========================================================================

    @app.route("/api/daemon/pause", methods=["POST"])
    def api_daemon_pause():
        from ..db import set_daemon_state
        state = get_daemon_state()
        if state and state.get("pid"):
            set_daemon_state(pid=state["pid"], dsstatus="paused")
        return jsonify({"status": "ok"})

    @app.route("/api/daemon/resume", methods=["POST"])
    def api_daemon_resume():
        from ..db import set_daemon_state
        state = get_daemon_state()
        if state and state.get("pid"):
            set_daemon_state(pid=state["pid"], dsstatus="running")
        return jsonify({"status": "ok"})

    # =========================================================================
    # API: Settings
    # =========================================================================

    @app.route("/api/settings", methods=["GET", "POST"])
    def api_settings_update():
        from ..settings import load_settings, save_settings

        if request.method == "POST":
            data = request.get_json() if request.is_json else request.form
            settings = load_settings()

            for key in ("max_concurrent_agents", "agent_timeout", "poll_interval"):
                if key in data:
                    settings[key] = int(data[key])

            if "model" in data:
                settings["model"] = data["model"]

            save_settings(settings)

            if request.is_json:
                return jsonify({"status": "ok", **settings})
            flash("Settings saved", "success")
            return redirect(url_for("system_page"))

        return jsonify(load_settings())

    @app.route("/api/status")
    def api_status():
        stats = get_dashboard_stats()
        daemon_state = get_daemon_state()
        return jsonify({
            "daemon": daemon_state,
            **stats,
        })

    # =========================================================================
    # API: Browse Directories (folder picker)
    # =========================================================================

    @app.route("/api/browse-dirs")
    def api_browse_dirs():
        from pathlib import Path as P

        path_str = request.args.get("path", "")
        if not path_str:
            path_str = str(P.home())

        target = P(path_str).resolve()
        if not target.is_dir():
            target = target.parent
        if not target.exists():
            target = P.home()

        dirs = []
        try:
            for entry in sorted(target.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    dirs.append(entry.name)
        except PermissionError:
            pass

        parent = str(target.parent) if target != target.parent else None

        return jsonify({
            "path": str(target),
            "parent": parent,
            "dirs": dirs,
        })

    # =========================================================================
    # API: Create Directory
    # =========================================================================

    @app.route("/api/create-dir", methods=["POST"])
    def api_create_dir():
        from pathlib import Path as P

        data = request.get_json()
        if not data or "parent" not in data or "name" not in data:
            return jsonify({"error": "parent and name required"}), 400

        parent_str = data["parent"].strip()
        name = data["name"].strip()

        if not parent_str or not name:
            return jsonify({"error": "parent and name must not be empty"}), 400

        # Sanitize name: no path separators or special chars
        if "/" in name or "\\" in name or name.startswith("."):
            return jsonify({"error": "Invalid folder name"}), 400

        parent = P(parent_str).resolve()
        if not parent.is_dir():
            return jsonify({"error": "Parent directory does not exist"}), 400

        new_dir = parent / name
        if new_dir.exists():
            return jsonify({"error": "Folder already exists"}), 400

        try:
            new_dir.mkdir(parents=False)
        except PermissionError:
            return jsonify({"error": "Permission denied"}), 403
        except OSError as e:
            return jsonify({"error": str(e)}), 500

        return jsonify({"path": str(new_dir)}), 201

    # =========================================================================
    # API: Add Service to Workspace
    # =========================================================================

    @app.route("/workspace/<int:prjid>/add-service", methods=["POST"])
    def workspace_add_service(prjid: int):
        project = get_project(prjid)
        if not project:
            flash("Project not found", "error")
            return redirect(url_for("workspace"))

        name = request.form.get("name", "").strip()
        desc = request.form.get("desc", "").strip() or None

        if not name:
            flash("Service name is required", "error")
            return redirect(url_for("workspace", prjid=prjid))

        create_component(
            prjid=prjid,
            cmpname=name,
            cmplevel="service",
            cmpdesc=desc,
        )
        flash(f"Service '{name}' created", "success")
        return redirect(url_for("workspace", prjid=prjid))

    @app.route("/api/projects/<int:prjid>/services", methods=["POST"])
    def api_add_service(prjid: int):
        project = get_project(prjid)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        data = request.get_json()
        if not data or not data.get("name"):
            return jsonify({"error": "name required"}), 400

        cmpid = create_component(
            prjid=prjid,
            cmpname=data["name"],
            cmplevel="service",
            cmpdesc=data.get("desc"),
        )
        return jsonify({"cmpid": cmpid}), 201

    # =========================================================================
    # API: Tech Stack Catalog
    # =========================================================================

    @app.route("/api/techstack/search")
    def api_techstack_search():
        from ..db import search_techstack_catalog

        query = request.args.get("q", "").strip()
        limit = int(request.args.get("limit", 50))
        results = search_techstack_catalog(query=query, limit=limit)
        return jsonify(results)

    @app.route("/api/techstack", methods=["POST"])
    def api_techstack_add():
        from ..db import add_techstack_entry

        data = request.get_json()
        if not data or not data.get("key"):
            return jsonify({"error": "key is required"}), 400

        try:
            tscat_id = add_techstack_entry(
                tscat_key=data["key"].strip(),
                tscat_owner=data.get("owner", "").strip() or None,
                tscat_desc=data.get("desc", "").strip() or None,
                tscat_notes=data.get("notes", "").strip() or None,
            )
            return jsonify({"tscat_id": tscat_id}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/techstack/<int:tscat_id>", methods=["DELETE"])
    def api_techstack_delete(tscat_id: int):
        from ..db import delete_techstack_entry

        delete_techstack_entry(tscat_id)
        return jsonify({"ok": True})

    # =========================================================================
    # API: Agent Spawn / Terminate
    # =========================================================================

    @app.route("/api/agents/spawn", methods=["POST"])
    def api_agents_spawn():
        from ..db import create_agent

        data = request.get_json()
        if not data or "role" not in data:
            return jsonify({"error": "role required"}), 400

        role = data["role"]
        if role not in AGENT_ROLES:
            return jsonify({"error": f"Invalid role: {role}"}), 400

        # prjid is optional; default to first project
        prjid = data.get("prjid")
        if prjid:
            prjid = int(prjid)
        else:
            projects = list_projects()
            if not projects:
                return jsonify({"error": "No projects exist. Create a project first."}), 400
            prjid = projects[0]["prjid"]

        # Generate a fun, unique agent name
        existing = list_agents(role=role)
        existing_names = [a.get("agtname", "") for a in existing]
        agent_name = generate_agent_name(role, existing_names)
        agtid = create_agent(
            prjid=prjid,
            agtrole=role,
            agtname=agent_name,
            agtmodel=data.get("model"),
        )
        create_system_log(f"Agent spawned: {agent_name} ({role})", related_agtid=agtid)
        return jsonify({"agtid": agtid, "role": role}), 201

    @app.route("/api/agents/<int:agtid>/rename", methods=["POST"])
    def api_agent_rename(agtid: int):
        from ..db import get_agent

        agent = get_agent(agtid)
        if not agent:
            return jsonify({"error": "Agent not found"}), 404

        data = request.get_json()
        if not data or not data.get("name", "").strip():
            return jsonify({"error": "name required"}), 400

        new_name = data["name"].strip()
        update_agent(agtid, agtname=new_name)
        return jsonify({"status": "ok", "agtid": agtid, "agtname": new_name})

    @app.route("/api/agents/<int:agtid>/terminate", methods=["POST"])
    def api_agent_terminate(agtid: int):
        from ..db import get_agent

        agent = get_agent(agtid)
        if not agent:
            return jsonify({"error": "Agent not found"}), 404

        update_agent(agtid, agtstatus="terminated")
        agent_name = agent.get("agtname") or f"Agent #{agtid}"
        create_system_log(f"Agent terminated: {agent_name} ({agent.get('agtrole', 'unknown')})", related_agtid=agtid)
        return jsonify({"status": "ok", "agtid": agtid})

    # =========================================================================
    # API: EA Chat
    # =========================================================================

    @app.route("/api/ea-chat/<int:prjid>")
    def api_ea_chat_get(prjid: int):
        """Get or create an EA interview for persistent EA chat."""
        interviews = list_interviews(prjid=prjid)
        ea_interview = None
        for itv in interviews:
            if itv.get("itvtype") == "enterprise_architect":
                ea_interview = itv
                break

        if ea_interview is None:
            itvid = create_interview(prjid, "enterprise_architect")
            ea_interview = get_interview(itvid)

        messages = get_interview_messages(ea_interview["itvid"])
        return jsonify({"interview": ea_interview, "messages": messages})

    @app.route("/api/ea-chat/<int:prjid>/message", methods=["POST"])
    def api_ea_chat_message(prjid: int):
        """Send a message to the EA chat."""
        interviews = list_interviews(prjid=prjid)
        ea_interview = None
        for itv in interviews:
            if itv.get("itvtype") == "enterprise_architect":
                ea_interview = itv
                break

        if ea_interview is None:
            return jsonify({"error": "No EA interview found"}), 404

        data = request.get_json()
        if not data or "content" not in data:
            return jsonify({"error": "content required"}), 400

        imsgid = create_interview_message(
            ea_interview["itvid"], "user", data["content"]
        )
        return jsonify({"imsgid": imsgid}), 201

    # =========================================================================
    # API: Agent Output Stream (SSE)
    # =========================================================================

    @app.route("/api/agents/<int:agtid>/stream")
    def api_agent_stream(agtid: int):
        from ..db import get_agent_output

        last_aoid = request.args.get("since", 0, type=int)

        def output_stream() -> Generator[str, None, None]:
            nonlocal last_aoid
            while True:
                outputs = get_agent_output(agtid, since_aoid=last_aoid or None)
                for out in outputs:
                    last_aoid = out["aoid"]
                    yield f"data: {json.dumps({'type': 'output', 'aoid': out['aoid'], 'content': out['aocontent']})}\n\n"
                if not outputs:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                time.sleep(2)

        return Response(
            output_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # =========================================================================
    # API: Agent Settings (Hierarchical)
    # =========================================================================

    @app.route("/api/agent-settings", methods=["GET", "POST"])
    def api_agent_settings():
        from ..db import set_agent_setting, delete_agent_setting

        if request.method == "POST":
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400

            scope = data.get("scope", "agent_type")
            scope_key = data.get("scope_key")
            settings = data.get("settings", {})

            if not scope_key:
                return jsonify({"error": "scope_key required"}), 400

            for key, value in settings.items():
                if value is None or value == "":
                    delete_agent_setting(scope, scope_key, key)
                else:
                    set_agent_setting(scope, scope_key, key, str(value))

            return jsonify({"status": "ok"})

        # GET: list all
        scope = request.args.get("scope")
        scope_key = request.args.get("scope_key")
        settings_list = list_agent_settings(scope=scope, scope_key=scope_key)
        return jsonify(settings_list)

    # =========================================================================
    # API: Work Queue
    # =========================================================================

    @app.route("/api/work-queue", methods=["POST"])
    def api_work_queue_add():
        from ..db import create_build_task

        data = request.get_json()
        if not data or "cmpid" not in data:
            return jsonify({"error": "cmpid required"}), 400

        btid = create_build_task(
            cmpid=int(data["cmpid"]),
            bttype=data.get("bttype", "implement"),
            btprompt=data.get("btprompt"),
        )
        return jsonify({"btid": btid}), 201

    # =========================================================================
    # API: Task Queue
    # =========================================================================

    @app.route("/api/task-queue", methods=["GET"])
    def api_task_queue_list():
        from ..db import list_tasks

        prjid = request.args.get("prjid", type=int)
        status = request.args.get("status")
        limit = request.args.get("limit", 100, type=int)
        tasks = list_tasks(prjid=prjid, status=status, limit=limit)
        return jsonify(tasks)

    @app.route("/api/task-queue", methods=["POST"])
    def api_task_queue_enqueue():
        from ..db import enqueue_task

        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        prjid = data.get("prjid")
        agent_type = data.get("agent_type")
        instructions = data.get("instructions")

        if not prjid or not agent_type or not instructions:
            return jsonify({"error": "prjid, agent_type, and instructions required"}), 400

        tqid = enqueue_task(
            prjid=int(prjid),
            tqagent_type=agent_type,
            tqinstructions=instructions,
            tqauthor=data.get("author", "user"),
            tqrequest_type=data.get("request_type", "task"),
            tqworkflow_step=data.get("workflow_step"),
            tqprevious_work=data.get("previous_work"),
            tqcmpid=data.get("cmpid"),
            tqpriority=int(data.get("priority", 5)),
            tqmax_retries=int(data.get("max_retries", 3)),
            tqstart_time=data.get("start_time"),
            tqexpire_time=data.get("expire_time"),
            tqagent_name=data.get("agent_name"),
            tqcollab_chain_id=data.get("collab_chain_id"),
            tqcollab_turn=data.get("collab_turn"),
        )
        return jsonify({"tqid": tqid}), 201

    @app.route("/api/task-queue/<int:tqid>", methods=["GET"])
    def api_task_queue_get(tqid: int):
        from ..db import get_task

        task = get_task(tqid)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(task)

    @app.route("/api/task-queue/<int:tqid>/cancel", methods=["POST"])
    def api_task_queue_cancel(tqid: int):
        from ..db import get_task, update_task

        task = get_task(tqid)
        if not task:
            return jsonify({"error": "Task not found"}), 404

        if task["tqstatus"] in ("complete", "failed", "expired", "cancelled"):
            return jsonify({"error": f"Cannot cancel task in status '{task['tqstatus']}'"}), 400

        update_task(tqid, tqstatus="cancelled")
        return jsonify({"status": "ok", "tqid": tqid})

    @app.route("/api/task-queue/stats/<int:prjid>", methods=["GET"])
    def api_task_queue_stats(prjid: int):
        from ..db import get_task_queue_stats

        stats = get_task_queue_stats(prjid)
        return jsonify(stats)

    @app.route("/api/projects/<int:prjid>/progress", methods=["GET"])
    def api_project_progress(prjid: int):
        from ..db import calculate_project_progress

        progress = calculate_project_progress(prjid)
        return jsonify(progress)

    @app.route("/api/projects/<int:prjid>/performance", methods=["GET"])
    def api_project_performance(prjid: int):
        from ..db import get_task_queue_stats

        stats = get_task_queue_stats(prjid)
        return jsonify({
            "avg_duration_secs": stats.get("avg_duration_secs", 0),
            "total_tasks": stats.get("total", 0),
            "completed_tasks": stats.get("complete", 0),
            "failed_tasks": stats.get("failed", 0),
        })



def _generate_interview_response(interview: dict, user_message: str) -> str:
    """Generate an AI response for an interview session via Claude CLI."""
    try:
        from ..agents.interview import generate_response
        return generate_response(interview, user_message)
    except FileNotFoundError:
        return (
            "**Claude CLI not found.** Install Claude Code "
            "(`npm install -g @anthropic-ai/claude-code`) and try again."
        )
    except RuntimeError as exc:
        return f"**AI response error:** {exc}"
    except Exception as exc:
        import logging
        logging.getLogger("bentwookie.web").error(
            f"Interview AI response failed: {exc}", exc_info=True
        )
        return "Unexpected error generating response. Check server logs."


def _build_hierarchy_tree(components: list[dict], prjid: int) -> list[dict]:
    """Build a nested tree from a flat list of components.

    Returns a list of service-level dicts, each with a 'children' list
    of component-level dicts, each with a 'children' list of function-level dicts.
    Each node is enriched with agent counts and test status.
    """
    by_id: dict[int, dict] = {}
    for c in components:
        c["children"] = []
        c["progress"] = 0
        c["test_status"] = "none"
        c["coding_agents"] = 0
        c["orchestrator_agents"] = 0
        by_id[c["cmpid"]] = c

    roots: list[dict] = []
    for c in components:
        pid = c.get("parent_id")
        if pid and pid in by_id:
            by_id[pid]["children"].append(c)
        else:
            roots.append(c)

    # Enrich with agent counts (agents assigned to each component)
    agents = list_agents(prjid=prjid)
    for agt in agents:
        cmpid = agt.get("agtcmpid")
        if cmpid and cmpid in by_id:
            role = agt.get("agtrole", "")
            if role in ("coding_agent", "testing_agent"):
                by_id[cmpid]["coding_agents"] += 1
            elif role in ("service_engineer", "enterprise_architect", "business_architect"):
                by_id[cmpid]["orchestrator_agents"] += 1

    # Enrich with test status from test_spec + test_result
    test_specs = list_test_specs(prjid=prjid)
    # Group specs by cmpid and determine status
    specs_by_cmp: dict[int, list[dict]] = {}
    for ts in test_specs:
        specs_by_cmp.setdefault(ts["cmpid"], []).append(ts)

    for cmpid_key, specs in specs_by_cmp.items():
        if cmpid_key not in by_id:
            continue
        # Check if any specs have been tested
        tested = [s for s in specs if s.get("tsstatus") == "passed"]
        failed = [s for s in specs if s.get("tsstatus") == "failed"]
        if len(tested) == len(specs) and len(specs) > 0:
            by_id[cmpid_key]["test_status"] = "pass"
        elif tested or failed:
            by_id[cmpid_key]["test_status"] = "partial"
        else:
            by_id[cmpid_key]["test_status"] = "none"

    # Compute progress for each node with children
    for node in by_id.values():
        kids = node["children"]
        if kids:
            done = sum(1 for k in kids if k["cmpstatus"] in ("built", "tested"))
            node["progress"] = int(done / len(kids) * 100) if kids else 0

    # Propagate child agent counts up to parent nodes
    for node in by_id.values():
        kids = node["children"]
        if kids:
            node["coding_agents"] += sum(k.get("coding_agents", 0) for k in kids)
            node["orchestrator_agents"] += sum(k.get("orchestrator_agents", 0) for k in kids)

    # Filter to service-level roots (skip project-level if present)
    services = [r for r in roots if r.get("cmplevel") == "service"]
    if not services:
        services = roots

    return services
