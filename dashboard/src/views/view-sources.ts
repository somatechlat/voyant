import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, type SourceListItem } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-sources')
export class ViewSources extends LitElement {
    @state() sources: SourceListItem[] = [];
    @state() loading = true;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try { this.sources = await api.get<SourceListItem[]>('/admin/sources'); }
        catch { this.sources = []; }
        finally { this.loading = false; }
    }

    private statusColor(s: string) {
        if (s === 'connected') return 'bg-green-50 text-green-700 border-green-200';
        if (s === 'error') return 'bg-red-50 text-red-700 border-red-200';
        return 'bg-amber-50 text-amber-700 border-amber-200';
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/sources"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8">
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-black font-display tracking-tight">Sources</h1>
                <button class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors">+ New Source</button>
            </div>
            ${this.loading ? html`<div class="text-center text-gray-400 py-16">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <table class="w-full text-sm">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-400 uppercase tracking-wider">
                        <th class="px-5 py-3">Name</th>
                        <th class="px-5 py-3">Type</th>
                        <th class="px-5 py-3">Tenant</th>
                        <th class="px-5 py-3">Status</th>
                        <th class="px-5 py-3">Created</th>
                    </tr></thead>
                    <tbody>
                    ${this.sources.map(s => html`
                        <tr class="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                            <td class="px-5 py-3 font-semibold">${s.name}</td>
                            <td class="px-5 py-3"><span class="px-2 py-0.5 text-xs bg-gray-100 rounded font-mono">${s.source_type}</span></td>
                            <td class="px-5 py-3 text-gray-500">${s.tenant_id}</td>
                            <td class="px-5 py-3"><span class="px-2 py-0.5 text-xs rounded border ${this.statusColor(s.status)}">${s.status}</span></td>
                            <td class="px-5 py-3 text-gray-400 text-xs">${new Date(s.created_at).toLocaleDateString()}</td>
                        </tr>`)}
                    </tbody>
                </table>
                ${this.sources.length === 0 ? html`<div class="text-center text-gray-400 py-12">No sources configured</div>` : ''}
            </div>`}
        </main>`;
    }
}
