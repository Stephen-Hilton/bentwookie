/**
 * BentWookie Agent Monitor
 * Real-time agent card updates, terminal output, detail panel.
 */
class AgentMonitor {
    constructor(options = {}) {
        this.cardsContainer = document.getElementById(options.cardsId || 'agent-cards');
        this.detailPanel = document.getElementById(options.detailId || 'agent-detail');
        this.terminalOutput = document.getElementById(options.terminalId || 'terminal-output');
        this.selectedAgentId = null;
        this.agents = {};
        this.outputBuffers = {};

        this.init();
    }

    init() {
        this.initSSE();

        if (this.cardsContainer) {
            this.cardsContainer.addEventListener('click', (e) => {
                const card = e.target.closest('.agent-card');
                if (card) {
                    this.selectAgent(card.dataset.agtid);
                }
            });
        }
    }

    initSSE() {
        const sse = typeof getSSE === 'function' ? getSSE() : null;
        if (!sse) return;

        sse.on('agent_status', (data) => {
            this.updateAgentCard(data.agtid, data);
        });

        sse.on('agent_output', (data) => {
            this.appendOutput(data.agtid, data.output);
        });

        sse.on('stats_update', (data) => {
            this.updateStats(data);
            this.refreshAgentTree();
        });
    }

    updateAgentCard(agtid, data) {
        this.agents[agtid] = { ...this.agents[agtid], ...data };

        const card = this.cardsContainer?.querySelector(`[data-agtid="${agtid}"]`);
        if (!card) return;

        // Update status class
        card.className = `agent-card agent-card-${data.agtstatus || 'idle'}`;

        // Update status badge
        const statusBadge = card.querySelector('.agent-status-badge');
        if (statusBadge) {
            statusBadge.className = `badge badge-${data.agtstatus}`;
            statusBadge.textContent = data.agtstatus;
        }

        // Update task
        const taskEl = card.querySelector('.agent-card-task');
        if (taskEl && data.current_task) {
            taskEl.textContent = data.current_task;
        }
    }

    appendOutput(agtid, output) {
        if (!this.outputBuffers[agtid]) {
            this.outputBuffers[agtid] = '';
        }
        this.outputBuffers[agtid] += output;

        // Keep buffer size manageable
        if (this.outputBuffers[agtid].length > 50000) {
            this.outputBuffers[agtid] = this.outputBuffers[agtid].slice(-40000);
        }

        if (this.selectedAgentId == agtid && this.terminalOutput) {
            this.terminalOutput.textContent = this.outputBuffers[agtid];
            this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
        }
    }

    selectAgent(agtid) {
        this.selectedAgentId = agtid;

        // Highlight selected card
        if (this.cardsContainer) {
            this.cardsContainer.querySelectorAll('.agent-card').forEach(c => {
                c.style.outline = c.dataset.agtid == agtid ? '3px solid var(--gold-primary)' : 'none';
            });
        }

        // Show detail panel
        if (this.detailPanel) {
            this.detailPanel.classList.add('visible');
        }

        // Load terminal output
        if (this.terminalOutput) {
            this.terminalOutput.textContent = this.outputBuffers[agtid] || 'No output yet.';
            this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
        }

        // Fetch latest agent info
        this.fetchAgentDetail(agtid);
    }

    async fetchAgentDetail(agtid) {
        try {
            const response = await fetch(`/api/agents/${agtid}`);
            if (response.ok) {
                const data = await response.json();
                this.renderDetail(data);
            }
        } catch (e) {
            console.error('Failed to fetch agent detail:', e);
        }
    }

    renderDetail(agent) {
        const infoEl = document.getElementById('agent-detail-info');
        if (!infoEl) return;

        infoEl.innerHTML = `
            <dl class="detail-list">
                <dt>ID</dt><dd>${agent.agtid}</dd>
                <dt>Role</dt><dd>${agent.agtrole}</dd>
                <dt>Status</dt><dd><span class="badge badge-${agent.agtstatus}">${agent.agtstatus}</span></dd>
                <dt>Project</dt><dd>${agent.prjname || 'N/A'}</dd>
                <dt>Component</dt><dd>${agent.cmpname || 'N/A'}</dd>
                <dt>Model</dt><dd>${agent.agtmodel || 'default'}</dd>
                <dt>Started</dt><dd>${agent.agtstarted || 'N/A'}</dd>
            </dl>
        `;
    }

