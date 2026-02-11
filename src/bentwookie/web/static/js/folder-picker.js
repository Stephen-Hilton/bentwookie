/**
 * BentWookie Folder Picker
 * Modal-based folder browser that fetches directories from the API.
 */
class FolderPicker {
    constructor() {
        this.overlay = document.getElementById('folder-picker-overlay');
        this.pathEl = document.getElementById('folder-picker-path');
        this.listEl = document.getElementById('folder-picker-list');
        this.currentPath = '';
        this.parentPath = null;
        this.targetInputId = null;
    }

    open(inputId) {
        this.targetInputId = inputId;
        const input = document.getElementById(inputId);
        const startPath = input ? input.value : '';
        this.overlay.style.display = 'flex';
        this.hideNewFolder();
        this.navigate(startPath || '');
    }

    close() {
        this.overlay.style.display = 'none';
        this.hideNewFolder();
    }

    select() {
        if (this.targetInputId && this.currentPath) {
            const input = document.getElementById(this.targetInputId);
            if (input) input.value = this.currentPath;
        }
        this.close();
    }

    goUp() {
        if (this.parentPath) {
            this.navigate(this.parentPath);
        }
    }

    showNewFolder() {
        const inputDiv = document.getElementById('folder-picker-new-input');
        const btn = document.getElementById('folder-picker-new');
        if (inputDiv) {
            inputDiv.style.display = 'flex';
            btn.style.display = 'none';
            const nameInput = document.getElementById('folder-picker-new-name');
            if (nameInput) {
                nameInput.value = '';
                nameInput.focus();
            }
        }
    }

    hideNewFolder() {
        const inputDiv = document.getElementById('folder-picker-new-input');
        const btn = document.getElementById('folder-picker-new');
        if (inputDiv) inputDiv.style.display = 'none';
        if (btn) btn.style.display = '';
    }

    async createFolder() {
        const nameInput = document.getElementById('folder-picker-new-name');
        const name = nameInput ? nameInput.value.trim() : '';
        if (!name) {
            alert('Please enter a folder name');
            return;
        }

        try {
            const resp = await fetch('/api/create-dir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ parent: this.currentPath, name }),
            });
            const data = await resp.json();
            if (resp.ok) {
                this.hideNewFolder();
                this.navigate(data.path);
            } else {
                alert(data.error || 'Failed to create folder');
            }
        } catch (e) {
            console.error('Create folder error:', e);
            alert('Failed to create folder');
        }
    }

    async navigate(path) {
        try {
            const url = '/api/browse-dirs' + (path ? '?path=' + encodeURIComponent(path) : '');
            const resp = await fetch(url);
            const data = await resp.json();

            this.currentPath = data.path;
            this.parentPath = data.parent;
            this.pathEl.textContent = data.path;

            this.listEl.innerHTML = '';
            if (data.dirs.length === 0) {
                this.listEl.innerHTML = '<div class="folder-picker-empty">No subdirectories</div>';
                return;
            }

            for (const dir of data.dirs) {
                const item = document.createElement('div');
                item.className = 'folder-picker-item';
                item.textContent = dir;
                item.addEventListener('click', () => {
                    this.navigate(data.path + '/' + dir);
                });
                this.listEl.appendChild(item);
            }
        } catch (e) {
            console.error('Folder picker error:', e);
            this.listEl.innerHTML = '<div class="folder-picker-empty">Error loading directories</div>';
        }
    }
}
