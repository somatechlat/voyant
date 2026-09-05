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

    createRenderRoot() { return this; }

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
        <main class="ml-60 min-h-screen bg-surface p-8">
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
                    <span class="text-xs text-gray-400">Ctrl+Enter to execute</span>
                    <button
                        class="px-5 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.loading ? 'opacity-50' : ''}"
                        ?disabled=${this.loading}
                        @click=${() => this.execute()}
                    >${this.loading ? 'Running...' : 'Execute'}</button>
                </div>
            </div>

            ${this.error ? html`<div class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm mb-6">${this.error}</div>` : ''}

            ${this.result ? html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden mb-6">
                <div class="px-5 py-3 border-b border-gray-100 flex items-center gap-4 text-xs text-gray-400">
                    <span>${this.result.row_count} rows</span>
                    <span>${this.result.execution_time_ms}ms</span>
                    ${this.result.truncated ? html`<span class="text-amber-600">Truncated</span>` : ''}
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
        </main>`;
    }
}
