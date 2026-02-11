/**
 * BentWookie EA Chat
 * Persistent Enterprise Architect conversation panel.
 */
class EAChat {
    constructor() {
        this.panel = document.getElementById('ea-chat-panel');
        this.messagesEl = document.getElementById('ea-chat-messages');
        this.inputEl = document.getElementById('ea-chat-input');
        this.isOpen = false;
        this.prjid = null;
        this.pollInterval = null;
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        // Detect current project from page context
        this.prjid = this._detectProjectId();
        if (!this.prjid) {
            console.warn('EA Chat: No project context detected');
            return;
        }

        this.panel.classList.add('open');
        this.isOpen = true;
        this.loadMessages();

        // Poll for new messages every 5 seconds
        this.pollInterval = setInterval(() => this.loadMessages(), 5000);
    }

    close() {
        this.panel.classList.remove('open');
        this.isOpen = false;
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    async loadMessages() {
        if (!this.prjid) return;

        try {
            const resp = await fetch(`/api/ea-chat/${this.prjid}`);
            if (!resp.ok) return;

            const data = await resp.json();
            this._renderMessages(data.messages || []);
        } catch (e) {
            console.error('EA Chat load error:', e);
        }
    }

    async send() {
        if (!this.prjid || !this.inputEl) return;

        const content = this.inputEl.value.trim();
        if (!content) return;

        this.inputEl.value = '';

        try {
            await fetch(`/api/ea-chat/${this.prjid}/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content }),
            });

            // Immediately reload messages
            await this.loadMessages();
        } catch (e) {
            console.error('EA Chat send error:', e);
        }
    }

    _renderMessages(messages) {
        if (!this.messagesEl) return;

        const wasAtBottom = this.messagesEl.scrollTop + this.messagesEl.clientHeight >= this.messagesEl.scrollHeight - 20;

        this.messagesEl.innerHTML = '';
        for (const msg of messages) {
            const div = document.createElement('div');
            div.className = `chat-message chat-message-${msg.imsgsender}`;
            div.textContent = msg.imsgcontent;
            this.messagesEl.appendChild(div);
        }

        if (messages.length === 0) {
            this.messagesEl.innerHTML = '<div class="empty-state" style="padding: 1rem; font-size: 0.875rem;">No messages yet. Start a conversation with the Enterprise Architect.</div>';
        }

        // Auto-scroll if was at bottom
        if (wasAtBottom) {
            this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
        }
    }

    _detectProjectId() {
        // Try project-select dropdown (workspace page)
        const select = document.getElementById('project-select');
        if (select) return select.value;

        // Try URL pattern /workspace/<prjid>
        const match = window.location.pathname.match(/\/workspace\/(\d+)/);
        if (match) return match[1];

        // Try /projects/<prjid>
        const match2 = window.location.pathname.match(/\/projects\/(\d+)/);
        if (match2) return match2[1];

        // Fall back to first project if available
        return null;
    }
}
