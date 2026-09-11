import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-chart';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface ClusterOverview {
    taskmanagers: number;
    slots_total: number;
    slots_available: number;
    jobs_running: number;
    jobs_finished: number;
    jobs_failed: number;
    healthy: boolean;
}

interface FlinkJob {
    job_id: string;
    name: string;
    state: string;
    start_time: number;
}

interface JobDetail {
    job_id: string;
    name: string;
    state: string;
    start_time: number;
    end_time: number;
    duration: number;
    tasks_total: number;
    tasks_running: number;
    tasks_failed: number;
    tasks_finished: number;
}

interface JobVertex {
    id: string;
    name: string;
    parallelism: number;
    status: string;
    start_time: number;
    end_time: number;
}

interface CheckpointStats {
    job_id: string;
    counts_restored: number;
    latest_completed_id: number;
    latest_completed_duration: number;
    latest_completed_size: number;
    latest_triggered_id: number;
    latest_triggered_status: string;
    history: Array<{ id: number; status: string; duration: number; end_to_end_duration: number }>;
}

interface JobMetrics {
    job_id: string;
    metrics: Record<string, unknown>;
}

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-streaming')
export class ViewStreaming extends LitElement {
    @state() cluster: ClusterOverview | null = null;
    @state() jobs: FlinkJob[] = [];
    @state() loading = true;
    @state() error: string | null = null;

    // Detail panel
    @state() selectedJob: JobDetail | null = null;
    @state() selectedVertices: JobVertex[] = [];
    @state() selectedCheckpoints: CheckpointStats | null = null;
    @state() selectedMetrics: JobMetrics | null = null;
    @state() detailLoading = false;

