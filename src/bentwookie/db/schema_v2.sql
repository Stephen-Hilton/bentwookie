-- BentWookie V2 Database Schema
-- 16 tables for AI agent swarm orchestration

-- ============================================================================
-- Project table (simplified from V1)
-- ============================================================================
CREATE TABLE IF NOT EXISTS project (
    prjid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjname TEXT NOT NULL UNIQUE,
    prjphase TEXT DEFAULT 'define',
    prjdesc TEXT,
    prjcodedir TEXT,
    prjmodel TEXT,
    prjmaxagents INTEGER DEFAULT 5,
    prjpriority INTEGER DEFAULT 5,
    prjtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Component table (unified 4-level hierarchy via adjacency list)
-- Levels: project, service, component, function
-- ============================================================================
CREATE TABLE IF NOT EXISTS component (
    cmpid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    parent_id INTEGER,
    cmpname TEXT NOT NULL,
    cmplevel TEXT NOT NULL CHECK (cmplevel IN ('project', 'service', 'component', 'function')),
    cmpstatus TEXT DEFAULT 'draft',
    cmpdesc TEXT,
    cmpspec TEXT,
    is_collapsed INTEGER DEFAULT 0,
    cmporder INTEGER DEFAULT 0,
    cmptouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES component(cmpid) ON DELETE CASCADE
);

-- ============================================================================
-- Connection map (peer connections between components at same level)
-- ============================================================================
CREATE TABLE IF NOT EXISTS connection_map (
    conid INTEGER PRIMARY KEY AUTOINCREMENT,
    from_cmpid INTEGER NOT NULL,
    to_cmpid INTEGER NOT NULL,
    condesc TEXT,
    contype TEXT DEFAULT 'data',
    contouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_cmpid) REFERENCES component(cmpid) ON DELETE CASCADE,
    FOREIGN KEY (to_cmpid) REFERENCES component(cmpid) ON DELETE CASCADE
);

-- ============================================================================
-- Dependency (build-order DAG edges)
-- ============================================================================
CREATE TABLE IF NOT EXISTS dependency (
    depid INTEGER PRIMARY KEY AUTOINCREMENT,
    cmpid INTEGER NOT NULL,
    depends_on_cmpid INTEGER NOT NULL,
    deptouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cmpid) REFERENCES component(cmpid) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_cmpid) REFERENCES component(cmpid) ON DELETE CASCADE,
    UNIQUE(cmpid, depends_on_cmpid)
);

-- ============================================================================
-- Agent (agent instances)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent (
    agtid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    agtrole TEXT NOT NULL CHECK (agtrole IN ('business_owner', 'enterprise_architect', 'business_architect', 'service_engineer', 'coding_agent', 'testing_agent')),
    agtstatus TEXT DEFAULT 'idle',
    agtname TEXT,
    agtmodel TEXT,
    agtshellpid INTEGER,
    agtcmpid INTEGER,
    agterror TEXT,
    agtstarted TIMESTAMP,
    agttouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid) ON DELETE CASCADE,
    FOREIGN KEY (agtcmpid) REFERENCES component(cmpid) ON DELETE SET NULL
);

-- ============================================================================
-- Agent message (inter-agent message queue)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_message (
    msgid INTEGER PRIMARY KEY AUTOINCREMENT,
    from_agtid INTEGER,
    to_agtid INTEGER NOT NULL,
    msgtype TEXT DEFAULT 'normal' CHECK (msgtype IN ('normal', 'urgent')),
    msgstatus TEXT DEFAULT 'queued' CHECK (msgstatus IN ('queued', 'delivered', 'read')),
    msgbody TEXT NOT NULL,
    msgtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_agtid) REFERENCES agent(agtid) ON DELETE SET NULL,
    FOREIGN KEY (to_agtid) REFERENCES agent(agtid) ON DELETE CASCADE
);

-- ============================================================================
-- Interview (interview sessions: BO + EA per project)
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview (
    itvid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    itvtype TEXT NOT NULL CHECK (itvtype IN ('business_owner', 'enterprise_architect')),
    itvstatus TEXT DEFAULT 'pending' CHECK (itvstatus IN ('pending', 'active', 'complete', 'error')),
    itvsummary TEXT,
    itvtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid) ON DELETE CASCADE
);

