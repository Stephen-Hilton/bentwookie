/**
 * BentWookie Hierarchy Tree Renderer
 *
 * Renders the workspace tree using .tree-service / .tree-component / .tree-function
 * CSS classes.  Produces the S-badge / C-badge format described in BUILD_INSTRUCTION.md.
 *
 * Usage:
 *   const tree = new HierarchyTree('container-id', {
 *       onNodeSelect: (cmpid, level) => { ... }
 *   });
 *   tree.render(flatComponentList);
 */
class HierarchyTree {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.onNodeSelect = options.onNodeSelect || null;
        this.onNodeClick = options.onNodeClick || null; // compat
        this.selectedId = null;
    }

    /* ------------------------------------------------------------------ */
    /*  Public API                                                         */
    /* ------------------------------------------------------------------ */

    render(components) {
        if (!this.container) return;
        this.container.innerHTML = '';

        const tree = this._buildTree(components);
        const services = tree.filter(n => n.cmplevel === 'service');
        const roots = services.length > 0 ? services : tree;

        let svcIdx = 0;
        roots.forEach(svc => {
            svcIdx++;
            this.container.appendChild(this._renderService(svc, svcIdx));
        });

        if (roots.length === 0) {
            this.container.innerHTML =
                '<div style="padding:2rem;text-align:center;color:#8B7355;font-style:italic">' +
                'No services defined yet.</div>';
        }
    }

    expandAll() {
        if (!this.container) return;
        this.container.querySelectorAll('.tree-children').forEach(c => c.classList.add('expanded'));
        this.container.querySelectorAll('.tree-chevron').forEach(ch => {
            if (ch.textContent.trim() === '>') ch.textContent = 'v';
        });
    }

    collapseAll() {
        if (!this.container) return;
        this.container.querySelectorAll('.tree-children').forEach(c => c.classList.remove('expanded'));
        this.container.querySelectorAll('.tree-chevron').forEach(ch => {
            if (ch.textContent.trim() === 'v') ch.textContent = '>';
        });
    }

    selectNode(cmpid) {
        this.container.querySelectorAll('.tree-node-selected').forEach(n => n.classList.remove('tree-node-selected'));
        const el = this.container.querySelector(`[data-cmpid="${cmpid}"]`);
        if (el) {
            el.classList.add('tree-node-selected');
            this.selectedId = cmpid;
        }
    }

    updateNodeStatus(cmpid, status) {
        const el = this.container.querySelector(`[data-cmpid="${cmpid}"]`);
        if (!el) return;
        const dot = el.querySelector('.status-dot');
        if (dot) {
            dot.className = 'status-dot ' + this._statusDotClass(status);
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Tree building                                                      */
    /* ------------------------------------------------------------------ */

    _buildTree(components) {
        const map = {};
        const roots = [];

        components.forEach(c => {
            map[c.cmpid] = { ...c, children: [] };
        });

        components.forEach(c => {
            if (c.parent_id && map[c.parent_id]) {
                map[c.parent_id].children.push(map[c.cmpid]);
            } else {
                roots.push(map[c.cmpid]);
            }
        });

        // Compute progress and aggregate agent counts for parent nodes
        Object.values(map).forEach(node => {
            const kids = node.children;
            if (kids.length > 0) {
                const done = kids.filter(k => k.cmpstatus === 'built' || k.cmpstatus === 'tested').length;
                node._progress = Math.round(done / kids.length * 100);
                node.coding_agents = (node.coding_agents || 0) + kids.reduce((s, k) => s + (k.coding_agents || 0), 0);
                node.orchestrator_agents = (node.orchestrator_agents || 0) + kids.reduce((s, k) => s + (k.orchestrator_agents || 0), 0);
            } else {
                node._progress = (node.cmpstatus === 'built' || node.cmpstatus === 'tested') ? 100 : 0;
            }
        });

        return roots;
    }

    /* ------------------------------------------------------------------ */
    /*  Rendering                                                          */
    /* ------------------------------------------------------------------ */

    _renderService(node, svcIdx) {
        const frag = document.createDocumentFragment();

        // Service row
        const row = this._el('div', 'tree-service tree-node tree-node-progress');
        row.dataset.cmpid = node.cmpid;
        row.dataset.level = 'service';
        row.style.setProperty('--progress-pct', (node._progress || 0) + '%');

        const hasKids = node.children && node.children.length > 0;
        const codingAgents = node.coding_agents || 0;
        const orchAgents = node.orchestrator_agents || 0;
        const testIcon = this._testIcon(node.test_status);

        row.innerHTML =
            `<span class="tree-chevron">${hasKids ? '>' : ''}</span>` +
            `<span class="tree-badge tree-badge-s">S</span>` +
            `<div class="tree-label tree-label-service">` +
            `<div class="tree-label-name">S${node.cmpid} - ${node.cmpname}</div>` +
            `<div class="tree-label-meta">${node._progress}% Complete &nbsp;&nbsp; Coding Agents: ${codingAgents} &nbsp;&nbsp; Orchestrator Agents: ${orchAgents} &nbsp;&nbsp; Components: ${node.children.length}</div>` +
            `</div>` +
            `<span class="tree-tests">` +
            `<span class="tree-test-icon">${testIcon}</span>` +
            `<a href="/components/${node.cmpid}?tab=tests" class="tree-test-link">Tests</a></span>`;

        row.addEventListener('click', e => this._handleClick(node, 'service', e));
        frag.appendChild(row);

        // Children container
        if (hasKids) {
            const childDiv = this._el('div', 'tree-children');
            childDiv.id = 'children-' + node.cmpid;

            node.children.forEach(comp => {
                this._appendComponent(childDiv, comp, node.cmpid);
            });

            frag.appendChild(childDiv);
        }

        return frag;
    }

    _appendComponent(container, node, svcCmpId) {
        const row = this._el('div', 'tree-component tree-node tree-node-progress');
        row.dataset.cmpid = node.cmpid;
        row.dataset.level = 'component';
        row.style.setProperty('--progress-pct', (node._progress || 0) + '%');

        const hasKids = node.children && node.children.length > 0;
        const codingAgents = node.coding_agents || 0;
        const testIcon = this._testIcon(node.test_status);

        row.innerHTML =
            `<span class="tree-chevron">${hasKids ? '>' : ''}</span>` +
            `<span class="tree-badge tree-badge-c">C</span>` +
            `<div class="tree-label tree-label-component">` +
            `<div class="tree-label-name">S${svcCmpId}C${node.cmpid} - ${node.cmpname}</div>` +
            `<div class="tree-label-meta">${node._progress}% Complete &nbsp;&nbsp; Coding Agents: ${codingAgents} &nbsp;&nbsp; Functions: ${node.children.length}</div>` +
            `</div>` +
            `<span class="tree-tests">` +
            `<span class="tree-test-icon">${testIcon}</span>` +
            `<a href="/components/${node.cmpid}?tab=tests" class="tree-test-link">Tests</a></span>`;

        row.addEventListener('click', e => this._handleClick(node, 'component', e));
        container.appendChild(row);

        if (hasKids) {
            const childDiv = this._el('div', 'tree-children');
            childDiv.id = 'children-' + node.cmpid;

            node.children.forEach(func => {
                this._appendFunction(childDiv, func);
            });

            container.appendChild(childDiv);
        }
    }

    _appendFunction(container, node) {
        const row = this._el('div', 'tree-function tree-node');
        row.dataset.cmpid = node.cmpid;
        row.dataset.level = 'function';

        const testIcon = this._testIcon(node.test_status);

        row.innerHTML =
            `<span class="status-dot ${this._statusDotClass(node.cmpstatus)}"></span>` +
            `<span class="tree-label tree-label-function">${node.cmpname}</span>` +
            `<span class="tree-tests">` +
            `<span class="tree-test-icon">${testIcon}</span>` +
            `<a href="/components/${node.cmpid}?tab=tests" class="tree-test-link">Tests</a></span>`;

        row.addEventListener('click', e => this._handleClick(node, 'function', e));
        container.appendChild(row);
    }

    /* ------------------------------------------------------------------ */
    /*  Event handling                                                     */
    /* ------------------------------------------------------------------ */

    _handleClick(node, level, event) {
        // If clicking a chevron, toggle children
        if (event.target.classList.contains('tree-chevron')) {
            event.stopPropagation();
            this._toggleChildren(node.cmpid, event.target);
            return;
        }
        // If clicking a link, let it navigate
        if (event.target.tagName === 'A') return;

        event.stopPropagation();
        this.selectNode(node.cmpid);

        if (this.onNodeSelect) {
            this.onNodeSelect(node.cmpid, level);
        }
        // Legacy compat
        if (this.onNodeClick) {
            this.onNodeClick(node.cmpid);
        }
    }

    _toggleChildren(cmpid, chevronEl) {
        const container = document.getElementById('children-' + cmpid);
        if (!container) return;
        container.classList.toggle('expanded');
        chevronEl.textContent = container.classList.contains('expanded') ? 'v' : '>';
    }

    /* ------------------------------------------------------------------ */
    /*  Helpers                                                            */
    /* ------------------------------------------------------------------ */

    _statusDotClass(status) {
        switch (status) {
            case 'built': case 'tested': return 'status-complete';
            case 'building': case 'validated': return 'status-in-progress';
            case 'error': return 'status-error';
            default: return 'status-pending';
        }
    }

    _testIcon(testStatus) {
        switch (testStatus) {
            case 'pass': return '\u{1F7E2}';   // green circle
            case 'partial': return '\u{1F7E1}'; // yellow circle
            default: return '\u26AA';            // white circle
        }
    }

    _el(tag, className) {
        const el = document.createElement(tag);
        if (className) el.className = className;
        return el;
    }
}
