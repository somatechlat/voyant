import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-chart';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface RegisteredModel {
    id: string;
    name: string;
    description: string;
    version_count: number;
    latest_stage: string;
    created_at: string;
}

interface ModelEndpoint {
    id: string;
    name: string;
    status: string;
    model_version: string | null;
    endpoint_path: string;
    invocation_count: number;
    avg_latency_ms: number;
}

interface ModelVersion {
    id: string;
    version: number;
    stage: string;
    status: string;
    metrics: Record<string, unknown>;
    description: string;
    created_at: string;
}

interface ModelDetail {
    id: string;
    name: string;
    description: string;
    versions: ModelVersion[];
}

interface EndpointMetrics {
    deployment_id: string;
    deployment_name: string;
    total_invocations: number;
    avg_latency_ms: number;
    metrics: Array<{
        timestamp: string;
        latency_p50: number;
        latency_p95: number;
        latency_p99: number;
        throughput_rps: number;
        error_rate: number;
        request_count: number;
    }>;
}

interface DriftReport {
    deployment_id: string;
    deployment_name: string;
    features_checked: number;
    features_drifted: number;
    overall_drifted: boolean;
    results: Array<{
        feature_name: string;
        drift_metric: string;
        drift_value: number;
        threshold: number;
        is_drifted: boolean;
        timestamp: string;
    }>;
}

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-models')
export class ViewModels extends LitElement {
    @state() models: RegisteredModel[] = [];
    @state() endpoints: ModelEndpoint[] = [];
    @state() loading = true;
    @state() error: string | null = null;

    // Detail panel
    @state() selectedModel: ModelDetail | null = null;
    @state() detailLoading = false;

    // Predict section
    @state() predictEndpoint = '';
    @state() predictInput = '{\n  "input_data": [1, 2, 3, 4]\n}';
    @state() predictResult: Record<string, unknown> | null = null;
    @state() predictLoading = false;

    // Drift section
    @state() selectedEndpointDrift: DriftReport | null = null;
    @state() driftLoading = false;

    // Metrics section
    @state() selectedEndpointMetrics: EndpointMetrics | null = null;
    @state() metricsLoading = false;