-- ============================================================================
-- Interview message (individual messages within an interview)
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview_message (
    imsgid INTEGER PRIMARY KEY AUTOINCREMENT,
    itvid INTEGER NOT NULL,
    imsgsender TEXT NOT NULL CHECK (imsgsender IN ('user', 'agent')),
    imsgcontent TEXT NOT NULL,
    imsgtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (itvid) REFERENCES interview(itvid) ON DELETE CASCADE
);

-- ============================================================================
-- Test spec (test specifications per component from Phase 3)
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_spec (
    tsid INTEGER PRIMARY KEY AUTOINCREMENT,
    cmpid INTEGER NOT NULL,
    tsname TEXT NOT NULL,
    tsdesc TEXT,
    tstype TEXT DEFAULT 'unit' CHECK (tstype IN ('unit', 'integration', 'e2e')),
    tsstatus TEXT DEFAULT 'draft',
    tstouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cmpid) REFERENCES component(cmpid) ON DELETE CASCADE
);

-- ============================================================================
-- Build task (work items assigned to agents during Phase 4)
-- ============================================================================
CREATE TABLE IF NOT EXISTS build_task (
    btid INTEGER PRIMARY KEY AUTOINCREMENT,
    cmpid INTEGER NOT NULL,
    agtid INTEGER,
    bttype TEXT DEFAULT 'implement' CHECK (bttype IN ('implement', 'assemble', 'integrate', 'test')),
    btstatus TEXT DEFAULT 'pending' CHECK (btstatus IN ('pending', 'blocked', 'assigned', 'in_progress', 'complete', 'error', 'cancelled', 'rework')),
    btprompt TEXT,
    btresult TEXT,
    bterror TEXT,
    bttouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cmpid) REFERENCES component(cmpid) ON DELETE CASCADE,
    FOREIGN KEY (agtid) REFERENCES agent(agtid) ON DELETE SET NULL
);

-- ============================================================================
-- Build plan (design phase plans per component)
-- ============================================================================
CREATE TABLE IF NOT EXISTS build_plan (
    bpid INTEGER PRIMARY KEY AUTOINCREMENT,
    cmpid INTEGER NOT NULL,
    bpcontent TEXT NOT NULL,
    bpstatus TEXT DEFAULT 'draft',
    bptouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cmpid) REFERENCES component(cmpid) ON DELETE CASCADE
);

-- ============================================================================
-- Design amendment (rework protocol log, append-only)
-- ============================================================================
CREATE TABLE IF NOT EXISTS design_amendment (
    daid INTEGER PRIMARY KEY AUTOINCREMENT,
    cmpid INTEGER NOT NULL,
    agtid INTEGER,
    dareason TEXT NOT NULL,
    dachange TEXT NOT NULL,
    datouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cmpid) REFERENCES component(cmpid) ON DELETE CASCADE,
    FOREIGN KEY (agtid) REFERENCES agent(agtid) ON DELETE SET NULL
);

-- ============================================================================
-- Traceability (business goals to component mapping)
-- ============================================================================
CREATE TABLE IF NOT EXISTS traceability (
    trcid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    cmpid INTEGER,
    trcgoal TEXT NOT NULL,
    trcdesc TEXT,
    trctouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid) ON DELETE CASCADE,
    FOREIGN KEY (cmpid) REFERENCES component(cmpid) ON DELETE SET NULL
);

-- ============================================================================
-- Learning (accumulated learnings, enhanced from V1)
-- ============================================================================
CREATE TABLE IF NOT EXISTS learning (
    lrnid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    lrndesc TEXT NOT NULL,
    lrnsource TEXT,
    lrnphase TEXT,
    lrntouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid) ON DELETE CASCADE
);

-- ============================================================================
-- Daemon state (orchestrator singleton status)
-- ============================================================================
CREATE TABLE IF NOT EXISTS daemon_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    pid INTEGER,
    dsstatus TEXT DEFAULT 'stopped',
    dsphase TEXT,
    dsproject_id INTEGER,
    started_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initialize daemon_state with empty row if not exists
