import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-scraper')
export class ViewScraper extends LitElement {
    @state() jobs: Array<Record<string, unknown>> = [];
    @state() loading = true;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try { this.jobs = await api.get('/admin/scraper/jobs?limit=100') as Array<Record<string, unknown>>; }
        catch { this.jobs = []; }
        finally { this.loading = false; }
    }

    private statusColor(s: string) {
        const m: Record<string, string> = { completed: 'bg-green-50 text-green-700', running: 'bg-blue-50 text-blue-700', failed: 'bg-red-50 text-red-700', cancelled: 'bg-gray-50 text-gray-500' };
        return m[s] || 'bg-amber-50 text-amber-700';
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/scraper"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8">
            <h1 class="text-2xl font-black font-display tracking-tight mb-6">Scraper</h1>
            ${this.loading ? html`<div class="text-center text-gray-400 py-16">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <table class="w-full text-sm">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-400 uppercase tracking-wider">
                        <th class="px-5 py-3">Job ID</th><th class="px-5 py-3">Status</th><th class="px-5 py-3">Pages</th><th class="px-5 py-3">Bytes</th><th class="px-5 py-3">Artifacts</th><th class="px-5 py-3">Errors</th><th class="px-5 py-3">Created</th>
                    </tr></thead>
                    <tbody>
                    ${this.jobs.map(j => html`
                        <tr class="border-b border-gray-50 hover:bg-gray-50">
                            <td class="px-5 py-3 font-mono text-xs">${(j.job_id as string).slice(0, 8)}</td>
                            <td class="px-5 py-3"><span class="px-2 py-0.5 text-xs rounded ${this.statusColor(j.status as string)}">${j.status}</span></td>
                            <td class="px-5 py-3">${j.pages_fetched}</td>
                            <td class="px-5 py-3">${((j.bytes_processed as number) / 1024).toFixed(1)}KB</td>
                            <td class="px-5 py-3">${j.artifact_count}</td>
                            <td class="px-5 py-3 ${j.error_count ? 'text-red-600' : ''}">${j.error_count}</td>
                            <td class="px-5 py-3 text-gray-400 text-xs">${new Date(j.created_at as string).toLocaleString()}</td>
                        </tr>`)}
                    </tbody>
                </table>
                ${this.jobs.length === 0 ? html`<div class="text-center text-gray-400 py-12">No scraper jobs</div>` : ''}
            </div>`}
        </main>`;
    }
}