    // Deploy modal
    @state() showDeployModal = false;

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
            const [models, endpoints] = await Promise.all([
                api.get<RegisteredModel[]>('/ml/models'),
                api.get<ModelEndpoint[]>('/ml/endpoints'),
            ]);
            this.models = models;
            this.endpoints = endpoints;
        } catch (e) {
            this.error = e instanceof Error ? e.message : 'Failed to load model data';
        } finally {
            this.loading = false;
        }
    }

    async loadModelDetail(modelId: string) {
        this.detailLoading = true;
        try {
            this.selectedModel = await api.get<ModelDetail>(`/ml/models/${modelId}`);
        } catch {
            this.selectedModel = null;
        } finally {
            this.detailLoading = false;
        }
    }

    async loadEndpointMetrics(endpointId: string) {
        this.metricsLoading = true;
        try {
            this.selectedEndpointMetrics = await api.get<EndpointMetrics>(`/ml/deployments/${endpointId}/metrics`);
        } catch {
            this.selectedEndpointMetrics = null;
        } finally {
            this.metricsLoading = false;
        }
    }

    async loadEndpointDrift(endpointId: string) {
        this.driftLoading = true;
        try {
            this.selectedEndpointDrift = await api.get<DriftReport>(`/ml/deployments/${endpointId}/drift`);
        } catch {
            this.selectedEndpointDrift = null;
        } finally {
            this.driftLoading = false;
        }
    }

    async runPredict() {
        if (!this.predictEndpoint) return;
        this.predictLoading = true;
        this.predictResult = null;
        try {
            const body = JSON.parse(this.predictInput);
            this.predictResult = await api.post<Record<string, unknown>>(`/ml/predict/${this.predictEndpoint}`, body);
        } catch (e) {
            this.predictResult = { error: e instanceof Error ? e.message : 'Prediction failed' };
        } finally {
            this.predictLoading = false;
        }
    }

    async rollbackDeployment(endpointId: string) {
        try {
            await api.post(`/ml/deployments/${endpointId}/rollback`, {});
            await this.loadData();
        } catch { /* empty */ }
    }

    /* ── Helpers ──────────────────────────────────────────────────────────── */

    private stageBadge(stage: string) {
        const colors: Record<string, string> = {
            none: 'bg-gray-50 text-gray-500 border-gray-200',
            staging: 'bg-blue-50 text-blue-700 border-blue-200',
            production: 'bg-green-50 text-green-700 border-green-200',
            archived: 'bg-amber-50 text-amber-700 border-amber-200',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[stage] || colors.none}">${stage}</span>`;
    }

    private statusBadge(s: string) {
        const colors: Record<string, string> = {
            active: 'bg-green-50 text-green-700 border-green-200',
            inactive: 'bg-gray-50 text-gray-500 border-gray-200',
        };
        const dot: Record<string, string> = { active: 'bg-green-500', inactive: 'bg-gray-400' };
        return html`<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-medium rounded-full border ${colors[s] || colors.inactive}">
            <span class="inline-block w-1.5 h-1.5 rounded-full ${dot[s] || dot.inactive}"></span>${s}</span>`;
    }

    private driftStatusColor(status: boolean) {
        return status ? 'text-red-600' : 'text-green-600';
    }

    /* ── Render ───────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/models"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Model Serving">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Model Serving</h1>
                    <p class="text-sm text-gray-500 mt-1">Manage model registry, endpoints, predictions, and drift monitoring</p>
                </div>
                <div class="flex gap-2">
                    <button class="px-4 py-1.5 text-sm font-semibold border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors flex items-center gap-2"
                        @click=${() => this.loadData()}>
                        <svg class="w-4 h-4 ${this.loading ? 'animate-spin' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                        Refresh
                    </button>
                    <button class="px-4 py-1.5 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
                        @click=${() => { this.showDeployModal = true; }}>
                        + Deploy Model
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
                <div class="text-sm text-gray-500">Loading models and endpoints...</div>
            </div>` : html`
            <!-- Predict Section -->
            ${this.renderPredictSection()}

            <!-- Models Table -->
            ${this.renderModelsTable()}

            <!-- Endpoints Table -->
            ${this.renderEndpointsTable()}
            `}

            <!-- Detail Panel -->
            ${this.selectedModel || this.detailLoading ? this.renderDetailPanel() : ''}
        </main>`;
    }

    /* ── Predict Section ──────────────────────────────────────────────────── */

    private renderPredictSection() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 p-5 mb-6">
            <h2 class="text-sm font-semibold text-gray-700 mb-3">Predict</h2>
            <div class="flex gap-3 mb-3">
                <select class="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                    .value=${this.predictEndpoint}
                    @change=${(e: Event) => { this.predictEndpoint = (e.target as HTMLSelectElement).value; }}>
                    <option value="">Select endpoint...</option>
                    ${this.endpoints.filter(e => e.status === 'active').map(e => html`
                    <option value="${e.name}">${e.name}</option>`)}
                </select>
                <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors ${this.predictLoading || !this.predictEndpoint ? 'opacity-50' : ''}"
                    ?disabled=${this.predictLoading || !this.predictEndpoint}
                    @click=${() => this.runPredict()}>
                    ${this.predictLoading ? 'Predicting...' : 'Predict'}
                </button>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs text-gray-500 mb-1">Input JSON</label>
                    <textarea class="w-full px-3 py-2 text-xs font-mono border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10" rows="4"
                        .value=${this.predictInput}
                        @input=${(e: Event) => { this.predictInput = (e.target as HTMLTextAreaElement).value; }}></textarea>
                </div>
                <div>
                    <label class="block text-xs text-gray-500 mb-1">Result</label>
                    <pre class="w-full px-3 py-2 text-xs font-mono bg-gray-50 border border-gray-200 rounded-lg overflow-auto h-[104px]">${this.predictResult ? JSON.stringify(this.predictResult, null, 2) : 'No prediction yet'}</pre>
                </div>
            </div>
        </div>`;
    }

    /* ── Models Table ─────────────────────────────────────────────────────── */

    private renderModelsTable() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden mb-6" aria-live="polite">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Registered Models</h2>
                <span class="text-xs text-gray-500">${this.models.length} models</span>
            </div>
            <table class="w-full text-sm" role="table" aria-label="Registered models">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">Name</th>
                    <th class="px-5 py-3">Versions</th>
                    <th class="px-5 py-3">Latest Stage</th>
                    <th class="px-5 py-3">Created</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.models.length === 0 ? html`
                <tr><td colspan="5" class="px-5 py-16 text-center text-gray-500">
                    <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
                        <svg class="w-7 h-7 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                    </div>
                    <div class="text-sm font-semibold text-gray-600">No models registered</div>
                    <div class="text-xs mt-2 text-gray-500">Register a model to start deploying and serving predictions.</div>
                </td></tr>` : ''}
                ${this.models.map(m => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                    role="button" tabindex="0"
                    @click=${() => this.loadModelDetail(m.id)}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.loadModelDetail(m.id); } }}>
                    <td class="px-5 py-3">
                        <div class="font-semibold">${m.name}</div>
                        ${m.description ? html`<div class="text-xs text-gray-500 mt-0.5 truncate max-w-[300px]">${m.description}</div>` : ''}
                    </td>
                    <td class="px-5 py-3"><span class="text-sm font-semibold">${m.version_count}</span></td>
                    <td class="px-5 py-3">${this.stageBadge(m.latest_stage)}</td>
                    <td class="px-5 py-3 text-xs text-gray-500">${new Date(m.created_at).toLocaleDateString()}</td>
                    <td class="px-5 py-3" @click=${(e: Event) => e.stopPropagation()}>
                        <button class="text-xs text-blue-600 hover:underline" @click=${() => this.loadModelDetail(m.id)}>View Versions</button>
                    </td>
                </tr>`)}
                </tbody>
            </table>
        </div>`;
    }

    /* ── Endpoints Table ──────────────────────────────────────────────────── */

    private renderEndpointsTable() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Serving Endpoints</h2>
                <span class="text-xs text-gray-500">${this.endpoints.length} endpoints</span>
            </div>
            <table class="w-full text-sm" role="table" aria-label="Serving endpoints">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">Endpoint Name</th>
                    <th class="px-5 py-3">Status</th>
                    <th class="px-5 py-3">Model Version</th>
                    <th class="px-5 py-3">Invocations</th>
                    <th class="px-5 py-3">Avg Latency</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.endpoints.length === 0 ? html`
                <tr><td colspan="6" class="px-5 py-12 text-center text-gray-500">
                    <div class="text-sm font-semibold text-gray-600">No endpoints configured</div>
                    <div class="text-xs mt-1 text-gray-500">Deploy a model to create a serving endpoint.</div>
                </td></tr>` : ''}
                ${this.endpoints.map(ep => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50">
                    <td class="px-5 py-3">
                        <div class="font-semibold">${ep.name}</div>
                        <div class="text-xs font-mono text-gray-500 mt-0.5">${ep.endpoint_path}</div>
                    </td>
                    <td class="px-5 py-3">${this.statusBadge(ep.status)}</td>
                    <td class="px-5 py-3 text-xs font-mono">${ep.model_version ? `v${ep.model_version}` : '—'}</td>
                    <td class="px-5 py-3 text-sm">${ep.invocation_count.toLocaleString()}</td>
                    <td class="px-5 py-3 text-sm font-mono">${ep.avg_latency_ms.toFixed(1)}ms</td>
                    <td class="px-5 py-3">
                        <div class="flex gap-2">
                            <button class="text-xs text-blue-600 hover:underline"
                                @click=${() => { this.loadEndpointMetrics(ep.id); this.loadEndpointDrift(ep.id); }}>Metrics</button>
                            <button class="text-xs text-amber-600 hover:underline"
                                @click=${() => this.rollbackDeployment(ep.id)}>Rollback</button>
                        </div>
                    </td>
                </tr>`)}
                </tbody>
            </table>
        </div>

        <!-- Drift & Metrics Inline -->
        ${this.selectedEndpointDrift ? this.renderDriftSection() : ''}
        ${this.selectedEndpointMetrics ? this.renderMetricsSection() : ''}`;
    }

    /* ── Drift Section ────────────────────────────────────────────────────── */

    private renderDriftSection() {
        const report = this.selectedEndpointDrift!;
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden mt-6">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Drift Report — ${report.deployment_name}</h2>
                <span class="text-xs ${report.overall_drifted ? 'text-red-600' : 'text-green-600'} font-semibold">
                    ${report.features_drifted} / ${report.features_checked} drifted
                </span>
            </div>
            ${this.driftLoading ? html`<div class="p-8 text-center text-gray-500">Loading drift data...</div>` : html`
            ${report.results.length === 0 ? html`<div class="p-8 text-center text-gray-500">No drift data available.</div>` : html`
            <table class="w-full text-sm">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-2.5">Feature</th>
                    <th class="px-5 py-2.5">Metric</th>
                    <th class="px-5 py-2.5">Value</th>
                    <th class="px-5 py-2.5">Threshold</th>
                    <th class="px-5 py-2.5">Status</th>
                </tr></thead>
                <tbody>
                ${report.results.map(r => html`
                <tr class="border-b border-gray-50">
                    <td class="px-5 py-2.5 font-medium">${r.feature_name}</td>
                    <td class="px-5 py-2.5"><span class="px-1.5 py-0.5 text-xs bg-gray-100 rounded font-mono">${r.drift_metric}</span></td>
                    <td class="px-5 py-2.5 font-mono text-xs">${r.drift_value.toFixed(4)}</td>
                    <td class="px-5 py-2.5 font-mono text-xs">${r.threshold.toFixed(4)}</td>
                    <td class="px-5 py-2.5">
                        <span class="inline-block w-3 h-3 rounded-full ${r.is_drifted ? 'bg-red-500' : 'bg-green-500'}"></span>
                        <span class="ml-1.5 text-xs ${this.driftStatusColor(r.is_drifted)}">${r.is_drifted ? 'Drifted' : 'OK'}</span>
                    </td>
                </tr>`)}
                </tbody>
            </table>`}`}
        </div>`;
    }

    /* ── Metrics Section ──────────────────────────────────────────────────── */

    private renderMetricsSection() {
        const m = this.selectedEndpointMetrics!;
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden mt-6">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Latency Metrics — ${m.deployment_name}</h2>
                <div class="flex gap-4 text-xs text-gray-500">
                    <span>Invocations: <strong>${m.total_invocations.toLocaleString()}</strong></span>
                    <span>Avg Latency: <strong>${m.avg_latency_ms.toFixed(1)}ms</strong></span>
                </div>
            </div>
            ${this.metricsLoading ? html`<div class="p-8 text-center text-gray-500">Loading metrics...</div>` : html`
            ${m.metrics.length === 0 ? html`<div class="p-8 text-center text-gray-500">No metrics data available.</div>` : html`
            <div class="p-4">
                <voyant-chart
                    type="line"
                    .data=${{
                        labels: m.metrics.map(pt => new Date(pt.timestamp).toLocaleTimeString()),
                        datasets: [
                            { name: 'p50', values: m.metrics.map(pt => pt.latency_p50) },
                            { name: 'p95', values: m.metrics.map(pt => pt.latency_p95) },
                            { name: 'p99', values: m.metrics.map(pt => pt.latency_p99) },
                        ],
                    }}
                    .options=${{ legend: { show: true }, yAxis: { type: 'value', name: 'ms' } }}
                    height="260px">
                </voyant-chart>
            </div>`}`}
        </div>`;
    }

    /* ── Detail Panel ─────────────────────────────────────────────────────── */

    private renderDetailPanel() {
        if (this.detailLoading) {
            return html`
            <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
                <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedModel = null; }}></div>
                <div class="relative w-[640px] bg-white h-full flex items-center justify-center shadow-2xl border-l border-gray-200">
                    <div class="text-gray-500" role="status">Loading model details...</div>
                </div>
            </div>`;
        }

        const model = this.selectedModel!;

        return html`
        <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Model: ${model.name}"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this.selectedModel = null; }}>
            <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedModel = null; }}></div>
            <div class="relative w-[640px] bg-white h-full overflow-y-auto shadow-2xl border-l border-gray-200" tabindex="-1">
                <div class="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between z-10">
                    <div>
                        <h2 class="font-bold text-lg">${model.name}</h2>
                        <div class="text-xs text-gray-500 mt-1">${model.versions.length} version(s)</div>
                    </div>
                    <button class="text-gray-500 hover:text-ink" @click=${() => { this.selectedModel = null; }}>✕</button>
                </div>

                <div class="p-6 space-y-6">
                    ${model.description ? html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-2">Description</h3>
                        <p class="text-sm text-gray-600">${model.description}</p>
                    </div>` : ''}

                    <!-- Versions Table -->
                    ${model.versions.length > 0 ? html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Versions</h3>
                        <div class="bg-white rounded-lg border border-gray-100 overflow-hidden">
                            <table class="w-full text-sm">
                                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                                    <th class="px-4 py-2.5">Version</th>
                                    <th class="px-4 py-2.5">Stage</th>
                                    <th class="px-4 py-2.5">Status</th>
                                    <th class="px-4 py-2.5">Metrics</th>
                                </tr></thead>
                                <tbody>
                                ${model.versions.map(v => html`
                                <tr class="border-b border-gray-50">
                                    <td class="px-4 py-2.5 font-mono font-semibold">v${v.version}</td>
                                    <td class="px-4 py-2.5">${this.stageBadge(v.stage)}</td>
                                    <td class="px-4 py-2.5 text-xs">${v.status}</td>
                                    <td class="px-4 py-2.5 text-xs font-mono max-w-[200px] truncate">${Object.keys(v.metrics || {}).length > 0 ? JSON.stringify(v.metrics) : '—'}</td>
                                </tr>`)}
                                </tbody>
                            </table>
                        </div>
                    </div>` : html`
                    <div class="text-sm text-gray-500 py-8 text-center">No versions available.</div>`}

                    <div class="flex gap-2 pt-4 border-t border-gray-100">
                        <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                            @click=${() => { this.selectedModel = null; }}>Close</button>
                    </div>
                </div>
            </div>
        </div>`;
    }
}