INSERT OR IGNORE INTO daemon_state (id) VALUES (1);

-- ============================================================================
-- Document (generated artifacts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS document (
    docid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    cmpid INTEGER,
    docname TEXT NOT NULL,
    docpath TEXT NOT NULL,
    doctype TEXT,
    docphase TEXT,
    docdesc TEXT,
    doctouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid) ON DELETE CASCADE,
    FOREIGN KEY (cmpid) REFERENCES component(cmpid) ON DELETE SET NULL
);

-- ============================================================================
-- Task Queue (central work queue for the orchestrator)
-- ============================================================================
CREATE TABLE IF NOT EXISTS task_queue (
    tqid INTEGER PRIMARY KEY AUTOINCREMENT,
    prjid INTEGER NOT NULL,
    tqauthor TEXT DEFAULT 'system',
    tqstatus TEXT DEFAULT 'pending' CHECK (tqstatus IN ('pending', 'assigned', 'in_progress', 'complete', 'failed', 'expired', 'cancelled')),
    tqsent_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tqstart_time TIMESTAMP,
    tqexpire_time TIMESTAMP,
    tqagent_type TEXT NOT NULL,
    tqagent_name TEXT,
    tqagent_id INTEGER,
    tqrequest_type TEXT DEFAULT 'task' CHECK (tqrequest_type IN ('task', 'collab')),
    tqworkflow_step INTEGER,
    tqprevious_work TEXT,
    tqinstructions TEXT NOT NULL,
    tqcmpid INTEGER,
    tqpriority INTEGER DEFAULT 5,
    tqretry_count INTEGER DEFAULT 0,
    tqmax_retries INTEGER DEFAULT 3,
    tqpickup_time TIMESTAMP,
    tqcomplete_time TIMESTAMP,
    tqduration_secs REAL,
    tqresult TEXT,
    tqerror TEXT,
    tqcollab_chain_id INTEGER,
    tqcollab_turn INTEGER,
    tqtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prjid) REFERENCES project(prjid) ON DELETE CASCADE,
    FOREIGN KEY (tqagent_id) REFERENCES agent(agtid) ON DELETE SET NULL,
    FOREIGN KEY (tqcmpid) REFERENCES component(cmpid) ON DELETE SET NULL
);

-- ============================================================================
-- Test result (test execution results)
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_result (
    trid INTEGER PRIMARY KEY AUTOINCREMENT,
    tsid INTEGER NOT NULL,
    agtid INTEGER,
    trpassed INTEGER DEFAULT 0,
    troutput TEXT,
    trerror TEXT,
    trtouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tsid) REFERENCES test_spec(tsid) ON DELETE CASCADE,
    FOREIGN KEY (agtid) REFERENCES agent(agtid) ON DELETE SET NULL
);

-- ============================================================================
-- Agent output (terminal output chunks for live streaming)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_output (
    aoid INTEGER PRIMARY KEY AUTOINCREMENT,
    agtid INTEGER NOT NULL,
    aocontent TEXT NOT NULL,
    aotouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agtid) REFERENCES agent(agtid) ON DELETE CASCADE
);

-- ============================================================================
-- Agent settings (hierarchical overrides: per-type or per-agent)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_settings (
    asid INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL CHECK (scope IN ('agent_type', 'agent')),
    scope_key TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    astouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scope, scope_key, setting_key)
);

-- ============================================================================
-- Agent context (work context snapshots for context save/restore)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_context (
    acid INTEGER PRIMARY KEY AUTOINCREMENT,
    agtid INTEGER NOT NULL,
    cmpid INTEGER,
    btid INTEGER,
    accontext TEXT NOT NULL,
    acstatus TEXT DEFAULT 'active',
    acscopelevel TEXT,
    acscopeid INTEGER,
    actqid INTEGER,
    actouchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agtid) REFERENCES agent(agtid) ON DELETE CASCADE,
    FOREIGN KEY (cmpid) REFERENCES component(cmpid) ON DELETE SET NULL,
    FOREIGN KEY (btid) REFERENCES build_task(btid) ON DELETE SET NULL,
    FOREIGN KEY (actqid) REFERENCES task_queue(tqid) ON DELETE SET NULL
);

