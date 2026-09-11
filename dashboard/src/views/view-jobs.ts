import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, type JobListItem, type JobDetail } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-jobs')
export class ViewJobs extends LitElement {
    @state() jobs: JobListItem[] = [];
    @state() loading = true;
    @state() filterStatus = '';
    @state() filterType = '';

    // Create job form
    @state() showCreate = false;
    @state() createType = 'ingest';
    @state() createSourceId = '';
    @state() createTable = '';
    @state() createSampleSize = 10000;
    @state() creating = false;
    @state() createResult = '';

    // Job detail drawer
    @state() selectedJob: JobDetail | null = null;
    @state() detailLoading = false;

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

    async viewDetail(jobId: string) {
        this.detailLoading = true;
        this.selectedJob = null;
        try {
            this.selectedJob = await api.get<JobDetail>(`/admin/jobs/${jobId}`);
        } catch { /* empty */ }
        finally { this.detailLoading = false; }
    }

    async createJob() {
        if (!this.createSourceId.trim()) return;
        this.creating = true;
        this.createResult = '';
        try {
            const endpoints: Record<string, string> = {
                ingest: '/admin/jobs/ingest',
                profile: '/admin/jobs/profile',
                quality: '/admin/jobs/quality',
                analyze: '/admin/analyze',
            };
            const body: Record<string, unknown> = { source_id: this.createSourceId };
            if (this.createType === 'ingest') {
                body.mode = 'full';
                if (this.createTable.trim()) body.tables = [this.createTable.trim()];
            } else if (this.createType === 'profile' || this.createType === 'quality') {
                if (this.createTable.trim()) body.table = this.createTable.trim();
                body.sample_size = this.createSampleSize;
            } else if (this.createType === 'analyze') {
                if (this.createTable.trim()) body.table = this.createTable.trim();
                body.sample_size = this.createSampleSize;
            }
            const res = await api.post<{ job_id: string }>(endpoints[this.createType], body);
            this.createResult = `Job created: ${res.job_id}`;
            this.showCreate = false;
            this.createSourceId = '';
            this.createTable = '';
            await this.load();
        } catch (e: unknown) {
            this.createResult = `Error: ${e instanceof Error ? e.message : 'Failed'}`;
        } finally { this.creating = false; }
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
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Jobs management">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Jobs</h1>
                    ${this.createResult ? html`<p class="text-sm mt-1 ${this.createResult.startsWith('Error') ? 'text-red-600' : 'text-green-600'}">${this.createResult}</p>` : ''}
                </div>
                <div class="flex gap-2">
                    <select class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
                        aria-label="Filter by status"
                        @change=${(e: Event) => { this.filterStatus = (e.target as HTMLSelectElement).value; this.load(); }}>
                        <option value="">All Status</option>
                        <option value="queued">Queued</option>
                        <option value="running">Running</option>
                        <option value="completed">Completed</option>
                        <option value="failed">Failed</option>
                        <option value="cancelled">Cancelled</option>
                    </select>
                    <select class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
                        aria-label="Filter by job type"
                        @change=${(e: Event) => { this.filterType = (e.target as HTMLSelectElement).value; this.load(); }}>
                        <option value="">All Types</option>
                        <option value="ingest">Ingest</option>
                        <option value="profile">Profile</option>
                        <option value="quality">Quality</option>
                        <option value="analyze">Analyze</option>
                        <option value="scrape">Scrape</option>
                    </select>
                    <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50" aria-label="Refresh jobs list" @click=${() => this.load()}>Refresh</button>
                    <button class="px-4 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors" aria-expanded=${this.showCreate} aria-label="Create new job" @click=${() => { this.showCreate = !this.showCreate; }}>+ New Job</button>
                </div>
            </div>

            <!-- Create Job Form -->
            ${this.showCreate ? html`
            <div class="bg-white rounded-xl border border-gray-100 p-6 mb-6" role="form" aria-label="Create new job">
                <h3 class="text-sm font-semibold text-gray-500 mb-4">Create New Job</h3>
                <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Type</label>
                        <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white" .value=${this.createType} @change=${(e: Event) => { this.createType = (e.target as HTMLSelectElement).value; }}>
                            <option value="ingest">Ingest</option>
                            <option value="profile">Profile</option>
                            <option value="quality">Quality</option>
                            <option value="analyze">Analyze</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Source ID *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono" placeholder="source-uuid" .value=${this.createSourceId} @input=${(e: Event) => { this.createSourceId = (e.target as HTMLInputElement).value; }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Table (optional)</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono" placeholder="table_name" .value=${this.createTable} @input=${(e: Event) => { this.createTable = (e.target as HTMLInputElement).value; }} />
                    </div>
                    ${this.createType !== 'ingest' ? html`
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Sample Size</label>
                        <input type="number" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" .value=${String(this.createSampleSize)} @input=${(e: Event) => { this.createSampleSize = parseInt((e.target as HTMLInputElement).value) || 10000; }} />
                    </div>` : html`<div></div>`}
                    <div class="flex items-end">
                        <button class="w-full px-4 py-2 text-sm font-bold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.creating ? 'opacity-50' : ''}" ?disabled=${this.creating} @click=${() => this.createJob()}>
                            ${this.creating ? 'Creating...' : 'Create Job'}
                        </button>
                    </div>
                </div>
            </div>` : ''}

            <!-- Jobs Table -->
            ${this.loading ? html`<div class="text-center text-gray-400 py-16" role="status" aria-live="polite">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite" aria-label="Jobs table">
                <table class="w-full text-sm" role="table" aria-label="Jobs list">
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
                        <tr class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer" @click=${() => this.viewDetail(j.job_id)}>
                            <td class="px-4 py-3 font-mono text-xs">${j.job_id.slice(0, 8)}</td>
                            <td class="px-4 py-3"><span class="px-2 py-0.5 text-xs bg-gray-100 rounded font-mono">${j.job_type}</span></td>
                            <td class="px-4 py-3 text-gray-500">${j.tenant_id}</td>
                            <td class="px-4 py-3">${this.statusBadge(j.status)}</td>
                            <td class="px-4 py-3"><div class="w-16 bg-gray-100 rounded-full h-1.5"><div class="bg-blue-500 h-1.5 rounded-full" style="width:${j.progress}%"></div></div></td>
                            <td class="px-4 py-3 text-gray-500 text-xs">${new Date(j.created_at).toLocaleString()}</td>
                            <td class="px-4 py-3" @click=${(e: Event) => e.stopPropagation()}>
                                ${j.status === 'running' || j.status === 'queued' ? html`<button class="text-xs text-red-600 hover:underline" aria-label="Cancel job ${j.job_id.slice(0, 8)}" @click=${() => this.cancel(j.job_id)}>Cancel</button>` : ''}
                                ${j.status === 'failed' ? html`<button class="text-xs text-blue-600 hover:underline" aria-label="Reset job ${j.job_id.slice(0, 8)}" @click=${() => this.reset(j.job_id)}>Reset</button>` : ''}
                            </td>
                        </tr>`)}
                    </tbody>
                </table>
                ${this.jobs.length === 0 ? html`<div class="text-center text-gray-400 py-12">No jobs found</div>` : ''}
            </div>`}

            <!-- Job Detail Drawer -->
            ${this.selectedJob ? html`
            <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Job detail drawer"
                @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this.selectedJob = null; }}>
                <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedJob = null; }}></div>
                <div class="relative w-[480px] bg-white h-full overflow-y-auto shadow-2xl border-l border-gray-200" tabindex="-1">
                    <div class="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
                        <h2 class="font-bold text-sm font-mono">${this.selectedJob.job_id.slice(0, 12)}</h2>
                        <button class="text-gray-400 hover:text-ink" aria-label="Close job detail" @click=${() => { this.selectedJob = null; }}>✕</button>
                    </div>
                    <div class="p-6 space-y-4">
                        <div class="grid grid-cols-2 gap-4">
                            <div><span class="text-xs text-gray-400">Type</span><div class="font-semibold">${this.selectedJob.job_type}</div></div>
                            <div><span class="text-xs text-gray-400">Status</span><div>${this.statusBadge(this.selectedJob.status)}</div></div>
                            <div><span class="text-xs text-gray-400">Tenant</span><div>${this.selectedJob.tenant_id}</div></div>
                            <div><span class="text-xs text-gray-400">Progress</span><div>${this.selectedJob.progress}%</div></div>
                            <div><span class="text-xs text-gray-400">Source</span><div class="font-mono text-xs">${this.selectedJob.source_id || '—'}</div></div>
                            <div><span class="text-xs text-gray-400">Created</span><div class="text-xs">${new Date(this.selectedJob.created_at).toLocaleString()}</div></div>
                        </div>

                        ${this.selectedJob.parameters && Object.keys(this.selectedJob.parameters).length > 0 ? html`
                        <div>
                            <h4 class="text-xs font-semibold text-gray-500 mb-2">Parameters</h4>
                            <pre class="p-3 bg-gray-50 rounded-lg text-xs font-mono overflow-auto max-h-40">${JSON.stringify(this.selectedJob.parameters, null, 2)}</pre>
                        </div>` : ''}

                        ${this.selectedJob.result_summary ? html`
                        <div>
                            <h4 class="text-xs font-semibold text-gray-500 mb-2">Result Summary</h4>
                            <pre class="p-3 bg-gray-50 rounded-lg text-xs font-mono overflow-auto max-h-40">${JSON.stringify(this.selectedJob.result_summary, null, 2)}</pre>
                        </div>` : ''}

                        ${this.selectedJob.error_message ? html`
                        <div>
                            <h4 class="text-xs font-semibold text-red-500 mb-2">Error</h4>
                            <div class="p-3 bg-red-50 rounded-lg text-xs text-red-700">${this.selectedJob.error_message}</div>
                        </div>` : ''}

                        ${this.selectedJob.artifacts.length > 0 ? html`
                        <div>
                            <h4 class="text-xs font-semibold text-gray-500 mb-2">Artifacts (${this.selectedJob.artifacts.length})</h4>
                            <div class="space-y-2">
                                ${this.selectedJob.artifacts.map(a => html`
                                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <div>
                                        <div class="text-sm font-semibold">${a.artifact_type}</div>
                                        <div class="text-xs text-gray-400">${a.format} · ${a.size_bytes ? `${(a.size_bytes / 1024).toFixed(1)}KB` : '—'}</div>
                                    </div>
                                    <a href="/v1/artifacts/${this.selectedJob?.job_id}/${a.artifact_type}/download?format=${a.format}"
                                       class="px-3 py-1 text-xs font-semibold bg-brand text-white rounded hover:bg-black transition-colors"
                                       target="_blank">Download</a>
                                </div>`)}
                            </div>
                        </div>` : ''}

                        <!-- Actions -->
                        <div class="flex gap-2 pt-4 border-t border-gray-100">
                            ${this.selectedJob.status === 'running' || this.selectedJob.status === 'queued' ? html`
                            <button class="px-4 py-2 text-sm font-semibold text-red-600 border border-red-200 rounded-lg hover:bg-red-50" @click=${() => { this.cancel(this.selectedJob!.job_id); this.selectedJob = null; }}>Cancel Job</button>` : ''}
                            ${this.selectedJob.status === 'failed' ? html`
                            <button class="px-4 py-2 text-sm font-semibold text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50" @click=${() => { this.reset(this.selectedJob!.job_id); this.selectedJob = null; }}>Reset to Queued</button>` : ''}
                        </div>
                    </div>
                </div>
            </div>` : ''}

            ${this.detailLoading ? html`
            <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/10" role="status" aria-live="polite">
                <div class="bg-white rounded-xl p-8 shadow-xl">Loading job details...</div>
            </div>` : ''}
        </main>`;
    }
}
