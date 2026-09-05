import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-ontology')
export class ViewOntology extends LitElement {
    @state() types: Array<Record<string, unknown>> = [];
    @state() links: Array<Record<string, unknown>> = [];
    @state() loading = true;
    @state() tab = 'types';

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try {
            const [types, links] = await Promise.all([api.get('/admin/ontology/types'), api.get('/admin/ontology/links')]);
            this.types = types as Array<Record<string, unknown>>;
            this.links = links as Array<Record<string, unknown>>;
        } catch { /* empty */ }
        finally { this.loading = false; }
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/ontology"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8">
            <h1 class="text-2xl font-black font-display tracking-tight mb-6">Ontology</h1>
            <div class="flex gap-1 mb-6 bg-white rounded-lg p-1 border border-gray-100 w-fit">
                <button class="px-4 py-2 text-sm font-semibold rounded-md transition-colors ${this.tab === 'types' ? 'bg-brand text-white' : 'text-gray-500'}" @click=${() => { this.tab = 'types'; }}>Object Types</button>
                <button class="px-4 py-2 text-sm font-semibold rounded-md transition-colors ${this.tab === 'links' ? 'bg-brand text-white' : 'text-gray-500'}" @click=${() => { this.tab = 'links'; }}>Link Types</button>
            </div>
            ${this.loading ? html`<div class="text-center text-gray-400 py-16">Loading...</div>` : html`
            ${this.tab === 'types' ? html`
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                ${this.types.map(t => html`
                <div class="bg-white rounded-xl border border-gray-100 p-5 hover:border-brand transition-all">
                    <h3 class="font-bold text-sm mb-1">${t.name}</h3>
                    <p class="text-xs text-gray-400 mb-3">${t.description || 'No description'}</p>
                    <div class="flex gap-4 text-xs text-gray-400">
                        <span>${t.property_count} properties</span>
                        <span>${t.instance_count} instances</span>
                        <span>v${t.version}</span>
                    </div>
                </div>`)}
                ${this.types.length === 0 ? html`<div class="col-span-3 text-center text-gray-400 py-12">No object types defined</div>` : ''}
            </div>` : ''}
            ${this.tab === 'links' ? html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <table class="w-full text-sm"><thead><tr class="border-b border-gray-100 text-left text-xs text-gray-400 uppercase tracking-wider">
                    <th class="px-5 py-3">Name</th><th class="px-5 py-3">Source → Target</th><th class="px-5 py-3">Cardinality</th>
                </tr></thead><tbody>
                ${this.links.map(l => html`
                    <tr class="border-b border-gray-50 hover:bg-gray-50"><td class="px-5 py-3 font-semibold">${l.name}</td><td class="px-5 py-3">${l.source_type} → ${l.target_type}</td><td class="px-5 py-3">${l.cardinality}</td></tr>`)}
                </tbody></table>
                ${this.links.length === 0 ? html`<div class="text-center text-gray-400 py-12">No link types defined</div>` : ''}
            </div>` : ''}
            `}</main>`;
    }
}
