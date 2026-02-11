/**
 * BentWookie SSE Client
 * EventSource wrapper with auto-reconnect and event dispatch.
 */
class BWEventSource {
    constructor(url, options = {}) {
        this.url = url || '/api/events';
        this.reconnectDelay = options.reconnectDelay || 3000;
        this.maxReconnectDelay = options.maxReconnectDelay || 30000;
        this.currentDelay = this.reconnectDelay;
        this.handlers = {};
        this.eventSource = null;
        this.connected = false;
        this.shouldReconnect = true;
    }

    connect() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        this.eventSource = new EventSource(this.url);

        this.eventSource.onopen = () => {
            this.connected = true;
            this.currentDelay = this.reconnectDelay;
            this.dispatch('connected', {});
        };

        this.eventSource.onerror = () => {
            this.connected = false;
            this.eventSource.close();
            this.dispatch('disconnected', {});

            if (this.shouldReconnect) {
                setTimeout(() => this.connect(), this.currentDelay);
                this.currentDelay = Math.min(this.currentDelay * 1.5, this.maxReconnectDelay);
            }
        };

        // Register known event types
        const eventTypes = [
            'agent_status', 'agent_output', 'activity',
            'phase_change', 'build_progress', 'message_sent',
            'stats_update', 'interview_response'
        ];

        eventTypes.forEach(type => {
            this.eventSource.addEventListener(type, (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.dispatch(type, data);
                } catch (e) {
                    this.dispatch(type, { raw: event.data });
                }
            });
        });

        // Catch-all for generic messages
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.dispatch('message', data);
            } catch (e) {
                // Ignore parse errors for heartbeat pings
            }
        };
    }

    on(event, handler) {
        if (!this.handlers[event]) {
            this.handlers[event] = [];
        }
        this.handlers[event].push(handler);
        return this;
    }

    off(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event] = this.handlers[event].filter(h => h !== handler);
        }
        return this;
    }

    dispatch(event, data) {
        if (this.handlers[event]) {
            this.handlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (e) {
                    console.error(`SSE handler error for ${event}:`, e);
                }
            });
        }
    }

    disconnect() {
        this.shouldReconnect = false;
        if (this.eventSource) {
            this.eventSource.close();
        }
        this.connected = false;
    }

    isConnected() {
        return this.connected;
    }
}

// Global SSE instance
let bwSSE = null;

function initSSE(url) {
    if (bwSSE) {
        bwSSE.disconnect();
    }
    bwSSE = new BWEventSource(url);
    bwSSE.connect();
    return bwSSE;
}

function getSSE() {
    if (!bwSSE) {
        bwSSE = initSSE('/api/events');
    }
    return bwSSE;
}
