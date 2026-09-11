import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-search')
export class ViewSearch extends LitElement {
    @state() query = '';
    @state() results: Array<Record<string, unknown>> = [];
    @state() loading = false;
    @state() indexText = '';
    @state() indexStatus = '';

    createRenderRoot() { return this; }

    async search() {
        if (!this.query.trim()) return;
        this.loading = true;
        try { this.results = await api.get(`/admin/search/query?q=${encodeURIComponent(this.query)}&limit=20`) as Array<Record<string, unknown>>; }
        catch { this.results = []; }
        finally { this.loading = false; }
    }

    async index() {
        if (!this.indexText.trim()) return;
        try {
            await api.post('/admin/search/index', { text: this.indexText });
            this.indexStatus = 'Indexed successfully';
            this.indexText = '';
        } catch { this.indexStatus = 'Indexing failed'; }
    }

    async deleteItem(id: string) {
        await api.del(`/admin/search/${id}`);
        this.results = this.results.filter(r => r.id !== id);
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/search"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8" role="main" aria-label="Search index management">
            <h1 class="text-2xl font-black font-display tracking-tight mb-6">Search Index</h1>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <h3 class="text-sm font-semibold text-gray-500 mb-3">Search</h3>
                    <div class="flex gap-2" role="search" aria-label="Search indexed documents">
                        <input type="text" class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand" aria-label="Search query" placeholder="Search query..." .value=${this.query} @input=${(e: Event) => { this.query = (e.target as HTMLInputElement).value; }} @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter') this.search(); }} />
                        <button class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors" aria-label="Run search" @click=${() => this.search()}>Search</button>
                    </div>
                </div>
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <h3 class="text-sm font-semibold text-gray-500 mb-3">Index Document</h3>
                    <textarea class="w-full h-20 p-3 border border-gray-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand" placeholder="Text to index..." .value=${this.indexText} @input=${(e: Event) => { this.indexText = (e.target as HTMLTextAreaElement).value; }}></textarea>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-xs text-gray-400">${this.indexStatus}</span>
                        <button class="px-4 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors" @click=${() => this.index()}>Index</button>
                    </div>
                </div>
            </div>

            ${this.loading ? html`<div class="text-center text-gray-400 py-8" role="status" aria-live="polite">Searching...</div>` : html`
            <div class="space-y-3" aria-live="polite">
                ${this.results.map(r => html`
                <div class="bg-white rounded-xl border border-gray-100 p-5 flex items-start justify-between hover:border-brand transition-all">
                    <div class="flex-1">
                        <div class="flex items-center gap-3 mb-2">
                            <span class="text-xs font-mono text-gray-400">${r.id}</span>
                            <span class="text-xs font-semibold text-brand">${((r.score as number) * 100).toFixed(1)}%</span>
                        </div>
                        <p class="text-sm text-gray-600">${(r.text_preview as string) || JSON.stringify(r.metadata).slice(0, 200)}</p>
                    </div>
                    <button class="text-xs text-red-500 hover:underline ml-4" aria-label="Delete search result ${r.id}" @click=${() => this.deleteItem(r.id as string)}>Delete</button>
                </div>`)}
                ${this.results.length === 0 && this.query ? html`<div class="text-center text-gray-400 py-8">No results</div>` : ''}
            </div>`}
        </main>`;
    }
}
