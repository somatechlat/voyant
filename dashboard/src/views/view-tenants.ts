import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, type TenantInfo } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-tenants')
export class ViewTenants extends LitElement {
    @state() tenants: TenantInfo[] = [];
    @state() loading = true;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try { this.tenants = await api.get<TenantInfo[]>('/admin/tenants'); }
        catch { this.tenants = []; }
        finally { this.loading = false; }
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/tenants"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8" role="main" aria-label="Tenants management">
            <h1 class="text-2xl font-black font-display tracking-tight mb-6">Tenants</h1>
            ${this.loading ? html`<div class="text-center text-gray-400 py-16" role="status" aria-live="polite">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
                <table class="w-full text-sm" role="table" aria-label="Tenants list">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-400 uppercase tracking-wider">
                        <th class="px-5 py-3">Tenant ID</th><th class="px-5 py-3">Realm</th><th class="px-5 py-3">Jobs</th><th class="px-5 py-3">Sources</th><th class="px-5 py-3">Artifacts</th><th class="px-5 py-3">Last Activity</th>
                    </tr></thead>
                    <tbody>
                    ${this.tenants.map(t => html`
                        <tr class="border-b border-gray-50 hover:bg-gray-50">
                            <td class="px-5 py-3 font-semibold">${t.tenant_id}</td>
                            <td class="px-5 py-3 text-gray-500">${t.realm}</td>
                            <td class="px-5 py-3">${t.job_count}</td>
                            <td class="px-5 py-3">${t.source_count}</td>
                            <td class="px-5 py-3">${t.artifact_count}</td>
                            <td class="px-5 py-3 text-gray-400 text-xs">${t.last_activity ? new Date(t.last_activity).toLocaleString() : '—'}</td>
                        </tr>`)}
                    </tbody>
                </table>
                ${this.tenants.length === 0 ? html`<div class="text-center text-gray-400 py-12">No tenants found</div>` : ''}
            </div>`}
        </main>`;
    }
}
