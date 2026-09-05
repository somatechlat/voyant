import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, type CapsuleListItem } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-capsules')
export class ViewCapsules extends LitElement {
    @state() capsules: CapsuleListItem[] = [];
    @state() loading = true;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try { this.capsules = await api.get<CapsuleListItem[]>('/admin/capsules'); }
        catch { this.capsules = []; }
        finally { this.loading = false; }
    }

    private statusColor(s: string) {
        const m: Record<string, string> = { active: 'bg-green-50 text-green-700 border-green-200', certified: 'bg-blue-50 text-blue-700 border-blue-200', draft: 'bg-gray-50 text-gray-500 border-gray-200', suspended: 'bg-amber-50 text-amber-700 border-amber-200', archived: 'bg-red-50 text-red-700 border-red-200' };
        return m[s] || m.draft;
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/capsules"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8">
            <h1 class="text-2xl font-black font-display tracking-tight mb-6">Capsules</h1>
            ${this.loading ? html`<div class="text-center text-gray-400 py-16">Loading...</div>` : html`
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                ${this.capsules.map(c => html`
                <div class="bg-white rounded-xl border border-gray-100 p-5 hover:border-brand hover:shadow-md transition-all group">
                    <div class="flex items-start justify-between mb-3">
                        <div>
                            <h3 class="font-bold text-sm group-hover:text-brand transition-colors">${c.name}</h3>
                            <p class="text-xs text-gray-400 font-mono">v${c.version}</p>
                        </div>
                        <span class="px-2 py-0.5 text-xs rounded border ${this.statusColor(c.status)}">${c.status}</span>
                    </div>
                    <p class="text-xs text-gray-400 mb-4">${c.capsule_type}</p>
                    <div class="flex items-center gap-4 text-xs text-gray-400">
                        <span>${c.install_count} installs</span>
                        <span>${c.execution_count} runs</span>
                        <span>${c.tenant_id}</span>
                    </div>
                    <div class="flex gap-2 mt-4 pt-3 border-t border-gray-50">
                        ${c.status === 'certified' ? html`<button class="text-xs text-brand font-semibold hover:underline" @click=${() => api.post(`/admin/capsules/${c.id}/activate`).then(() => this.connectedCallback())}>Activate</button>` : ''}
                        ${c.status === 'active' ? html`<button class="text-xs text-amber-600 font-semibold hover:underline" @click=${() => api.post(`/admin/capsules/${c.id}/suspend`, {reason: 'Admin'}).then(() => this.connectedCallback())}>Suspend</button>` : ''}
                        ${c.status === 'active' || c.status === 'suspended' ? html`<button class="text-xs text-gray-400 font-semibold hover:underline" @click=${() => api.post(`/admin/capsules/${c.id}/archive`).then(() => this.connectedCallback())}>Archive</button>` : ''}
                    </div>
                </div>`)}
                ${this.capsules.length === 0 ? html`<div class="col-span-3 text-center text-gray-400 py-12">No capsules installed</div>` : ''}
            </div>`}
        </main>`;
    }
}