    updateStats(data) {
        const statsEls = {
            'stat-active': data.active_agents,
            'stat-idle': data.idle_agents,
            'stat-error': data.error_agents,
            'stat-messages': data.pending_messages,
        };

        Object.entries(statsEls).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el && value !== undefined) {
                el.textContent = value;
            }
        });
    }

    async pauseAll() {
        await fetch('/api/agents/pause-all', { method: 'POST' });
    }

    async resumeAll() {
        await fetch('/api/agents/resume-all', { method: 'POST' });
    }

    async spawnAgent(prjid, role) {
        try {
            const body = { role };
            if (prjid) body.prjid = parseInt(prjid);
            const resp = await fetch('/api/agents/spawn', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await resp.json();
            if (resp.ok) {
                this.refreshAgentTree();
                if (typeof updateAllSubheaderCounts === 'function') updateAllSubheaderCounts();
            } else {
                alert(data.error || 'Failed to spawn agent');
            }
        } catch (e) {
            console.error('Spawn agent error:', e);
            alert('Failed to spawn agent');
        }
    }

    async terminateAgent(agtid) {
        if (!confirm('Terminate this agent?')) return;

        try {
            const resp = await fetch(`/api/agents/${agtid}/terminate`, {
                method: 'POST',
            });
            if (resp.ok) {
                this.refreshAgentTree();
                if (typeof updateAllSubheaderCounts === 'function') updateAllSubheaderCounts();
            } else {
                const data = await resp.json();
                alert(data.error || 'Failed to terminate agent');
            }
        } catch (e) {
            console.error('Terminate agent error:', e);
            alert('Failed to terminate agent');
        }
    }

    async refreshAgentTree() {
        try {
            const resp = await fetch('/api/agents');
            if (!resp.ok) return;
            const agents = await resp.json();
            // Filter terminated agents
            const activeAgents = agents.filter(a => a.agtstatus !== 'terminated');

            const tree = document.getElementById('agent-tree');
            if (!tree) return;

            const roleNames = this._roleNames || {};

            tree.querySelectorAll('.agent-tree-group').forEach(group => {
                const role = group.dataset.role;
                const roleAgents = activeAgents.filter(a => a.agtrole === role);

                // Update count badge
                const countEl = group.querySelector('.agent-tree-group-count');
                if (countEl) countEl.textContent = roleAgents.length;

                // Update children
                const childrenEl = group.querySelector('.agent-tree-group-children');
                if (!childrenEl) return;

                if (roleAgents.length === 0) {
                    childrenEl.innerHTML = '<div class="agent-tree-empty">No agents</div>';
                } else {
                    childrenEl.innerHTML = roleAgents.map(agent => `
                        <div class="agent-tree-item agent-tree-item-${agent.agtstatus}"
                             data-agtid="${agent.agtid}"
                             onclick="selectAgentFromTree(${agent.agtid})">
                            <span class="agent-tree-status-dot agent-tree-dot-${agent.agtstatus}"></span>
                            <div class="agent-tree-item-info">
                                <span class="agent-tree-item-name">${agent.agtname || 'Agent #' + agent.agtid}</span>
                                <span class="agent-tree-item-meta">${agent.cmpname || agent.agtstatus}</span>
                            </div>
                            <button class="agent-tree-terminate" onclick="event.stopPropagation(); agentMonitor.terminateAgent(${agent.agtid})" title="Terminate">&times;</button>
                        </div>
                    `).join('');
                }

                // Auto-expand if agents exist
                if (roleAgents.length > 0) {
                    childrenEl.classList.add('expanded');
                    const chevron = group.querySelector('.tree-chevron');
                    if (chevron) chevron.innerHTML = '&#9660;';
                }
            });

            // Update stats bar
            const statActive = document.getElementById('stat-active');
            const statIdle = document.getElementById('stat-idle');
            const statError = document.getElementById('stat-error');
            if (statActive) statActive.textContent = activeAgents.filter(a => a.agtstatus === 'working').length;
            if (statIdle) statIdle.textContent = activeAgents.filter(a => a.agtstatus === 'idle').length;
            if (statError) statError.textContent = activeAgents.filter(a => a.agtstatus === 'error').length;

            // Refresh queue log
            this.refreshQueueLog();
        } catch (e) {
            console.error('Failed to refresh agent tree:', e);
        }
    }

    async refreshQueueLog() {
        try {
            const resp = await fetch('/api/messages?limit=50');
            if (!resp.ok) return;
            const messages = await resp.json();
            const logEl = document.getElementById('queue-log');
            if (!logEl) return;

            if (messages.length === 0) {
                logEl.innerHTML = '<p class="empty-state">No messages in queue.</p>';
                return;
            }

            logEl.innerHTML = messages.map(msg => `
                <div class="queue-log-entry queue-log-${msg.msgtype || 'normal'}">
                    <span class="queue-log-time">${(msg.msgtouchts || '').substring(0, 19)}</span>
                    <span class="queue-log-type badge badge-sm badge-${msg.msgstatus || 'queued'}">${msg.msgstatus || 'queued'}</span>
                    <span class="queue-log-from">${msg.from_name || (msg.from_agtid ? 'Agent #' + msg.from_agtid : 'System')}</span>
                    <span class="queue-log-arrow">&rarr;</span>
                    <span class="queue-log-to">${msg.to_name || (msg.to_agtid ? 'Agent #' + msg.to_agtid : 'Broadcast')}</span>
                    <span class="queue-log-body">${(msg.msgbody || '').substring(0, 80)}</span>
                </div>
            `).join('');
        } catch (e) {
            // Silently fail
        }
    }

}
