/**
 * BentWookie Interview Chat UI
 * Handles chat interface, voice input, SSE streaming, and AI-embedded form controls.
 */
class InterviewChat {
    constructor(options = {}) {
        this.chatMessages = document.getElementById(options.messagesId || 'chat-messages');
        this.chatInput = document.getElementById(options.inputId || 'chat-input');
        this.sendButton = document.getElementById(options.sendBtnId || 'send-btn');
        this.voiceButton = document.getElementById(options.voiceBtnId || 'voice-btn');
        this.typingIndicator = document.getElementById(options.typingId || 'typing-indicator');
        this.interviewId = options.interviewId;
        this.isRecording = false;
        this.recognition = null;
        this._committedText = '';
        this._msgCounter = 0;

        this.init();
    }

    init() {
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendMessage());
        }

        if (this.chatInput) {
            this.chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        if (this.voiceButton) {
            this.voiceButton.addEventListener('click', () => this.toggleVoice());
        }

        this.initVoice();
        this.initSSE();
        this.rehydrateHistoricalMessages();
        this.scrollToBottom();
    }

    initVoice() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            if (this.voiceButton) {
                this.voiceButton.style.display = 'none';
            }
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onresult = (event) => {
            let finalText = '';
            let interimText = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalText += transcript;
                } else {
                    interimText += transcript;
                }
            }

            if (finalText) {
                this._committedText += this._applyPunctuation(finalText);
            }

            if (this.chatInput) {
                this.chatInput.value = this._committedText + interimText;
            }
        };

        this.recognition.onerror = (event) => {
            // Ignore non-fatal errors (pauses, aborts)
            if (event.error === 'no-speech' || event.error === 'aborted') {
                return;
            }
            this.stopRecording();
        };

        this.recognition.onend = () => {
            // Chrome kills continuous recognition periodically — auto-restart
            if (this.isRecording) {
                try { this.recognition.start(); } catch (e) { /* ignore */ }
            }
        };
    }

    toggleVoice() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }

    startRecording() {
        if (!this.recognition) return;
        this.isRecording = true;
        // Preserve any existing typed text as the base
        const existing = (this.chatInput ? this.chatInput.value.trim() : '');
        this._committedText = existing ? existing + ' ' : '';
        if (this.voiceButton) {
            this.voiceButton.classList.add('recording');
        }
        this.recognition.start();
    }

    stopRecording() {
        this.isRecording = false;
        if (this.voiceButton) {
            this.voiceButton.classList.remove('recording');
        }
        if (this.recognition) {
            try { this.recognition.stop(); } catch (e) { /* ignore */ }
        }
    }

    _applyPunctuation(text) {
        const replacements = [
            [/\bperiod\b/gi, '.'],
            [/\bfull stop\b/gi, '.'],
            [/\bcomma\b/gi, ','],
            [/\bquestion mark\b/gi, '?'],
            [/\bexclamation point\b/gi, '!'],
            [/\bexclamation mark\b/gi, '!'],
            [/\bcolon\b/gi, ':'],
            [/\bsemicolon\b/gi, ';'],
            [/\bsemi-colon\b/gi, ';'],
            [/\bdash\b/gi, '—'],
            [/\bhyphen\b/gi, '-'],
            [/\bellipsis\b/gi, '…'],
            [/\bopen quote\b/gi, '"'],
            [/\bclose quote\b/gi, '"'],
            [/\bquote\b/gi, '"'],
            [/\bopen paren\b/gi, '('],
            [/\bclose paren\b/gi, ')'],
            [/\bopen bracket\b/gi, '['],
            [/\bclose bracket\b/gi, ']'],
            [/\bnew line\b/gi, '\n'],
            [/\bnewline\b/gi, '\n'],
        ];
        let result = text;
        for (const [pattern, replacement] of replacements) {
            result = result.replace(pattern, replacement);
        }
        // Remove extra spaces before punctuation marks
        result = result.replace(/\s+([.,?!:;)}\]—])/g, '$1');
        return result;
    }

    initSSE() {
        const sse = typeof getSSE === 'function' ? getSSE() : null;
        if (!sse) return;

        sse.on('interview_response', (data) => {
            if (data.interview_id == this.interviewId) {
                this.hideTyping();
                this.addMessage('agent', data.content);
                if (data.suggestions) {
                    this.showSuggestions(data.suggestions);
                }
            }
        });
    }

    // ------------------------------------------------------------------
    // Message sending
    // ------------------------------------------------------------------

    async sendMessage() {
        if (!this.chatInput) return;
        const text = this.chatInput.value.trim();
        if (!text) return;

        this.chatInput.value = '';
        this._committedText = '';
        this.sendMessageText(text);
    }

    async sendMessageText(text) {
        this.addMessage('user', text);
        this.showTyping();
        this.clearSuggestions();
        this._enableCompleteButton();

        try {
            const response = await fetch(`/api/interviews/${this.interviewId}/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: text }),
            });

            if (response.ok) {
                const data = await response.json();
                this.hideTyping();
                if (data.response && data.response.content) {
                    this.addMessage('agent', data.response.content);
                }
            } else {
                this.hideTyping();
                this.addMessage('agent', 'Error: Failed to send message. Please try again.');
            }
        } catch (error) {
            this.hideTyping();
            this.addMessage('agent', 'Error: Connection failed. Please try again.');
        }
    }

    _enableCompleteButton() {
        // Enable the complete button once enough messages are exchanged
        const btn = document.getElementById('complete-btn');
        if (btn) {
            const msgCount = this.chatMessages.querySelectorAll('.chat-message').length;
            if (msgCount >= 6) {
                btn.disabled = false;
                btn.removeAttribute('title');
            }
        }
    }

    // ------------------------------------------------------------------
    // Message display
    // ------------------------------------------------------------------

    _nextMessageId() {
        return ++this._msgCounter;
    }

    addMessage(sender, content) {
        if (!this.chatMessages) return;

        const msgId = this._nextMessageId();
        const div = document.createElement('div');
        div.className = `chat-message chat-message-${sender}`;
        div.dataset.msgId = msgId;

        if (sender === 'agent') {
            div.dataset.rawContent = content;
            const segments = this.parseContent(content);
            div.innerHTML = this.renderSegments(segments, msgId, false);
            this._bindFormSubmit(div, msgId);
        } else {
            div.innerHTML = this.formatPlainText(content);
        }

        // Insert before the typing indicator so new messages always appear above it
        if (this.typingIndicator) {
            this.chatMessages.insertBefore(div, this.typingIndicator);
        } else {
            this.chatMessages.appendChild(div);
        }
        this.scrollToBottom();
    }

    // ------------------------------------------------------------------
    // Content formatting and parsing
    // ------------------------------------------------------------------

    formatPlainText(text) {
        // Basic markdown-like formatting with HTML escaping
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    parseContent(text) {
        // Split text into plain text segments and form control segments
        const controlRe = /\[(radio|checkbox|select):([a-zA-Z_]\w*)(?:\s+"([^"]*)")?\]\n((?:- .+\n?)+)/g;
        const segments = [];
        let lastIndex = 0;
        let match;

        while ((match = controlRe.exec(text)) !== null) {
            // Text before the control block
            if (match.index > lastIndex) {
                segments.push({
                    type: 'text',
                    content: text.slice(lastIndex, match.index),
                });
            }

            // Parse options from "- Option" lines
            const optionLines = match[4].trim().split('\n');
            const options = optionLines
                .map(line => line.replace(/^- /, '').trim())
                .filter(Boolean);

            segments.push({
                type: 'control',
                controlType: match[1],
                name: match[2],
                label: match[3] || match[2],
                options: options,
            });

            lastIndex = match.index + match[0].length;
        }

        // Remaining text after last control
        if (lastIndex < text.length) {
            segments.push({
                type: 'text',
                content: text.slice(lastIndex),
            });
        }

        // If no segments were found, treat entire text as plain
        if (segments.length === 0) {
            segments.push({ type: 'text', content: text });
        }

        return segments;
    }

    renderSegments(segments, msgId, disabled) {
        let html = '';
        let hasControls = false;

        for (const seg of segments) {
            if (seg.type === 'text') {
                html += this.formatPlainText(seg.content);
            } else if (seg.type === 'control') {
                hasControls = true;
                if (seg.controlType === 'radio') {
                    html += this.renderRadioControl(seg.name, seg.label, seg.options, msgId, disabled);
                } else if (seg.controlType === 'checkbox') {
                    html += this.renderCheckboxControl(seg.name, seg.label, seg.options, msgId, disabled);
                } else if (seg.controlType === 'select') {
                    html += this.renderSelectControl(seg.name, seg.label, seg.options, msgId, disabled);
                }
            }
        }

        if (hasControls && !disabled) {
            html += `<div class="bw-control-submit">
                <button class="bw-submit-btn btn btn-primary btn-sm" data-msg-id="${msgId}">
                    Submit Selection
                </button>
            </div>`;
        }

        return html;
    }

    renderRadioControl(name, label, options, msgId, disabled) {
        const scopedName = `ctrl_${name}_${msgId}`;
        const disabledAttr = disabled ? ' disabled' : '';
        let html = `<fieldset class="bw-control-group${disabled ? ' disabled' : ''}" data-control-name="${name}">
            <legend class="bw-control-label">${this._escapeHtml(label)}</legend>
            <div class="bw-control-options">`;
        for (const opt of options) {
            const id = `${scopedName}_${this._slugify(opt)}`;
            html += `<label class="bw-control-option">
                <input type="radio" name="${scopedName}" value="${this._escapeAttr(opt)}" id="${id}"${disabledAttr}>
                ${this._escapeHtml(opt)}
            </label>`;
        }
        html += `</div></fieldset>`;
        return html;
    }

    renderCheckboxControl(name, label, options, msgId, disabled) {
        const scopedName = `ctrl_${name}_${msgId}`;
        const disabledAttr = disabled ? ' disabled' : '';
        let html = `<fieldset class="bw-control-group${disabled ? ' disabled' : ''}" data-control-name="${name}">
            <legend class="bw-control-label">${this._escapeHtml(label)}</legend>
            <div class="bw-control-options">`;
        for (const opt of options) {
            const id = `${scopedName}_${this._slugify(opt)}`;
            html += `<label class="bw-control-option">
                <input type="checkbox" name="${scopedName}" value="${this._escapeAttr(opt)}" id="${id}"${disabledAttr}>
                ${this._escapeHtml(opt)}
            </label>`;
        }
        html += `</div></fieldset>`;
        return html;
    }

    renderSelectControl(name, label, options, msgId, disabled) {
        const scopedName = `ctrl_${name}_${msgId}`;
        const disabledAttr = disabled ? ' disabled' : '';
        let html = `<fieldset class="bw-control-group${disabled ? ' disabled' : ''}" data-control-name="${name}">
            <legend class="bw-control-label">${this._escapeHtml(label)}</legend>
            <div class="bw-control-options">
                <select name="${scopedName}"${disabledAttr}>
                    <option value="">-- Select --</option>`;
        for (const opt of options) {
            html += `<option value="${this._escapeAttr(opt)}">${this._escapeHtml(opt)}</option>`;
        }
        html += `</select></div></fieldset>`;
        return html;
    }

    _bindFormSubmit(div, msgId) {
        const submitBtn = div.querySelector(`.bw-submit-btn[data-msg-id="${msgId}"]`);
        if (submitBtn) {
            submitBtn.addEventListener('click', () => this.submitFormControls(msgId));
        }
    }

    submitFormControls(msgId) {
        const msgDiv = this.chatMessages.querySelector(`[data-msg-id="${msgId}"]`);
        if (!msgDiv) return;

        const fieldsets = msgDiv.querySelectorAll('.bw-control-group');
        const selections = [];

        for (const fs of fieldsets) {
            const controlName = fs.dataset.controlName;
            const legend = fs.querySelector('.bw-control-label');
            const label = legend ? legend.textContent.trim() : controlName;

            // Check for select element
            const selectEl = fs.querySelector('select');
            if (selectEl && selectEl.value) {
                selections.push(`${label}: ${selectEl.value}`);
                continue;
            }

            // Check for checked radio/checkbox inputs
            const checked = fs.querySelectorAll('input:checked');
            if (checked.length > 0) {
                const values = Array.from(checked).map(c => c.value);
                selections.push(`${label}: ${values.join(', ')}`);
            }
        }

        if (selections.length === 0) {
            return; // Nothing selected
        }

        // Disable the controls
        const controls = msgDiv.querySelectorAll('input, select, .bw-submit-btn');
        controls.forEach(c => c.disabled = true);
        msgDiv.querySelectorAll('.bw-control-group').forEach(g => g.classList.add('disabled'));

        const text = selections.join('\n');
        this.sendMessageText(text);
    }

    // ------------------------------------------------------------------
    // Rehydrate historical messages with form controls
    // ------------------------------------------------------------------

    rehydrateHistoricalMessages() {
        if (!this.chatMessages) return;

        const agentDivs = this.chatMessages.querySelectorAll('.chat-message-agent[data-raw-content]');
        for (const div of agentDivs) {
            const raw = div.dataset.rawContent;
            if (!raw) continue;

            const segments = this.parseContent(raw);
            const hasControls = segments.some(s => s.type === 'control');
            if (hasControls) {
                const msgId = this._nextMessageId();
                div.dataset.msgId = msgId;
                div.innerHTML = this.renderSegments(segments, msgId, true);
            }
        }
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _escapeAttr(text) {
        return text.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    _slugify(text) {
        return text.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
    }

    showTyping() {
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'flex';
            this.scrollToBottom();
        }
    }

    hideTyping() {
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'none';
        }
    }

    showSuggestions(suggestions) {
        this.clearSuggestions();
        const container = document.getElementById('suggested-responses');
        if (!container || !suggestions) return;

        suggestions.forEach(text => {
            const pill = document.createElement('button');
            pill.className = 'suggested-pill';
            pill.textContent = text;
            pill.addEventListener('click', () => {
                if (this.chatInput) {
                    this.chatInput.value = text;
                    this.sendMessage();
                }
            });
            container.appendChild(pill);
        });
    }

    clearSuggestions() {
        const container = document.getElementById('suggested-responses');
        if (container) container.innerHTML = '';
    }

    scrollToBottom() {
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }
}