    // Submit modal
    @state() showSubmitModal = false;
    @state() submitForm = { jar_id: '', entry_class: '', program_args: '', parallelism: '' };
    @state() submitting = false;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadData();
    }

    /* ── Data Loading ─────────────────────────────────────────────────────── */

    async loadData() {
        this.loading = true;
        this.error = null;
        try {
            const [cluster, jobsResp] = await Promise.all([
                api.get<ClusterOverview>('/streaming/cluster/overview'),
                api.get<{ jobs: FlinkJob[]; total: number }>('/streaming/jobs'),
            ]);
            this.cluster = cluster;
            this.jobs = jobsResp.jobs || [];
        } catch (e) {
            this.error = e instanceof Error ? e.message : 'Failed to connect to Flink cluster';
            this.cluster = null;
            this.jobs = [];
        } finally {
            this.loading = false;
        }
    }

    async loadJobDetail(jobId: string) {
        this.detailLoading = true;
        this.selectedJob = null;
        this.selectedVertices = [];
        this.selectedCheckpoints = null;
        this.selectedMetrics = null;

        try {
            const [detail, verticesResp, checkpoints, metrics] = await Promise.all([
                api.get<JobDetail>(`/streaming/jobs/${jobId}`),
                api.get<{ job_id: string; vertices: JobVertex[] }>(`/streaming/jobs/${jobId}/vertices`).catch(() => ({ job_id: jobId, vertices: [] })),
                api.get<CheckpointStats>(`/streaming/jobs/${jobId}/checkpoints`).catch(() => null),
                api.get<JobMetrics>(`/streaming/jobs/${jobId}/metrics`).catch(() => null),
            ]);
            this.selectedJob = detail;
            this.selectedVertices = verticesResp.vertices || [];
            this.selectedCheckpoints = checkpoints;
            this.selectedMetrics = metrics;
        } catch {
            this.selectedJob = null;
        } finally {
            this.detailLoading = false;
        }
    }

    async submitJob() {
        this.submitting = true;
        try {
            await api.post('/streaming/jobs/submit', {
                jar_id: this.submitForm.jar_id,
                entry_class: this.submitForm.entry_class || undefined,
                program_args: this.submitForm.program_args || undefined,
                parallelism: this.submitForm.parallelism ? parseInt(this.submitForm.parallelism) : undefined,
            });
            this.showSubmitModal = false;
            this.submitForm = { jar_id: '', entry_class: '', program_args: '', parallelism: '' };
            await this.loadData();
        } catch { /* empty */ } finally {
            this.submitting = false;
        }
    }

    async cancelJob(jobId: string) {
        try {
            await api.post('/streaming/jobs/cancel', { job_id: jobId, drain: false });
            await this.loadData();
            if (this.selectedJob?.job_id === jobId) this.selectedJob = null;
        } catch { /* empty */ }
    }

    /* ── Helpers ──────────────────────────────────────────────────────────── */

    private stateBadge(state: string) {
        const colors: Record<string, string> = {
            RUNNING: 'bg-green-50 text-green-700 border-green-200',
            FINISHED: 'bg-blue-50 text-blue-700 border-blue-200',
            FAILED: 'bg-red-50 text-red-700 border-red-200',
            CANCELED: 'bg-gray-50 text-gray-500 border-gray-200',
            CANCELLING: 'bg-amber-50 text-amber-700 border-amber-200',
            CREATED: 'bg-gray-50 text-gray-500 border-gray-200',
            RESTARTING: 'bg-amber-50 text-amber-700 border-amber-200',
            SUSPENDED: 'bg-purple-50 text-purple-700 border-purple-200',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[state] || 'bg-gray-50 text-gray-700 border-gray-200'}">${state}</span>`;
    }

    private formatDuration(ms: number): string {
        if (ms <= 0) return '—';
        const seconds = Math.floor(ms / 1000);
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
        const hours = Math.floor(minutes / 60);
        return `${hours}h ${minutes % 60}m`;
    }

    private formatTimestamp(ms: number): string {
        if (!ms || ms <= 0) return '—';
        return new Date(ms).toLocaleString();
    }

    /* ── Render ───────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/streaming"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Streaming Monitor">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Streaming Monitor</h1>
                    <p class="text-sm text-gray-400 mt-1">Manage Flink cluster, streaming jobs, checkpoints, and metrics</p>
                </div>
                <div class="flex gap-2">
                    <button class="px-4 py-1.5 text-sm font-semibold border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors flex items-center gap-2"
                        @click=${() => this.loadData()}>
                        <svg class="w-4 h-4 ${this.loading ? 'animate-spin' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                        Refresh
                    </button>
                    <button class="px-4 py-1.5 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
                        @click=${() => { this.showSubmitModal = true; }}>
                        + Submit Job
                    </button>
                </div>
            </div>

            ${this.error ? html`
            <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <svg class="w-5 h-5 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                    <span class="text-sm text-red-700">${this.error}</span>
                </div>
                <button class="text-sm text-red-600 hover:underline" @click=${() => this.loadData()}>Retry</button>
            </div>` : ''}

            ${this.loading ? html`
            <div class="text-center py-16" role="status" aria-live="polite">
                <div class="inline-block w-8 h-8 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin mb-3"></div>
                <div class="text-sm text-gray-400">Connecting to Flink cluster...</div>
            </div>` : html`
            <!-- Cluster Overview -->
            ${this.renderClusterOverview()}

            <!-- Jobs Table -->
            ${this.renderJobsTable()}
            `}

            <!-- Detail Panel -->
            ${this.selectedJob || this.detailLoading ? this.renderDetailPanel() : ''}

            <!-- Submit Modal -->
            ${this.showSubmitModal ? this.renderSubmitModal() : ''}
        </main>`;
    }

    /* ── Cluster Overview ─────────────────────────────────────────────────── */

    private renderClusterOverview() {
        if (!this.cluster) return html``;
        const c = this.cluster;
        const cards = [
            { label: 'TaskManagers', value: c.taskmanagers, color: 'text-gray-900' },
            { label: 'Jobs Running', value: c.jobs_running, color: c.jobs_running > 0 ? 'text-green-600' : 'text-gray-400' },
            { label: 'Jobs Finished', value: c.jobs_finished, color: 'text-blue-600' },
            { label: 'Jobs Failed', value: c.jobs_failed, color: c.jobs_failed > 0 ? 'text-red-600' : 'text-gray-400' },
            { label: 'Total Slots', value: c.slots_total, color: 'text-gray-900' },
            { label: 'Available Slots', value: c.slots_available, color: c.slots_available > 0 ? 'text-green-600' : 'text-amber-600' },
        ];

        return html`
        <div class="grid grid-cols-6 gap-3 mb-6">
            ${cards.map(card => html`
            <div class="bg-white rounded-xl border border-gray-100 p-4">
                <div class="text-xs font-medium text-gray-400 uppercase tracking-wider">${card.label}</div>
                <div class="text-2xl font-black font-display mt-1 ${card.color}">${card.value}</div>
            </div>`)}
        </div>`;
    }

    /* ── Jobs Table ───────────────────────────────────────────────────────── */

    private renderJobsTable() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Flink Jobs</h2>
                <span class="text-xs text-gray-400">${this.jobs.length} jobs</span>
            </div>
            <table class="w-full text-sm" role="table" aria-label="Flink jobs">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">Job ID</th>
                    <th class="px-5 py-3">Name</th>
                    <th class="px-5 py-3">Status</th>
                    <th class="px-5 py-3">Start Time</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.jobs.length === 0 ? html`
                <tr><td colspan="5" class="px-5 py-16 text-center text-gray-400">
                    <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
                        <svg class="w-7 h-7 text-gray-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                    </div>
                    <div class="text-sm font-semibold text-gray-600">No streaming jobs</div>
                    <div class="text-xs mt-2 text-gray-400">Submit a Flink job to start streaming analytics.</div>
                </td></tr>` : ''}
                ${this.jobs.map(j => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                    role="button" tabindex="0"
                    @click=${() => this.loadJobDetail(j.job_id)}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.loadJobDetail(j.job_id); } }}>
                    <td class="px-5 py-3">
                        <span class="text-xs font-mono text-gray-500">${j.job_id.substring(0, 12)}...</span>
                    </td>
                    <td class="px-5 py-3 font-semibold">${j.name || '—'}</td>
                    <td class="px-5 py-3">${this.stateBadge(j.state)}</td>
                    <td class="px-5 py-3 text-xs text-gray-500">${this.formatTimestamp(j.start_time)}</td>
                    <td class="px-5 py-3" @click=${(e: Event) => e.stopPropagation()}>
                        <div class="flex gap-2">
                            <button class="text-xs text-blue-600 hover:underline" @click=${() => this.loadJobDetail(j.job_id)}>Details</button>
                            ${j.state === 'RUNNING' ? html`
                            <button class="text-xs text-red-600 hover:underline" @click=${() => this.cancelJob(j.job_id)}>Cancel</button>` : ''}
                        </div>
                    </td>
                </tr>`)}
                </tbody>
            </table>
        </div>`;
    }

    /* ── Detail Panel ─────────────────────────────────────────────────────── */

    private renderDetailPanel() {
        if (this.detailLoading) {
            return html`
            <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
                <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedJob = null; }}></div>
                <div class="relative w-[720px] bg-white h-full flex items-center justify-center shadow-2xl border-l border-gray-200">
                    <div class="text-gray-400" role="status">Loading job details...</div>
                </div>
            </div>`;
        }

        const job = this.selectedJob!;

        return html`
        <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Job: ${job.name}"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this.selectedJob = null; }}>
            <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedJob = null; }}></div>
            <div class="relative w-[720px] bg-white h-full overflow-y-auto shadow-2xl border-l border-gray-200" tabindex="-1">
                <div class="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between z-10">
                    <div>
                        <h2 class="font-bold text-lg">${job.name || 'Unnamed Job'}</h2>
                        <div class="flex items-center gap-2 mt-1">
                            ${this.stateBadge(job.state)}
                            <span class="text-xs font-mono text-gray-400">${job.job_id}</span>
                        </div>
                    </div>
                    <button class="text-gray-400 hover:text-ink" @click=${() => { this.selectedJob = null; }}>✕</button>
                </div>

                <div class="p-6 space-y-8">
                    <!-- Job Info -->
                    <div class="grid grid-cols-3 gap-4">
                        <div class="p-3 bg-gray-50 rounded-lg">
                            <div class="text-xs text-gray-400">Start Time</div>
                            <div class="text-sm mt-1">${this.formatTimestamp(job.start_time)}</div>
                        </div>
                        <div class="p-3 bg-gray-50 rounded-lg">
                            <div class="text-xs text-gray-400">Duration</div>
                            <div class="text-sm font-semibold mt-1">${this.formatDuration(job.duration)}</div>
                        </div>
                        <div class="p-3 bg-gray-50 rounded-lg">
                            <div class="text-xs text-gray-400">Tasks</div>
                            <div class="text-sm font-semibold mt-1">${job.tasks_running} / ${job.tasks_total} running</div>
                        </div>
                    </div>

                    <!-- Task Breakdown -->
                    <div class="grid grid-cols-4 gap-3">
                        <div class="p-3 bg-green-50 rounded-lg text-center">
                            <div class="text-lg font-bold text-green-700">${job.tasks_running}</div>
                            <div class="text-xs text-green-600">Running</div>
                        </div>
                        <div class="p-3 bg-blue-50 rounded-lg text-center">
                            <div class="text-lg font-bold text-blue-700">${job.tasks_finished}</div>
                            <div class="text-xs text-blue-600">Finished</div>
                        </div>
                        <div class="p-3 bg-red-50 rounded-lg text-center">
                            <div class="text-lg font-bold text-red-700">${job.tasks_failed}</div>
                            <div class="text-xs text-red-600">Failed</div>
                        </div>
                        <div class="p-3 bg-gray-50 rounded-lg text-center">
                            <div class="text-lg font-bold text-gray-700">${job.tasks_total}</div>
                            <div class="text-xs text-gray-600">Total</div>
                        </div>
                    </div>

                    <!-- Vertices -->
                    ${this.selectedVertices.length > 0 ? html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Vertices (Operators)</h3>
                        <div class="bg-white rounded-lg border border-gray-100 overflow-hidden">
                            <table class="w-full text-sm">
                                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                                    <th class="px-4 py-2.5">Name</th>
                                    <th class="px-4 py-2.5">Parallelism</th>
                                    <th class="px-4 py-2.5">Status</th>
                                </tr></thead>
                                <tbody>
                                ${this.selectedVertices.map(v => html`
                                <tr class="border-b border-gray-50">
                                    <td class="px-4 py-2.5 font-medium">${v.name || v.id}</td>
                                    <td class="px-4 py-2.5 text-xs">${v.parallelism}</td>
                                    <td class="px-4 py-2.5">${this.stateBadge(v.status)}</td>
                                </tr>`)}
                                </tbody>
                            </table>
                        </div>
                    </div>` : ''}

                    <!-- Checkpoints -->
                    ${this.selectedCheckpoints ? html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Checkpoints</h3>
                        <div class="grid grid-cols-3 gap-3 mb-3">
                            <div class="p-3 bg-gray-50 rounded-lg">
                                <div class="text-xs text-gray-400">Latest Completed</div>
                                <div class="text-sm font-mono mt-1">#${this.selectedCheckpoints.latest_completed_id}</div>
                            </div>
                            <div class="p-3 bg-gray-50 rounded-lg">
                                <div class="text-xs text-gray-400">Duration</div>
                                <div class="text-sm font-mono mt-1">${this.selectedCheckpoints.latest_completed_duration}ms</div>
                            </div>
                            <div class="p-3 bg-gray-50 rounded-lg">
                                <div class="text-xs text-gray-400">Size</div>
                                <div class="text-sm font-mono mt-1">${(this.selectedCheckpoints.latest_completed_size / 1024).toFixed(1)}KB</div>
                            </div>
                        </div>
                        ${this.selectedCheckpoints.history.length > 0 ? html`
                        <div class="bg-white rounded-lg border border-gray-100 overflow-hidden">
                            <table class="w-full text-sm">
                                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                                    <th class="px-4 py-2.5">ID</th>
                                    <th class="px-4 py-2.5">Status</th>
                                    <th class="px-4 py-2.5">Duration</th>
                                    <th class="px-4 py-2.5">E2E Duration</th>
                                </tr></thead>
                                <tbody>
                                ${this.selectedCheckpoints.history.map(h => html`
                                <tr class="border-b border-gray-50">
                                    <td class="px-4 py-2.5 font-mono">#${h.id}</td>
                                    <td class="px-4 py-2.5 text-xs">${h.status}</td>
                                    <td class="px-4 py-2.5 font-mono text-xs">${h.duration}ms</td>
                                    <td class="px-4 py-2.5 font-mono text-xs">${h.end_to_end_duration}ms</td>
                                </tr>`)}
                                </tbody>
                            </table>
                        </div>` : ''}
                    </div>` : ''}

                    <!-- Metrics -->
                    ${this.selectedMetrics && Object.keys(this.selectedMetrics.metrics || {}).length > 0 ? html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Metrics</h3>
                        <div class="grid grid-cols-2 gap-2">
                            ${Object.entries(this.selectedMetrics.metrics).slice(0, 12).map(([k, v]) => html`
                            <div class="p-2 bg-gray-50 rounded text-xs">
                                <span class="text-gray-500">${k}</span>
                                <span class="float-right font-mono font-semibold">${typeof v === 'number' ? v.toLocaleString() : String(v)}</span>
                            </div>`)}
                        </div>
                    </div>` : ''}

                    <div class="flex gap-2 pt-4 border-t border-gray-100">
                        ${job.state === 'RUNNING' ? html`
                        <button class="px-4 py-2 text-sm font-semibold bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                            @click=${() => this.cancelJob(job.job_id)}>Cancel Job</button>` : ''}
                        <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                            @click=${() => { this.selectedJob = null; }}>Close</button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    /* ── Submit Modal ─────────────────────────────────────────────────────── */

    private renderSubmitModal() {
        return html`
        <div class="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Submit job"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this.showSubmitModal = false; }}>
            <div class="absolute inset-0 bg-black/30" @click=${() => { this.showSubmitModal = false; }}></div>
            <div class="relative bg-white rounded-2xl shadow-2xl w-[520px]" tabindex="-1">
                <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                    <h2 class="font-bold text-lg">Submit Streaming Job</h2>
                    <button class="text-gray-400 hover:text-ink" @click=${() => { this.showSubmitModal = false; }}>✕</button>
                </div>
                <div class="p-6 space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">JAR ID *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="JAR file ID on the Flink cluster"
                            .value=${this.submitForm.jar_id}
                            @input=${(e: Event) => { this.submitForm = { ...this.submitForm, jar_id: (e.target as HTMLInputElement).value }; }}>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Entry Class</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="com.example.MainClass"
                            .value=${this.submitForm.entry_class}
                            @input=${(e: Event) => { this.submitForm = { ...this.submitForm, entry_class: (e.target as HTMLInputElement).value }; }}>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Program Arguments</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="--source-topic events --sink-topic results"
                            .value=${this.submitForm.program_args}
                            @input=${(e: Event) => { this.submitForm = { ...this.submitForm, program_args: (e.target as HTMLInputElement).value }; }}>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Parallelism</label>
                        <input type="number" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="Default"
                            .value=${this.submitForm.parallelism}
                            @input=${(e: Event) => { this.submitForm = { ...this.submitForm, parallelism: (e.target as HTMLInputElement).value }; }}>
                    </div>
                </div>
                <div class="px-6 py-4 border-t border-gray-100 flex items-center justify-end gap-2">
                    <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        @click=${() => { this.showSubmitModal = false; }}>Cancel</button>
                    <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors ${this.submitting ? 'opacity-50' : ''}"
                        ?disabled=${this.submitting || !this.submitForm.jar_id.trim()}
                        @click=${() => this.submitJob()}>
                        ${this.submitting ? 'Submitting...' : 'Submit Job'}
                    </button>
                </div>
            </div>
        </div>`;
    }
}
