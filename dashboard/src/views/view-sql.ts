import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-sql')
export class ViewSql extends LitElement {
    @state() sql = '';
    @state() result: { columns: string[]; rows: unknown[][]; row_count: number; execution_time_ms: number; truncated: boolean } | null = null;
    @state() loading = false;
    @state() error = '';
    @state() history: string[] = [];
    @state() tables: Array<{ name: string; table_schema?: string }> = [];
    @state() tablesLoading = false;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadTables();
    }

    async loadTables() {
        this.tablesLoading = true;
        try {
            const res = await api.get<{ tables: Array<{ name: string; table_schema?: string }> }>('/admin/sql/tables');
            this.tables = res.tables || [];
        } catch { this.tables = []; }
        finally { this.tablesLoading = false; }
    }

    insertTable(name: string) {
        this.sql = this.sql ? `${this.sql}\nSELECT * FROM ${name} LIMIT 100;` : `SELECT * FROM ${name} LIMIT 100;`;
    }

    exportCsv() {
        if (!this.result) return;
        const header = this.result.columns.join(',');
        const rows = this.result.rows.map(r => r.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
        const csv = `${header}\n${rows}`;
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'query_result.csv'; a.click();
        URL.revokeObjectURL(url);
    }

    async execute() {
        if (!this.sql.trim()) return;
        this.loading = true;
        this.error = '';
        this.result = null;
        try {
            this.result = await api.post('/admin/sql/execute', { sql: this.sql, limit: 500 });
            this.history = [this.sql, ...this.history.slice(0, 19)];
        } catch (e: unknown) {
            this.error = e instanceof Error ? e.message : 'Query failed';
        } finally { this.loading = false; }
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/sql"></saas-sidebar>
        <div class="ml-60 flex min-h-screen">
            <!-- Table Browser Sidebar -->
            <aside class="w-56 bg-white border-r border-gray-100 p-4 flex-shrink-0 overflow-y-auto">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Tables</h3>
                    <button class="text-xs text-brand hover:underline" @click=${() => this.loadTables()}>Refresh</button>
                </div>
                ${this.tablesLoading ? html`<div class="text-xs text-gray-400">Loading...</div>` : html`
                <div class="space-y-0.5">
                    ${this.tables.map(t => html`
                    <button class="w-full text-left px-2 py-1.5 text-xs font-mono text-gray-600 hover:bg-gray-50 hover:text-brand rounded truncate transition-colors" @click=${() => this.insertTable(t.name)} title="${t.name}">
                        ${t.name}
                    </button>`)}
                    ${this.tables.length === 0 ? html`<div class="text-xs text-gray-400">No tables found</div>` : ''}
                </div>`}
            </aside>

            <!-- Main Content -->
            <main class="flex-1 bg-surface p-8">
                <h1 class="text-2xl font-black font-display tracking-tight mb-6">SQL Console</h1>
                <div class="bg-white rounded-xl border border-gray-100 p-5 mb-6">
                    <textarea
                        class="w-full h-32 p-4 border border-gray-200 rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                        placeholder="SELECT * FROM voyant_job LIMIT 10;"
                        .value=${this.sql}
                        @input=${(e: Event) => { this.sql = (e.target as HTMLTextAreaElement).value; }}
                        @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) this.execute(); }}
                    ></textarea>
                    <div class="flex items-center justify-between mt-3">
                        <span class="text-xs text-gray-400">Ctrl+Enter to execute · Click table name to insert query</span>
                        <div class="flex gap-2">
                            ${this.result ? html`<button class="px-3 py-1.5 text-xs border border-gray-200 rounded-lg hover:bg-gray-50" @click=${() => this.exportCsv()}>Export CSV</button>` : ''}
                            <button
                                class="px-5 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.loading ? 'opacity-50' : ''}"
                                ?disabled=${this.loading}
                                @click=${() => this.execute()}
                            >${this.loading ? 'Running...' : 'Execute'}</button>
                        </div>
                    </div>
                </div>

                ${this.error ? html`<div class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm mb-6">${this.error}</div>` : ''}

                ${this.result ? html`
                <div class="bg-white rounded-xl border border-gray-100 overflow-hidden mb-6">
                    <div class="px-5 py-3 border-b border-gray-100 flex items-center gap-4 text-xs text-gray-400">
                        <span class="font-semibold text-ink">${this.result.row_count} rows</span>
                        <span>${this.result.execution_time_ms}ms</span>
                        ${this.result.truncated ? html`<span class="text-amber-600 font-semibold">Truncated</span>` : ''}
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm">
                            <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-400 uppercase tracking-wider">
                                ${this.result.columns.map(c => html`<th class="px-4 py-2 font-mono">${c}</th>`)}
                            </tr></thead>
                            <tbody>
                            ${this.result.rows.map(row => html`
                                <tr class="border-b border-gray-50 hover:bg-gray-50">
                                    ${row.map(cell => html`<td class="px-4 py-2 font-mono text-xs">${cell === null ? html`<span class="text-gray-300">NULL</span>` : String(cell)}</td>`)}
                                </tr>`)}
                            </tbody>
                        </table>
                    </div>
                </div>` : ''}

                ${this.history.length > 0 ? html`
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <h3 class="text-sm font-semibold text-gray-500 mb-3">History</h3>
                    ${this.history.map(q => html`
                    <button class="block w-full text-left px-3 py-2 text-xs font-mono text-gray-500 hover:bg-gray-50 rounded truncate" @click=${() => { this.sql = q; }}>${q}</button>`)}
                </div>` : ''}
            </main>
        </div>`;
    }
}
