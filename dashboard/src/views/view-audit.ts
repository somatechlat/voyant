import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, type AuditLogItem } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-audit')
export class ViewAudit extends LitElement {
    @state() logs: AuditLogItem[] = [];
    @state() loading = true;
    @state() filterAction = '';
    @state() filterOutcome = '';

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.load();
    }

    async load() {
        this.loading = true;
        let path = '/admin/audit?limit=200';
        if (this.filterAction) path += `&action=${this.filterAction}`;
        try { this.logs = await api.get<AuditLogItem[]>(path); }
        catch { this.logs = []; }
        finally { this.loading = false; }
    }

    private outcomeColor(o: string) {
        if (o === 'success') return 'text-green-700';
        if (o === 'denied') return 'text-brand';
        return 'text-red-700';
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/audit"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8" role="main" aria-label="Audit log">
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-black font-display tracking-tight">Audit Log</h1>
                <div class="flex gap-2">
                    <input type="text" placeholder="Filter by action..." aria-label="Filter audit log by action" class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white w-48"
                        @change=${(e: Event) => { this.filterAction = (e.target as HTMLInputElement).value; this.load(); }} />
                    <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50" aria-label="Refresh audit log" @click=${() => this.load()}>Refresh</button>
                </div>
            </div>
            ${this.loading ? html`<div class="text-center text-gray-500 py-16" role="status" aria-live="polite">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
                <table class="w-full text-sm" role="table" aria-label="Audit log entries">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase tracking-wider">
                        <th class="px-5 py-3">Actor</th><th class="px-5 py-3">Action</th><th class="px-5 py-3">Resource</th><th class="px-5 py-3">Outcome</th><th class="px-5 py-3">IP</th><th class="px-5 py-3">Time</th>
                    </tr></thead>
                    <tbody>
                    ${this.logs.map(l => html`
                        <tr class="border-b border-gray-50 hover:bg-gray-50">
                            <td class="px-5 py-3 font-mono text-xs">${l.actor}</td>
                            <td class="px-5 py-3"><span class="px-2 py-0.5 text-xs bg-gray-100 rounded font-mono">${l.action}</span></td>
                            <td class="px-5 py-3 text-xs">${l.resource_type}:${l.resource_id.slice(0, 8)}</td>
                            <td class="px-5 py-3 font-semibold text-xs ${this.outcomeColor(l.outcome)}">${l.outcome}</td>
                            <td class="px-5 py-3 text-gray-500 text-xs font-mono">${l.ip_address || '—'}</td>
                            <td class="px-5 py-3 text-gray-500 text-xs">${new Date(l.created_at).toLocaleString()}</td>
                        </tr>`)}
                    </tbody>
                </table>
                ${this.logs.length === 0 ? html`<div class="text-center text-gray-500 py-12">No audit events</div>` : ''}
            </div>`}
        </main>`;
    }
}
