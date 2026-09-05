import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-governance')
export class ViewGovernance extends LitElement {
    @state() tab = 'policies';
    @state() data: Record<string, unknown[]> = { policies: [], contracts: [], quotas: [] };
    @state() loading = true;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try {
            const [policies, contracts, quotas] = await Promise.all([
                api.get('/admin/governance/policies'),
                api.get('/admin/governance/contracts'),
                api.get('/admin/governance/quotas'),
            ]);
            this.data = { policies, contracts, quotas };
        } catch { /* empty */ }
        finally { this.loading = false; }
    }

    render() {
        const tabs = ['policies', 'contracts', 'quotas'];
        return html`
        <saas-sidebar currentPath="/admin/governance"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8">
            <h1 class="text-2xl font-black font-display tracking-tight mb-6">Governance</h1>
            <div class="flex gap-1 mb-6 bg-white rounded-lg p-1 border border-gray-100 w-fit">
                ${tabs.map(t => html`
                <button class="px-4 py-2 text-sm font-semibold rounded-md transition-colors ${this.tab === t ? 'bg-brand text-white' : 'text-gray-500 hover:text-ink'}" @click=${() => { this.tab = t; }}>${t.charAt(0).toUpperCase() + t.slice(1)}</button>`)}
            </div>
            ${this.loading ? html`<div class="text-center text-gray-400 py-16">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                ${this.tab === 'policies' ? html`
                <table class="w-full text-sm"><thead><tr class="border-b border-gray-100 text-left text-xs text-gray-400 uppercase tracking-wider">
                    <th class="px-5 py-3">Name</th><th class="px-5 py-3">Type</th><th class="px-5 py-3">Status</th><th class="px-5 py-3">Level</th><th class="px-5 py-3">Tenant</th>
                </tr></thead><tbody>
                ${(this.data.policies as Array<Record<string, string>>).map((p: Record<string, string>) => html`
                    <tr class="border-b border-gray-50 hover:bg-gray-50"><td class="px-5 py-3 font-semibold">${p.name}</td><td class="px-5 py-3 text-xs font-mono">${p.policy_type}</td><td class="px-5 py-3">${p.status}</td><td class="px-5 py-3">${p.enforcement_level}</td><td class="px-5 py-3 text-gray-500">${p.tenant_id}</td></tr>`)}
                </tbody></table>` : ''}
                ${this.tab === 'contracts' ? html`
                <table class="w-full text-sm"><thead><tr class="border-b border-gray-100 text-left text-xs text-gray-400 uppercase tracking-wider">
                    <th class="px-5 py-3">Name</th><th class="px-5 py-3">Dataset URN</th><th class="px-5 py-3">Status</th><th class="px-5 py-3">Version</th>
                </tr></thead><tbody>
                ${(this.data.contracts as Array<Record<string, unknown>>).map((c: Record<string, unknown>) => html`
                    <tr class="border-b border-gray-50 hover:bg-gray-50"><td class="px-5 py-3 font-semibold">${c.name}</td><td class="px-5 py-3 text-xs font-mono">${c.dataset_urn}</td><td class="px-5 py-3">${c.status}</td><td class="px-5 py-3">v${c.version}</td></tr>`)}
                </tbody></table>` : ''}
                ${this.tab === 'quotas' ? html`
                <table class="w-full text-sm"><thead><tr class="border-b border-gray-100 text-left text-xs text-gray-400 uppercase tracking-wider">
                    <th class="px-5 py-3">Tenant</th><th class="px-5 py-3">Tier</th><th class="px-5 py-3">Jobs</th><th class="px-5 py-3">Artifacts</th><th class="px-5 py-3">Sources</th>
                </tr></thead><tbody>
                ${(this.data.quotas as Array<Record<string, unknown>>).map((q: Record<string, unknown>) => html`
                    <tr class="border-b border-gray-50 hover:bg-gray-50"><td class="px-5 py-3 font-semibold">${q.tenant_id}</td><td class="px-5 py-3">${q.tier}</td><td class="px-5 py-3">${q.jobs_today}/${q.jobs_limit}</td><td class="px-5 py-3">${q.artifacts_gb}GB/${q.artifacts_limit_gb}GB</td><td class="px-5 py-3">${q.sources_count}/${q.sources_limit}</td></tr>`)}
                </tbody></table>` : ''}
            </div>`}
        </main>`;
    }
}
