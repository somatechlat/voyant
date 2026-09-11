import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, type TableInfo } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-monaco-editor';
import '../components/voyant-data-table';

interface SavedQuery {
    id: string;
    name: string;
    description: string;
    query_text: string;
    language: string;
    parameters: Record<string, unknown> | null;
    is_public: boolean;
    created_by: string;
    created_at: string;
    updated_at: string;
}

@customElement('view-sql')
export class ViewSql extends LitElement {
    @state() sql = 'SELECT 1 AS test';
    @state() results: { columns: string[]; rows: unknown[][]; row_count: number; execution_time_ms: number } | null = null;
    @state() running = false;
    @state() error = '';
    @state() tables: TableInfo[] = [];
    @state() history: Array<{ sql: string; time: number; rows: number }> = [];
    @state() savedQueries: SavedQuery[] = [];
    @state() saveDialogOpen = false;
    @state() saveName = '';
    @state() saveDescription = '';
    @state() saveIsPublic = false;
    @state() saving = false;
    @state() activeSavedId: string | null = null;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try {
            const tablesRes = await api.get<TableInfo[] | { tables: TableInfo[] }>('/admin/sql/tables').catch(() => []);
            if (Array.isArray(tablesRes)) {
                this.tables = tablesRes;
            } else if (tablesRes && typeof tablesRes === 'object' && 'tables' in tablesRes) {
                this.tables = (tablesRes as { tables: TableInfo[] }).tables || [];
            } else {
                this.tables = [];
            }
        } catch { /* empty */ }
        this._loadSavedQueries();
    }

    async _loadSavedQueries() {
        try {
            const res = await api.get<SavedQuery[]>('/sql/saved');
            this.savedQueries = Array.isArray(res) ? res : [];
        } catch { /* empty */ }
    }

    async _runQuery() {
        this.running = true;
        this.error = '';
        this.results = null;
        const start = performance.now();
        try {
            const res = await api.post('/sql/query', { sql: this.sql, limit: 1000 });
            const elapsed = Math.round(performance.now() - start);
            this.results = res as typeof this.results;
            this.history = [{ sql: this.sql, time: elapsed, rows: (this.results?.row_count || 0) }, ...this.history.slice(0, 19)];
        } catch (e: unknown) {
            this.error = (e as Error).message || 'Query failed';
        }
        finally { this.running = false; }
    }

    private _onRun(e: CustomEvent) {
        this.sql = e.detail.value;
        this._runQuery();
    }

    private _onEditorChange(e: CustomEvent) {
        this.sql = e.detail.value;
    }

    private _openSaveDialog() {
        this.saveName = this.activeSavedId
            ? (this.savedQueries.find(q => q.id === this.activeSavedId)?.name || '')
            : '';
        this.saveDescription = this.activeSavedId
            ? (this.savedQueries.find(q => q.id === this.activeSavedId)?.description || '')
            : '';
        this.saveIsPublic = this.activeSavedId
            ? (this.savedQueries.find(q => q.id === this.activeSavedId)?.is_public || false)
            : false;
        this.saveDialogOpen = true;
    }

    private _closeSaveDialog() {
        this.saveDialogOpen = false;
        this.saveName = '';
        this.saveDescription = '';
        this.saveIsPublic = false;
    }

    async _saveQuery() {
        if (!this.saveName.trim()) return;
        this.saving = true;
        try {
            const payload = {
                name: this.saveName.trim(),
                description: this.saveDescription.trim(),
                query_text: this.sql,
                language: 'sql',
                parameters: null,
                is_public: this.saveIsPublic,
            };
            if (this.activeSavedId) {
                await api.put(`/sql/saved/${this.activeSavedId}`, payload);
            } else {
                const res = await api.post('/sql/saved', payload) as SavedQuery;
                this.activeSavedId = res.id;
            }
            await this._loadSavedQueries();
            this._closeSaveDialog();
        } catch (e: unknown) {
            this.error = (e as Error).message || 'Failed to save query';
        }
        this.saving = false;
    }

    async _deleteSavedQuery(id: string) {
        try {
            await api.delete(`/sql/saved/${id}`);
            if (this.activeSavedId === id) this.activeSavedId = null;
            await this._loadSavedQueries();
        } catch { /* empty */ }
    }

    private _loadSavedQuery(q: SavedQuery) {
        this.sql = q.query_text;
        this.activeSavedId = q.id;
    }

    private _shareQuery(q: SavedQuery) {
        // Stub: POST /sql/saved/{id}/share
        api.post(`/sql/saved/${q.id}/share`, { message: '' }).catch(() => {});
        alert(`Sharing for "${q.name}" is not yet implemented.`);
    }

    render() {
        const resultColumns = this.results?.columns?.map(c => ({ key: c, label: c, sortable: true })) || [];
        const resultRows = this.results?.rows?.map(r => {
            const obj: Record<string, unknown> = {};
            this.results!.columns.forEach((c, i) => { obj[c] = r[i]; });
            return obj;
        }) || [];

        return html`
        <saas-sidebar currentPath="/admin/sql"></saas-sidebar>
        <main class="ml-60 min-h-screen" style="background:var(--saas-bg-page)" role="main" aria-label="SQL console">
            <div style="padding:32px">
                <h1 style="font-size:28px;font-weight:900;font-family:Geist,Inter,system-ui,sans-serif;letter-spacing:-0.02em">SQL Console</h1>
                <p style="font-size:13px;color:var(--saas-text-secondary);margin-top:4px">Execute read-only queries via Trino · Ctrl+Enter to run</p>

                <div style="display:grid;grid-template-columns:1fr 260px;gap:16px;margin-top:24px">
                    <div>
                        <!-- Monaco Editor -->
                        <div class="voyant-card" style="overflow:hidden;margin-bottom:12px" role="textbox" aria-label="SQL query editor" aria-multiline="true">
                            <voyant-monaco-editor
                                .value=${this.sql}
                                language="sql"
                                height="200px"
                                @change=${this._onEditorChange}
                                @run=${this._onRun}
                            ></voyant-monaco-editor>
                        </div>

                        <!-- Run bar -->
                        <div style="display:flex;gap:8px;align-items:center;margin-bottom:16px">
                            <button class="voyant-btn-primary voyant-btn" aria-label="Run SQL query" @click=${this._runQuery} ?disabled=${this.running}>
                                ${this.running ? html`<span class="animate-spin" style="display:inline-block">⏳</span> Running...` : html`▶ Run Query`}
                            </button>
                            <button class="voyant-btn voyant-btn" aria-label="Save query" @click=${this._openSaveDialog}
                                style="font-size:12px;padding:6px 14px;border:1px solid var(--saas-border);border-radius:6px;cursor:pointer;background:var(--saas-bg-card)">
                                ${this.activeSavedId ? '💾 Update' : '💾 Save'}
                            </button>
                            ${this.results ? html`
                            <span style="font-size:12px;color:var(--saas-text-muted)" aria-live="polite">
                                ${this.results.row_count} rows · ${this.results.execution_time_ms}ms
                            </span>` : ''}
                            ${this.error ? html`<span style="font-size:12px;color:var(--saas-danger)" role="alert">${this.error}</span>` : ''}
                        </div>

                        <!-- Results -->
                        ${this.results ? html`
                        <div class="voyant-card" style="padding:20px" role="region" aria-label="Query results" aria-live="polite">
                            <voyant-data-table
                                .columns=${resultColumns}
                                .rows=${resultRows}
                                .exportable=${true}
                                .filterable=${true}
                            ></voyant-data-table>
                        </div>
                        ` : html`
                        <div class="voyant-card" style="padding:80px;text-align:center" role="status">
                            <div style="font-size:32px;opacity:0.2;margin-bottom:12px">📊</div>
                            <div style="font-size:13px;color:var(--saas-text-muted)">Write a query and press Ctrl+Enter or click Run</div>
                        </div>
                        `}
                    </div>

                    <!-- Sidebar: Tables + Saved Queries + History -->
                    <div style="display:flex;flex-direction:column;gap:16px">
                        <div class="voyant-card" style="padding:16px" role="navigation" aria-label="Database tables">
                            <h3 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Tables</h3>
                            <div style="max-height:200px;overflow-y:auto" role="list" aria-label="Available tables">
                                ${this.tables.length > 0 ? this.tables.map(t => html`
                                <div style="padding:6px 8px;border-radius:6px;font-size:12px;cursor:pointer;transition:all 120ms;font-family:JetBrains Mono,monospace"
                                    role="listitem"
                                    tabindex="0"
                                    aria-label="Insert query for table ${t.name}"
                                    @mouseenter=${(e: Event) => (e.currentTarget as HTMLElement).style.background = 'var(--saas-brand-light)'}
                                    @mouseleave=${(e: Event) => (e.currentTarget as HTMLElement).style.background = ''}
                                    @click=${() => { this.sql = `SELECT * FROM ${t.name} LIMIT 100`; }}
                                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.sql = `SELECT * FROM ${t.name} LIMIT 100`; } }}>
                                    📋 ${t.name}
                                </div>
                                `) : html`<div style="font-size:11px;color:var(--saas-text-muted)">Loading tables...</div>`}
                            </div>
                        </div>

                        <!-- Saved Queries -->
                        <div class="voyant-card" style="padding:16px" role="region" aria-label="Saved queries">
                            <h3 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Saved Queries</h3>
                            <div style="max-height:200px;overflow-y:auto" role="list" aria-label="Saved queries list">
                                ${this.savedQueries.length > 0 ? this.savedQueries.map(q => html`
                                <div style="padding:8px;border-radius:6px;margin-bottom:6px;border:1px solid ${q.id === this.activeSavedId ? 'var(--saas-brand)' : 'var(--saas-border)'};cursor:pointer;transition:all 120ms"
                                    role="listitem"
                                    tabindex="0"
                                    aria-label="Saved query: ${q.name}"
                                    @mouseenter=${(e: Event) => (e.currentTarget as HTMLElement).style.borderColor = 'var(--saas-brand)'}
                                    @mouseleave=${(e: Event) => (e.currentTarget as HTMLElement).style.borderColor = q.id === this.activeSavedId ? 'var(--saas-brand)' : 'var(--saas-border)'}
                                    @click=${() => this._loadSavedQuery(q)}
                                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this._loadSavedQuery(q); } }}>
                                    <div style="display:flex;justify-content:space-between;align-items:center">
                                        <div style="font-size:12px;font-weight:600;color:var(--saas-text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${q.name}</div>
                                        <div style="display:flex;gap:4px;flex-shrink:0">
                                            <button title="Share" style="background:none;border:none;cursor:pointer;font-size:12px;padding:2px 4px"
                                                @click=${(e: Event) => { e.stopPropagation(); this._shareQuery(q); }}>🔗</button>
                                            <button title="Delete" style="background:none;border:none;cursor:pointer;font-size:12px;padding:2px 4px"
                                                @click=${(e: Event) => { e.stopPropagation(); this._deleteSavedQuery(q.id); }}>🗑</button>
                                        </div>
                                    </div>
                                    ${q.description ? html`<div style="font-size:10px;color:var(--saas-text-muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${q.description}</div>` : ''}
                                    <div style="font-size:10px;color:var(--saas-text-muted);margin-top:2px;font-family:JetBrains Mono,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${q.query_text}</div>
                                </div>
                                `) : html`<div style="font-size:11px;color:var(--saas-text-muted)">No saved queries</div>`}
                            </div>
                        </div>

                        <!-- History -->
                        <div class="voyant-card" style="padding:16px;flex:1" role="region" aria-label="Query history">
                            <h3 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">History</h3>
                            <div style="max-height:300px;overflow-y:auto" role="list" aria-label="Query history list">
                                ${this.history.length > 0 ? this.history.map(h => html`
                                <div style="padding:8px;border-radius:6px;margin-bottom:6px;border:1px solid var(--saas-border);cursor:pointer;transition:all 120ms"
                                    role="listitem"
                                    tabindex="0"
                                    aria-label="Query: ${h.sql.slice(0, 50)}${h.sql.length > 50 ? '...' : ''}"
                                    @mouseenter=${(e: Event) => (e.currentTarget as HTMLElement).style.borderColor = 'var(--saas-brand)'}
                                    @mouseleave=${(e: Event) => (e.currentTarget as HTMLElement).style.borderColor = 'var(--saas-border)'}
                                    @click=${() => { this.sql = h.sql; this.activeSavedId = null; }}
                                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.sql = h.sql; this.activeSavedId = null; } }}>
                                    <div style="font-size:11px;font-family:JetBrains Mono,monospace;color:var(--saas-text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${h.sql}</div>
                                    <div style="font-size:10px;color:var(--saas-text-muted);margin-top:2px">${h.rows} rows · ${h.time}ms</div>
                                </div>
                                `) : html`<div style="font-size:11px;color:var(--saas-text-muted)">No queries yet</div>`}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Save Dialog -->
            ${this.saveDialogOpen ? html`
            <div style="position:fixed;inset:0;background:rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;z-index:1000"
                @click=${this._closeSaveDialog}>
                <div class="voyant-card" style="padding:24px;width:420px;max-width:90vw" @click=${(e: Event) => e.stopPropagation()}>
                    <h2 style="font-size:16px;font-weight:700;margin-bottom:16px">${this.activeSavedId ? 'Update Saved Query' : 'Save Query'}</h2>
                    <div style="margin-bottom:12px">
                        <label style="font-size:12px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:4px">Name *</label>
                        <input type="text" .value=${this.saveName}
                            @input=${(e: Event) => { this.saveName = (e.target as HTMLInputElement).value; }}
                            style="width:100%;padding:8px 12px;border:1px solid var(--saas-border);border-radius:6px;font-size:13px;box-sizing:border-box"
                            placeholder="My query name" />
                    </div>
                    <div style="margin-bottom:12px">
                        <label style="font-size:12px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:4px">Description</label>
                        <input type="text" .value=${this.saveDescription}
                            @input=${(e: Event) => { this.saveDescription = (e.target as HTMLInputElement).value; }}
                            style="width:100%;padding:8px 12px;border:1px solid var(--saas-border);border-radius:6px;font-size:13px;box-sizing:border-box"
                            placeholder="Optional description" />
                    </div>
                    <div style="margin-bottom:16px">
                        <label style="font-size:12px;display:flex;align-items:center;gap:8px;cursor:pointer">
                            <input type="checkbox" .checked=${this.saveIsPublic}
                                @change=${(e: Event) => { this.saveIsPublic = (e.target as HTMLInputElement).checked; }} />
                            <span style="font-weight:600;color:var(--saas-text-muted)">Public (visible to all team members)</span>
                        </label>
                    </div>
                    <div style="display:flex;gap:8px;justify-content:flex-end">
                        <button class="voyant-btn" style="font-size:12px;padding:6px 16px;border:1px solid var(--saas-border);border-radius:6px;cursor:pointer;background:var(--saas-bg-card)"
                            @click=${this._closeSaveDialog}>Cancel</button>
                        <button class="voyant-btn-primary voyant-btn" style="font-size:12px;padding:6px 16px;border-radius:6px;cursor:pointer"
                            @click=${this._saveQuery} ?disabled=${this.saving || !this.saveName.trim()}>
                            ${this.saving ? 'Saving...' : (this.activeSavedId ? 'Update' : 'Save')}
                        </button>
                    </div>
                </div>
            </div>
            ` : ''}
        </main>`;
    }
}
