/**
 * BentWookie Dependency Graph Renderer
 * Simple SVG-based dependency graph visualization.
 * Falls back to dagre-d3 if available, otherwise uses basic SVG.
 */
class DependencyGraph {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.width = options.width || 800;
        this.height = options.height || 500;
        this.nodeWidth = options.nodeWidth || 140;
        this.nodeHeight = options.nodeHeight || 40;
        this.onNodeClick = options.onNodeClick || null;

        this.statusColors = {
            draft: '#D4CFC5',
            defined: '#D9EDF7',
            designed: '#F3E8FF',
            validated: '#FCF3CF',
            building: '#FEF3CD',
            built: '#DFF0D8',
            tested: '#D4EDDA',
            error: '#F2DEDE',
        };
    }

    render(graphData) {
        if (!this.container || !graphData) return;

        const { nodes, edges } = graphData;
        if (!nodes || nodes.length === 0) {
            this.container.innerHTML = '<p class="empty-state">No components to display.</p>';
            return;
        }

        // Check if dagre-d3 is available
        if (typeof dagreD3 !== 'undefined' && typeof d3 !== 'undefined') {
            this.renderDagreD3(graphData);
        } else {
            this.renderSimpleSVG(graphData);
        }
    }

    renderSimpleSVG(graphData) {
        const { nodes, edges } = graphData;

        // Simple layout: nodes in rows by level
        const levels = {};
        nodes.forEach(n => {
            const level = n.cmplevel || 'other';
            if (!levels[level]) levels[level] = [];
            levels[level].push(n);
        });

        const levelOrder = ['project', 'service', 'component', 'function', 'other'];
        const rows = levelOrder.filter(l => levels[l]).map(l => levels[l]);

        const padding = 20;
        const rowHeight = this.nodeHeight + 60;
        const svgHeight = Math.max(rows.length * rowHeight + padding * 2, this.height);
        const maxRowWidth = Math.max(...rows.map(r => r.length));
        const svgWidth = Math.max(maxRowWidth * (this.nodeWidth + 30) + padding * 2, this.width);

        // Position nodes
        const positions = {};
        rows.forEach((row, rowIdx) => {
            const totalWidth = row.length * (this.nodeWidth + 30) - 30;
            const startX = (svgWidth - totalWidth) / 2;

            row.forEach((node, colIdx) => {
                positions[node.cmpid] = {
                    x: startX + colIdx * (this.nodeWidth + 30),
                    y: padding + rowIdx * rowHeight,
                };
            });
        });

        // Build SVG
        let svg = `<svg width="${svgWidth}" height="${svgHeight}" xmlns="http://www.w3.org/2000/svg">`;
        svg += '<defs><marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#8B8579"/></marker></defs>';

        // Edges
        edges.forEach(edge => {
            const from = positions[edge.depends_on_cmpid];
            const to = positions[edge.cmpid];
            if (from && to) {
                const x1 = from.x + this.nodeWidth / 2;
                const y1 = from.y + this.nodeHeight;
                const x2 = to.x + this.nodeWidth / 2;
                const y2 = to.y;
                svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#8B8579" stroke-width="1.5" marker-end="url(#arrowhead)"/>`;
            }
        });

        // Nodes
        nodes.forEach(node => {
            const pos = positions[node.cmpid];
            if (!pos) return;

            const color = this.statusColors[node.cmpstatus] || '#D4CFC5';
            const truncName = node.cmpname.length > 18 ? node.cmpname.slice(0, 16) + '..' : node.cmpname;

            svg += `<g class="graph-node" data-cmpid="${node.cmpid}" style="cursor:pointer">`;
            svg += `<rect x="${pos.x}" y="${pos.y}" width="${this.nodeWidth}" height="${this.nodeHeight}" rx="6" fill="${color}" stroke="#8B7355" stroke-width="1.5"/>`;
            svg += `<text x="${pos.x + this.nodeWidth / 2}" y="${pos.y + this.nodeHeight / 2 + 4}" text-anchor="middle" font-size="12" font-family="sans-serif" fill="#3D3022">${truncName}</text>`;
            svg += '</g>';
        });

        svg += '</svg>';
        this.container.innerHTML = svg;

        // Click handlers
        this.container.querySelectorAll('.graph-node').forEach(g => {
            g.addEventListener('click', () => {
                const cmpid = g.dataset.cmpid;
                if (this.onNodeClick) {
                    this.onNodeClick(cmpid);
                } else {
                    window.location.href = `/components/${cmpid}`;
                }
            });
        });
    }

    renderDagreD3(graphData) {
        const { nodes, edges } = graphData;

        this.container.innerHTML = `<svg width="${this.width}" height="${this.height}"><g/></svg>`;
        const svg = d3.select(this.container).select('svg');
        const inner = svg.select('g');

        const g = new dagreD3.graphlib.Graph().setGraph({
            rankdir: 'TB',
            nodesep: 30,
            ranksep: 50,
            marginx: 20,
            marginy: 20,
        });

        nodes.forEach(node => {
            const color = this.statusColors[node.cmpstatus] || '#D4CFC5';
            g.setNode(node.cmpid, {
                label: node.cmpname,
                width: this.nodeWidth,
                height: this.nodeHeight,
                style: `fill: ${color}; stroke: #8B7355;`,
                labelStyle: 'font-size: 12px; fill: #3D3022;',
            });
        });

        edges.forEach(edge => {
            g.setEdge(edge.depends_on_cmpid, edge.cmpid, {
                arrowhead: 'vee',
                style: 'stroke: #8B8579; fill: none;',
                arrowheadStyle: 'fill: #8B8579;',
            });
        });

        const render = new dagreD3.render();
        render(inner, g);

        // Fit to container
        const gBBox = inner.node().getBBox();
        const scale = Math.min(
            this.width / (gBBox.width + 40),
            this.height / (gBBox.height + 40),
            1
        );
        const xOffset = (this.width - gBBox.width * scale) / 2;
        const yOffset = (this.height - gBBox.height * scale) / 2;
        inner.attr('transform', `translate(${xOffset},${yOffset}) scale(${scale})`);

        // Pan/zoom
        const zoom = d3.zoom().on('zoom', (event) => {
            inner.attr('transform', event.transform);
        });
        svg.call(zoom);

        // Click handlers
        inner.selectAll('g.node').on('click', (event, v) => {
            if (this.onNodeClick) {
                this.onNodeClick(v);
            } else {
                window.location.href = `/components/${v}`;
            }
        });
    }

    updateNodeStatus(cmpid, status) {
        const color = this.statusColors[status] || '#D4CFC5';
        const node = this.container?.querySelector(`[data-cmpid="${cmpid}"] rect`);
        if (node) {
            node.setAttribute('fill', color);
        }
    }
}
