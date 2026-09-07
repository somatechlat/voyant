import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-monaco-editor';
import '../components/voyant-data-table';

@customElement('view-sql')
export class ViewSql extends LitElement {
    @state() sql = 'SELECT 1 AS test';
    @state() results: { columns: string[]; rows: Array<Record<string, unknown>>; row_count: number; execution_time_ms: number } | null = null;
    @state() running = false;
    @state() error = '';
    @state() tables: string[] = [];
    @state() history: Array<{ sql: string; time: number; rows: number }> = [];

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try {
            const tablesRes = await api.get('/admin/sql/tables').catch(() => []);
            this.tables = (tablesRes as string[]) || [];
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

    render() {
        const resultColumns = this.results?.columns?.map(c => ({ key: c, label: c, sortable: true })) || [];
        const resultRows = this.results?.rows?.map(r => {
            const obj: Record<string, unknown> = {};
            this.results!.columns.forEach((c, i) => { obj[c] = r[i]; });
            return obj;
        }) || [];

        return html`
        <saas-sidebar currentPath="/admin/sql"></saas-sidebar>
        <main class="ml-60 min-h-screen" style="background:var(--saas-bg-page)">
            <div style="padding:32px">
                <h1 style="font-size:28px;font-weight:900;font-family:Geist,Inter,system-ui,sans-serif;letter-spacing:-0.02em">SQL Console</h1>
                <p style="font-size:13px;color:var(--saas-text-secondary);margin-top:4px">Execute read-only queries via Trino · Ctrl+Enter to run</p>

                <div style="display:grid;grid-template-columns:1fr 260px;gap:16px;margin-top:24px">
                    <div>
                        <!-- Monaco Editor -->
                        <div class="voyant-card" style="overflow:hidden;margin-bottom:12px">
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
                            <button class="voyant-btn-primary voyant-btn" @click=${this._runQuery} ?disabled=${this.running}>
                                ${this.running ? html`<span class="animate-spin" style="display:inline-block">⏳</span> Running...` : html`▶ Run Query`}
                            </button>
                            ${this.results ? html`
                            <span style="font-size:12px;color:var(--saas-text-muted)">
                                ${this.results.row_count} rows · ${this.results.execution_time_ms}ms
                            </span>` : ''}
                            ${this.error ? html`<span style="font-size:12px;color:var(--saas-danger)">${this.error}</span>` : ''}
                        </div>

                        <!-- Results -->
                        ${this.results ? html`
                        <div class="voyant-card" style="padding:20px">
                            <voyant-data-table
                                .columns=${resultColumns}
                                .rows=${resultRows}
                                .exportable=${true}
                                .filterable=${true}
                            ></voyant-data-table>
                        </div>
                        ` : html`
                        <div class="voyant-card" style="padding:80px;text-align:center">
                            <div style="font-size:32px;opacity:0.2;margin-bottom:12px">📊</div>
                            <div style="font-size:13px;color:var(--saas-text-muted)">Write a query and press Ctrl+Enter or click Run</div>
                        </div>
                        `}
                    </div>

                    <!-- Sidebar: Tables + History -->
                    <div style="display:flex;flex-direction:column;gap:16px">
                        <div class="voyant-card" style="padding:16px">
                            <h3 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Tables</h3>
                            <div style="max-height:200px;overflow-y:auto">
                                ${this.tables.length > 0 ? this.tables.map(t => html`
                                <div style="padding:6px 8px;border-radius:6px;font-size:12px;cursor:pointer;transition:all 120ms;font-family:JetBrains Mono,monospace"
                                    @mouseenter=${(e: Event) => (e.currentTarget as HTMLElement).style.background = 'var(--saas-brand-light)'}
                                    @mouseleave=${(e: Event) => (e.currentTarget as HTMLElement).style.background = ''}
                                    @click=${() => { this.sql = `SELECT * FROM ${t} LIMIT 100`; }}>
                                    📋 ${t}
                                </div>
                                `) : html`<div style="font-size:11px;color:var(--saas-text-muted)">Loading tables...</div>`}
                            </div>
                        </div>

                        <div class="voyant-card" style="padding:16px;flex:1">
                            <h3 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">History</h3>
                            <div style="max-height:300px;overflow-y:auto">
                                ${this.history.length > 0 ? this.history.map(h => html`
                                <div style="padding:8px;border-radius:6px;margin-bottom:6px;border:1px solid var(--saas-border);cursor:pointer;transition:all 120ms"
                                    @mouseenter=${(e: Event) => (e.currentTarget as HTMLElement).style.borderColor = 'var(--saas-brand)'}
                                    @mouseleave=${(e: Event) => (e.currentTarget as HTMLElement).style.borderColor = 'var(--saas-border)'}
                                    @click=${() => { this.sql = h.sql; }}>
                                    <div style="font-size:11px;font-family:JetBrains Mono,monospace;color:var(--saas-text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${h.sql}</div>
                                    <div style="font-size:10px;color:var(--saas-text-muted);margin-top:2px">${h.rows} rows · ${h.time}ms</div>
                                </div>
                                `) : html`<div style="font-size:11px;color:var(--saas-text-muted)">No queries yet</div>`}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>`;
    }
}
