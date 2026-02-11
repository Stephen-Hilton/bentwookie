/**
 * BentWookie Detail Panel Renderer
 *
 * Renders the right-panel detail view in the workspace based on the selected
 * hierarchy node.  Fetches component data from /api/components/<id> and
 * renders using .detail-header / .detail-content / .detail-section / .detail-grid
 * CSS classes.
 *
 * Usage:
 *   const panel = new DetailPanel('detail-header', 'detail-content');
 *   panel.load(cmpid, level);
 */
class DetailPanel {
    constructor(headerElId, contentElId) {
        this.header = document.getElementById(headerElId);
        this.content = document.getElementById(contentElId);
        this.currentId = null;
    }

    /* ------------------------------------------------------------------ */
    /*  Public API                                                         */
    /* ------------------------------------------------------------------ */

    /**
     * Fetch component data and render the detail view.
     * @param {number} cmpid - Component ID
     * @param {string} level - 'service' | 'component' | 'function'
     */
    load(cmpid, level) {
        this.currentId = cmpid;
        this._setLoading();

        fetch('/api/components/' + cmpid)
            .then(r => {
                if (!r.ok) throw new Error('Component not found');
                return r.json();
            })
            .then(data => {
                if (this.currentId !== cmpid) return; // stale
                this._render(data, level);
            })
            .catch(err => {
                if (this.currentId !== cmpid) return;
                this._setError(err.message);
            });
    }

    /**
     * Fetch fresh project data from the API and render the full detail view.
     * @param {number} prjid - Project ID
     */
    loadProject(prjid) {
        this.currentId = null;
        this._setLoading();

        fetch('/api/projects/' + prjid)
            .then(r => {
                if (!r.ok) throw new Error('Project not found');
                return r.json();
            })
            .then(data => {
                this._renderProject(data.project, data.stats);
            })
            .catch(err => {
                this._setError(err.message);
            });
    }

    _renderProject(project, stats) {
        if (this.header) this.header.textContent = project.prjname;

        let html = '';

        // Attributes
        html += this._section(project.prjname, this._grid({
            'Phase': this._badge(project.prjphase),
            'Description': project.prjdesc || 'N/A',
            'Code Directory': project.prjcodedir || 'N/A',
        }));

        // Progress
        if (stats) {
            const pct = stats.progress_pct || 0;
            const cc = stats.component_counts || {};
            html += this._section('Progress',
                this._progressBar(pct) +
                this._grid({
                    'Total Components': stats.total_components || 0,
                    'Services': cc.service || 0,
                    'Components': cc.component || 0,
                    'Functions': cc['function'] || 0,
                    'Active Agents': (stats.agent_counts?.working || 0) + (stats.agent_counts?.idle || 0),
                })
            );
        }

        // Actions
        const prjid = project.prjid;
        let actions = '<div class="button-group">' +
            '<a href="/projects/' + prjid + '/edit" class="btn btn-sm">Edit Project</a>' +
            '<a href="/projects/' + prjid + '" class="btn btn-sm">Full View</a>';
        if (project.prjphase === 'define') {
            actions += '<a href="/interviews" class="btn btn-sm btn-primary">Start Interview</a>';
        }
        actions += '</div>';
        html += this._section('Actions', actions);

        if (this.content) this.content.innerHTML = html;
    }

    /* ------------------------------------------------------------------ */
    /*  Rendering                                                          */
    /* ------------------------------------------------------------------ */

    _render(data, level) {
        const levelLabel = this._capitalize(level || data.cmplevel);
        if (this.header) {
            this.header.textContent = levelLabel + ': ' + data.cmpname;
        }

        let html = '';

        // Attributes section
        const attrs = {
            'Name': data.cmpname,
            'Level': '<span class="badge badge-secondary">' + data.cmplevel + '</span>',
            'Status': this._badge(data.cmpstatus),
        };
        if (data.prjname) attrs['Project'] = data.prjname;
        if (data.cmpdesc) attrs['Description'] = data.cmpdesc;
        if (data.assigned_agent) attrs['Assigned Agent'] = data.assigned_agent;

        html += this._section('Attributes', this._grid(attrs));

        // Progress section (if has children)
        if (data.child_count > 0) {
            const pct = Math.round((data.children_complete / data.child_count) * 100);
            html += this._section('Progress',
                this._progressBar(pct) +
                this._grid({
                    'Children': data.child_count,
                    'Complete': data.children_complete,
                })
            );
        }

        // Tests section
        if (data.test_count > 0) {
            html += this._section('Tests', this._grid({
                'Test Specs': data.test_count,
                'Passed': data.tests_passed,
            }));
        }

        // Specification section
        if (data.cmpspec) {
            html += this._section('Specification',
                '<div class="markdown-content">' + this._escapeHtml(data.cmpspec) + '</div>'
            );
        }

        // Actions section
        html += this._section('Actions',
            '<div class="button-group">' +
            '<a href="/components/' + data.cmpid + '" class="btn btn-sm">Full Detail</a>' +
            '</div>'
        );

        if (this.content) this.content.innerHTML = html;
    }

    _setLoading() {
        if (this.header) this.header.textContent = 'Loading...';
        if (this.content) this.content.innerHTML =
            '<div style="padding:2rem;text-align:center;color:#8B7355;">Loading details...</div>';
    }

    _setError(msg) {
        if (this.header) this.header.textContent = 'Error';
        if (this.content) this.content.innerHTML =
            '<div class="error-box"><pre>' + this._escapeHtml(msg) + '</pre></div>';
    }

    /* ------------------------------------------------------------------ */
    /*  HTML helpers                                                       */
    /* ------------------------------------------------------------------ */

    _section(title, bodyHtml) {
        return '<div class="detail-section"><h3>' + this._escapeHtml(title) + '</h3>' + bodyHtml + '</div>';
    }

    _grid(kvPairs) {
        let html = '<div class="detail-grid">';
        for (const [key, val] of Object.entries(kvPairs)) {
            html += '<dt>' + this._escapeHtml(key) + '</dt>';
            html += '<dd>' + val + '</dd>';
        }
        html += '</div>';
        return html;
    }

    _progressBar(pct) {
        return '<div class="detail-progress">' +
            '<div class="detail-progress-bar">' +
            '<div class="detail-progress-fill" style="width:' + pct + '%"></div>' +
            '</div>' +
            '<span class="detail-progress-text">' + pct + '%</span>' +
            '</div>';
    }

    _badge(status) {
        return '<span class="badge badge-' + status + '">' + status + '</span>';
    }

    _capitalize(s) {
        return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
    }

    _escapeHtml(text) {
        if (!text) return '';
        const str = String(text);
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