-- ============================================================================
-- Tech Stack Catalog (searchable service templates)
-- ============================================================================
CREATE TABLE IF NOT EXISTS techstack_catalog (
    tscat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tscat_key TEXT NOT NULL UNIQUE,
    tscat_owner TEXT,
    tscat_desc TEXT,
    tscat_notes TEXT,
    tscat_custom INTEGER DEFAULT 0,
    tscat_touchts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_techstack_key ON techstack_catalog(tscat_key);

-- ============================================================================
-- Indexes for common queries
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_component_prjid ON component(prjid);
CREATE INDEX IF NOT EXISTS idx_component_parent ON component(parent_id);
CREATE INDEX IF NOT EXISTS idx_component_level ON component(cmplevel);
CREATE INDEX IF NOT EXISTS idx_component_status ON component(cmpstatus);
CREATE INDEX IF NOT EXISTS idx_dependency_cmpid ON dependency(cmpid);
CREATE INDEX IF NOT EXISTS idx_dependency_depends ON dependency(depends_on_cmpid);
CREATE INDEX IF NOT EXISTS idx_agent_prjid ON agent(prjid);
CREATE INDEX IF NOT EXISTS idx_agent_status ON agent(agtstatus);
CREATE INDEX IF NOT EXISTS idx_agent_message_to ON agent_message(to_agtid);
CREATE INDEX IF NOT EXISTS idx_agent_message_status ON agent_message(msgstatus);
CREATE INDEX IF NOT EXISTS idx_interview_prjid ON interview(prjid);
CREATE INDEX IF NOT EXISTS idx_interview_message_itvid ON interview_message(itvid);
CREATE INDEX IF NOT EXISTS idx_test_spec_cmpid ON test_spec(cmpid);
CREATE INDEX IF NOT EXISTS idx_build_task_cmpid ON build_task(cmpid);
CREATE INDEX IF NOT EXISTS idx_build_task_agtid ON build_task(agtid);
CREATE INDEX IF NOT EXISTS idx_build_task_status ON build_task(btstatus);
CREATE INDEX IF NOT EXISTS idx_build_plan_cmpid ON build_plan(cmpid);
CREATE INDEX IF NOT EXISTS idx_design_amendment_cmpid ON design_amendment(cmpid);
CREATE INDEX IF NOT EXISTS idx_traceability_prjid ON traceability(prjid);
CREATE INDEX IF NOT EXISTS idx_learning_prjid ON learning(prjid);
CREATE INDEX IF NOT EXISTS idx_document_prjid ON document(prjid);
CREATE INDEX IF NOT EXISTS idx_test_result_tsid ON test_result(tsid);
CREATE INDEX IF NOT EXISTS idx_connection_map_from ON connection_map(from_cmpid);
CREATE INDEX IF NOT EXISTS idx_connection_map_to ON connection_map(to_cmpid);
CREATE INDEX IF NOT EXISTS idx_agent_output_agtid ON agent_output(agtid);
CREATE INDEX IF NOT EXISTS idx_agent_output_ts ON agent_output(aotouchts);
CREATE INDEX IF NOT EXISTS idx_agent_settings_scope ON agent_settings(scope, scope_key);
CREATE INDEX IF NOT EXISTS idx_agent_context_agtid ON agent_context(agtid);
CREATE INDEX IF NOT EXISTS idx_agent_context_btid ON agent_context(btid);

-- Task queue indexes
CREATE INDEX IF NOT EXISTS idx_tq_prjid ON task_queue(prjid);
CREATE INDEX IF NOT EXISTS idx_tq_status ON task_queue(tqstatus);
CREATE INDEX IF NOT EXISTS idx_tq_agent_type ON task_queue(tqagent_type);
CREATE INDEX IF NOT EXISTS idx_tq_agent_id ON task_queue(tqagent_id);
CREATE INDEX IF NOT EXISTS idx_tq_start_time ON task_queue(tqstart_time);
CREATE INDEX IF NOT EXISTS idx_tq_priority ON task_queue(tqpriority);
CREATE INDEX IF NOT EXISTS idx_tq_workflow_step ON task_queue(tqworkflow_step);
