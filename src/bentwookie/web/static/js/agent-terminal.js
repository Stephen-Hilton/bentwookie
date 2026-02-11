/**
 * BentWookie Agent Terminal
 * Live terminal output streaming via SSE per-agent endpoint.
 */
class AgentTerminal {
    constructor(containerEl) {
        this.container = containerEl;
        this.eventSource = null;
        this.currentAgentId = null;
    }

    connect(agtid) {
        this.disconnect();
        this.currentAgentId = agtid;
        this.container.textContent = '';
        this._pingCount = 0;
        this._hasOutput = false;

        this.eventSource = new EventSource(`/api/agents/${agtid}/stream`);

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'output' && data.content) {
                    this._hasOutput = true;
                    this._appendContent(data.content);
                } else if (data.type === 'ping') {
                    this._pingCount++;
                    if (!this._hasOutput && this._pingCount >= 2) {
                        this.container.textContent = 'Agent connected. Waiting for output...';
                    }
                }
            } catch (e) {
                // Ignore parse errors
            }
        };

        this.eventSource.onerror = () => {
            if (!this._hasOutput) {
                this.container.textContent = 'Agent stream disconnected. Will retry...';
            }
        };
    }

    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.currentAgentId = null;
    }

    _appendContent(text) {
        if (!this.container) return;

        // If container shows placeholder text, clear it
        if (this.container.textContent === 'Agent connected. Waiting for output...' ||
            this.container.textContent === 'Agent stream disconnected. Will retry...' ||
            this.container.textContent === 'No output yet.' ||
            this.container.textContent === 'Select an agent to view output.') {
            this.container.textContent = '';
        }

        this.container.textContent += text;

        // Cap buffer size
        if (this.container.textContent.length > 100000) {
            this.container.textContent = this.container.textContent.slice(-80000);
        }

        // Auto-scroll
        this.container.scrollTop = this.container.scrollHeight;
    }
}
