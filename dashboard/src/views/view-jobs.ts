import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, type JobListItem } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-jobs')
export class ViewJobs extends LitElement {
    @state() jobs: JobListItem[] = [];
    @state() loading = true;
    @state() filterStatus = '';
    @state() filterType = '';

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.load();
    }

    async load() {
        this.loading = true;
        let path = '/admin/jobs?limit=200';
        if (this.filterStatus) path += `&status=${this.filterStatus}`;
        if (this.filterType) path += `&job_type=${this.filterType}`;
        try { this.jobs = await api.get<JobListItem[]>(path); }
        catch { this.jobs = []; }
        finally { this.loading = false; }
    }

    async cancel(id: string) {
        if (!confirm('Cancel this job?')) return;
        await api.post(`/admin/jobs/${id}/cancel`);
        await this.load();
    }

    async reset(id: string) {
        if (!confirm('Reset this failed job to queued?')) return;
        await api.post(`/admin/jobs/${id}/reset`);
        await this.load();
    }

    private statusBadge(s: string) {
        const colors: Record<string, string> = {
            completed: 'bg-green-50 text-green-700 border-green-200',
            running: 'bg-blue-50 text-blue-700 border-blue-200',
            queued: 'bg-amber-50 text-amber-700 border-amber-200',
            failed: 'bg-red-50 text-red-700 border-red-200',
            cancelled: 'bg-gray-50 text-gray-500 border-gray-200',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[s] || colors.cancelled}">${s}</span>`;
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/jobs"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8">
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-semibold">Jobs</h1>
                <div class="flex gap-2">
                    <select class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
                        @change=${(e: Event) => { this.filterStatus = (e.target as HTMLSelectElement).value; this.load(); }}>
                        <option value="">All Status</option>
                        <option value="queued">Queued</option>
                        <option value="running">Running</option>
                        <option value="completed">Completed</option>
                        <option value="failed">Failed</option>
                        <option value="cancelled">Cancelled</option>
                    </select>
                    <select class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
                        @change=${(e: Event) => { this.filterType = (e.target as HTMLSelectElement).value; this.load(); }}>
                        <option value="">All Types</option>
                        <option value="ingest">Ingest</option>
                        <option value="profile">Profile</option>
                        <option value="quality">Quality</option>
                        <option value="analyze">Analyze</option>
                        <option value="scrape">Scrape</option>
                    </select>
                    <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50" @click=${() => this.load()}>Refresh</button>
                </div>
            </div>

            ${this.loading ? html`<div class="text-center text-gray-400 py-16">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <table class="w-full text-sm">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                        <th class="px-4 py-3">Job ID</th>
                        <th class="px-4 py-3">Type</th>
                        <th class="px-4 py-3">Tenant</th>
                        <th class="px-4 py-3">Status</th>
                        <th class="px-4 py-3">Progress</th>
                        <th class="px-4 py-3">Created</th>
                        <th class="px-4 py-3">Actions</th>
                    </tr></thead>
                    <tbody>
                    ${this.jobs.map(j => html`
                        <tr class="border-b border-gray-50 hover:bg-gray-50">
                            <td class="px-4 py-3 font-mono text-xs">${j.job_id.slice(0, 8)}</td>
                            <td class="px-4 py-3"><span class="px-2 py-0.5 text-xs bg-gray-100 rounded">${j.job_type}</span></td>
                            <td class="px-4 py-3 text-gray-500">${j.tenant_id}</td>
                            <td class="px-4 py-3">${this.statusBadge(j.status)}</td>
                            <td class="px-4 py-3"><div class="w-16 bg-gray-100 rounded-full h-1.5"><div class="bg-blue-500 h-1.5 rounded-full" style="width:${j.progress}%"></div></div></td>
                            <td class="px-4 py-3 text-gray-500 text-xs">${new Date(j.created_at).toLocaleString()}</td>
                            <td class="px-4 py-3">
                                ${j.status === 'running' || j.status === 'queued' ? html`<button class="text-xs text-red-600 hover:underline" @click=${() => this.cancel(j.job_id)}>Cancel</button>` : ''}
                                ${j.status === 'failed' ? html`<button class="text-xs text-blue-600 hover:underline" @click=${() => this.reset(j.job_id)}>Reset</button>` : ''}
                            </td>
                        </tr>`)}
                    </tbody>
                </table>
                ${this.jobs.length === 0 ? html`<div class="text-center text-gray-400 py-12">No jobs found</div>` : ''}
            </div>`}
        </main>`;
    }
}
