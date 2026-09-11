import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-chart';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface Deployment {
    id: string;
    model_name: string;
    version: string;
    endpoint: string;
    status: 'healthy' | 'drifted' | 'critical';
    last_check: string;
    features_drifted_count: number;
    created_at: string;
}

interface FeatureDrift {
    feature_name: string;
    metric: 'KS' | 'PSI';
    value: number;
    threshold: number;
    status: 'green' | 'yellow' | 'red';
}

interface DriftAlert {
    id: string;
    timestamp: string;
    severity: 'info' | 'warning' | 'critical';
    message: string;
    feature?: string;
}

interface DriftDetail {
    deployment: Deployment;
    features: FeatureDrift[];
    prediction_distribution: {
        labels: string[];
        training: number[];
        current: number[];
    };
    latency: {
        labels: string[];
        p50: number[];
        p95: number[];
        p99: number[];
    };
    alerts: DriftAlert[];
}

interface DriftSummary {
    total_deployments: number;
    models_with_drift: number;
    healthy_models: number;
    alerts_24h: number;
}

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-drift')
export class ViewDrift extends LitElement {
    @state() deployments: Deployment[] = [];
    @state() summary: DriftSummary = { total_deployments: 0, models_with_drift: 0, healthy_models: 0, alerts_24h: 0 };
    @state() loading = true;

    // Detail panel
    @state() selectedDeployment: DriftDetail | null = null;
    @state() detailLoading = false;

    // Acknowledge state
    @state() acknowledgingId: string | null = null;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadData();
    }

    /* ── Data Loading ─────────────────────────────────────────────────────── */

    async loadData() {
        this.loading = true;
        try {
            const deps = await api.get<Deployment[]>('/ml/deployments');
            this.deployments = deps;
            this.summary = {
                total_deployments: deps.length,
                models_with_drift: deps.filter(d => d.status === 'drifted' || d.status === 'critical').length,
                healthy_models: deps.filter(d => d.status === 'healthy').length,
                alerts_24h: deps.reduce((sum, d) => sum + d.features_drifted_count, 0), // approximated; real count from alerts endpoint
            };
        } catch {
            this.deployments = [];
        } finally {
            this.loading = false;
        }
    }

    async loadDriftDetail(deploymentId: string) {
        this.detailLoading = true;
        try {
            const [driftData, metricsData] = await Promise.all([
                api.get<Record<string, unknown>>(`/ml/deployments/${deploymentId}/drift`),
                api.get<Record<string, unknown>>(`/ml/deployments/${deploymentId}/metrics`),
            ]);

            const dep = this.deployments.find(d => d.id === deploymentId);

            this.selectedDeployment = {
                deployment: dep || (driftData.deployment as Deployment),
                features: (driftData.features as FeatureDrift[]) || [],
                prediction_distribution: (driftData.prediction_distribution as DriftDetail['prediction_distribution']) || { labels: [], training: [], current: [] },
                latency: (metricsData.latency as DriftDetail['latency']) || { labels: [], p50: [], p95: [], p99: [] },
                alerts: (driftData.alerts as DriftAlert[]) || [],
            };
        } catch {
            this.selectedDeployment = null;
        } finally {
            this.detailLoading = false;
        }
    }

    async acknowledgeDrift(deploymentId: string) {
        this.acknowledgingId = deploymentId;
        try {
            await api.post(`/ml/deployments/${deploymentId}/drift/acknowledge`, {});
            await this.loadData();
            if (this.selectedDeployment?.deployment.id === deploymentId) {
                this.selectedDeployment = null;
            }
        } catch { /* empty */ } finally {
            this.acknowledgingId = null;
        }
    }

    /* ── Helpers ──────────────────────────────────────────────────────────── */

    private statusBadge(s: string) {
        const colors: Record<string, string> = {
            healthy: 'bg-green-50 text-green-700 border-green-200',
            drifted: 'bg-amber-50 text-amber-700 border-amber-200',
            critical: 'bg-red-50 text-red-700 border-red-200',
        };
        const dot: Record<string, string> = {
            healthy: 'bg-green-500',
            drifted: 'bg-amber-500',
            critical: 'bg-red-500',
        };
        return html`
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-medium rounded-full border ${colors[s] || colors.healthy}">
                <span class="inline-block w-1.5 h-1.5 rounded-full ${dot[s] || dot.healthy}"></span>
                ${s}
            </span>`;
    }

    private severityBadge(s: string) {
        const colors: Record<string, string> = {
            info: 'bg-blue-50 text-blue-700 border-blue-200',
            warning: 'bg-amber-50 text-amber-700 border-amber-200',
            critical: 'bg-red-50 text-red-700 border-red-200',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[s] || colors.info}">${s}</span>`;
    }

    private driftStatusBar(status: string, value: number, threshold: number) {
        const pct = Math.min(100, Math.round((value / Math.max(threshold * 2, value)) * 100));
        const color = status === 'green' ? 'bg-green-500' : status === 'yellow' ? 'bg-amber-500' : 'bg-red-500';
        return html`
            <div class="flex items-center gap-2">
                <div class="w-24 bg-gray-100 rounded-full h-1.5">
                    <div class="${color} h-1.5 rounded-full transition-all" style="width:${pct}%"></div>
                </div>
                <span class="text-xs font-mono text-gray-500">${value.toFixed(3)} / ${threshold.toFixed(3)}</span>
            </div>`;
    }

    /* ── Render ───────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/drift"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Model Drift Monitoring">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Model Drift Monitoring</h1>
                    <p class="text-sm text-gray-500 mt-1">Track feature drift, prediction distribution shifts, and model health</p>
                </div>
                <button class="px-4 py-1.5 text-sm font-semibold border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors flex items-center gap-2"
                    aria-label="Refresh drift data" @click=${() => this.loadData()}>
                    <svg class="w-4 h-4 ${this.loading ? 'animate-spin' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
                        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                    </svg>
                    Refresh
                </button>
            </div>

            ${this.loading ? html`<div class="text-center text-gray-500 py-16" role="status" aria-live="polite">Loading deployments...</div>` : ''}

            ${!this.loading ? html`
            <!-- Summary Cards -->
            ${this.renderSummaryCards()}

            <!-- Drift Overview Table -->
            ${this.renderOverviewTable()}
            ` : ''}

            <!-- Detail Panel (slide-in) -->
            ${this.selectedDeployment || this.detailLoading ? this.renderDetailPanel() : ''}
        </main>`;
    }

    /* ── Summary Cards ────────────────────────────────────────────────────── */

    private renderSummaryCards() {
        const cards = [
            { label: 'Total Deployments Monitored', value: this.summary.total_deployments, icon: 'grid', color: 'text-gray-900', bg: 'bg-white' },
            { label: 'Models with Drift', value: this.summary.models_with_drift, icon: 'alert', color: this.summary.models_with_drift > 0 ? 'text-amber-600' : 'text-green-600', bg: this.summary.models_with_drift > 0 ? 'bg-amber-50' : 'bg-green-50' },
            { label: 'Healthy Models', value: this.summary.healthy_models, icon: 'check', color: 'text-green-600', bg: 'bg-green-50' },
            { label: 'Alerts (24h)', value: this.summary.alerts_24h, icon: 'bell', color: this.summary.alerts_24h > 0 ? 'text-red-600' : 'text-gray-500', bg: this.summary.alerts_24h > 0 ? 'bg-red-50' : 'bg-white' },
        ];

        return html`
        <div class="grid grid-cols-4 gap-4 mb-6">
            ${cards.map(c => html`
            <div class="bg-white rounded-xl border border-gray-100 p-5 flex items-start justify-between">
                <div>
                    <div class="text-xs font-medium text-gray-500 uppercase tracking-wider">${c.label}</div>
                    <div class="text-3xl font-black font-display mt-2 ${c.color}">${c.value}</div>
                </div>
                <div class="h-10 w-10 rounded-lg ${c.bg} flex items-center justify-center">
                    ${c.icon === 'grid' ? html`<svg class="h-5 w-5 ${c.color}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>` : ''}
                    ${c.icon === 'alert' ? html`<svg class="h-5 w-5 ${c.color}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>` : ''}
                    ${c.icon === 'check' ? html`<svg class="h-5 w-5 ${c.color}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>` : ''}
                    ${c.icon === 'bell' ? html`<svg class="h-5 w-5 ${c.color}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>` : ''}
                </div>
            </div>`)}
        </div>`;
    }

    /* ── Overview Table ────────────────────────────────────────────────────── */

    private renderOverviewTable() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Drift Overview</h2>
                <span class="text-xs text-gray-500">${this.deployments.length} deployments</span>
            </div>
            <table class="w-full text-sm" role="table" aria-label="Drift overview">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">Model Name</th>
                    <th class="px-5 py-3">Version</th>
                    <th class="px-5 py-3">Endpoint</th>
                    <th class="px-5 py-3">Status</th>
                    <th class="px-5 py-3">Last Check</th>
                    <th class="px-5 py-3">Features Drifted</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.deployments.length === 0 ? html`
                <tr><td colspan="7" class="px-5 py-16 text-center text-gray-500">
                    <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
                        <svg class="w-7 h-7 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    </div>
                    <div class="text-sm font-semibold text-gray-600">No deployments found</div>
                    <div class="text-xs mt-2 text-gray-500">ML deployments will appear here once models are deployed for monitoring.</div>
                </td></tr>` : ''}
                ${this.deployments.map(d => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                    role="button" tabindex="0"
                    aria-label="Deployment: ${d.model_name} ${d.version}"
                    @click=${() => this.loadDriftDetail(d.id)}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.loadDriftDetail(d.id); } }}>
                    <td class="px-5 py-3">
                        <div class="font-semibold">${d.model_name}</div>
                    </td>
                    <td class="px-5 py-3">
                        <span class="px-2 py-0.5 text-xs bg-gray-100 rounded font-mono">${d.version}</span>
                    </td>
                    <td class="px-5 py-3">
                        <span class="text-xs font-mono text-gray-500 truncate max-w-[200px] inline-block">${d.endpoint}</span>
                    </td>
                    <td class="px-5 py-3">${this.statusBadge(d.status)}</td>
                    <td class="px-5 py-3 text-xs text-gray-500">${d.last_check ? new Date(d.last_check).toLocaleString() : '—'}</td>
                    <td class="px-5 py-3">
                        <span class="text-sm font-semibold ${d.features_drifted_count > 0 ? 'text-amber-600' : 'text-gray-500'}">${d.features_drifted_count}</span>
                    </td>
                    <td class="px-5 py-3" @click=${(e: Event) => e.stopPropagation()}>
                        <div class="flex gap-2">
                            <button class="text-xs text-blue-600 hover:underline"
                                aria-label="View drift details for ${d.model_name}"
                                @click=${() => this.loadDriftDetail(d.id)}>View Details</button>
                            ${d.status !== 'healthy' ? html`
                            <button class="text-xs text-amber-600 hover:underline ${this.acknowledgingId === d.id ? 'opacity-50' : ''}"
                                ?disabled=${this.acknowledgingId === d.id}
                                aria-label="Acknowledge drift for ${d.model_name}"
                                @click=${() => this.acknowledgeDrift(d.id)}>
                                ${this.acknowledgingId === d.id ? 'Ack...' : 'Acknowledge'}
                            </button>` : ''}
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
            <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Loading drift details">
                <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedDeployment = null; }}></div>
                <div class="relative w-[720px] bg-white h-full flex items-center justify-center shadow-2xl border-l border-gray-200">
                    <div class="text-gray-500" role="status" aria-live="polite">Loading drift details...</div>
                </div>
            </div>`;
        }

        const detail = this.selectedDeployment!;
        const dep = detail.deployment;

        return html`
        <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Drift detail: ${dep.model_name}"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') { this.selectedDeployment = null; } }}>
            <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedDeployment = null; }}></div>
            <div class="relative w-[720px] bg-white h-full overflow-y-auto shadow-2xl border-l border-gray-200" tabindex="-1">
                <!-- Header -->
                <div class="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between z-10">
                    <div>
                        <h2 class="font-bold text-lg">${dep.model_name}</h2>
                        <div class="flex items-center gap-2 mt-1">
                            ${this.statusBadge(dep.status)}
                            <span class="text-xs text-gray-500 font-mono">${dep.version}</span>
                            <span class="text-xs text-gray-500 font-mono">${dep.endpoint}</span>
                        </div>
                    </div>
                    <button class="text-gray-500 hover:text-ink" aria-label="Close drift detail" @click=${() => { this.selectedDeployment = null; }}>✕</button>
                </div>

                <div class="p-6 space-y-8">
                    <!-- Model Info Summary -->
                    <div class="grid grid-cols-3 gap-4">
                        <div class="p-3 bg-gray-50 rounded-lg">
                            <div class="text-xs text-gray-500">Last Check</div>
                            <div class="text-sm font-semibold mt-1">${dep.last_check ? new Date(dep.last_check).toLocaleString() : '—'}</div>
                        </div>
                        <div class="p-3 bg-gray-50 rounded-lg">
                            <div class="text-xs text-gray-500">Features Drifted</div>
                            <div class="text-sm font-semibold mt-1 ${dep.features_drifted_count > 0 ? 'text-amber-600' : ''}">${dep.features_drifted_count}</div>
                        </div>
                        <div class="p-3 bg-gray-50 rounded-lg">
                            <div class="text-xs text-gray-500">Status</div>
                            <div class="mt-1">${this.statusBadge(dep.status)}</div>
                        </div>
                    </div>

                    <!-- Feature Drift Table -->
                    ${detail.features.length > 0 ? html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Feature Drift</h3>
                        <div class="bg-white rounded-lg border border-gray-100 overflow-hidden">
                            <table class="w-full text-sm" role="table" aria-label="Feature drift details">
                                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                                    <th class="px-4 py-2.5">Feature Name</th>
                                    <th class="px-4 py-2.5">Metric</th>
                                    <th class="px-4 py-2.5">Value</th>
                                    <th class="px-4 py-2.5">Threshold</th>
                                    <th class="px-4 py-2.5">Status</th>
                                </tr></thead>
                                <tbody>
                                ${detail.features.map(f => html`
                                <tr class="border-b border-gray-50">
                                    <td class="px-4 py-2.5 font-medium">${f.feature_name}</td>
                                    <td class="px-4 py-2.5"><span class="px-1.5 py-0.5 text-xs bg-gray-100 rounded font-mono">${f.metric}</span></td>
                                    <td class="px-4 py-2.5 font-mono text-xs">${f.value.toFixed(4)}</td>
                                    <td class="px-4 py-2.5 font-mono text-xs">${f.threshold.toFixed(4)}</td>
                                    <td class="px-4 py-2.5">${this.driftStatusBar(f.status, f.value, f.threshold)}</td>
                                </tr>`)}
                                </tbody>
                            </table>
                        </div>
                    </div>` : html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Feature Drift</h3>
                        <div class="text-sm text-gray-500 py-8 text-center">No feature drift data available</div>
                    </div>`}

                    <!-- Prediction Distribution Chart -->
                    ${detail.prediction_distribution.labels.length > 0 ? html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Prediction Distribution</h3>
                        <div class="bg-white rounded-lg border border-gray-100 p-4">
                            <div class="text-xs text-gray-500 mb-2">Training vs Current distribution comparison</div>
                            <voyant-chart
                                type="bar"
                                .data=${{
                                    labels: detail.prediction_distribution.labels,
                                    datasets: [
                                        { name: 'Training', values: detail.prediction_distribution.training },
                                        { name: 'Current', values: detail.prediction_distribution.current },
                                    ],
                                }}
                                .options=${{ legend: { show: true } }}
                                height="280px">
                            </voyant-chart>
                        </div>
                    </div>` : ''}

                    <!-- Latency Chart -->
                    ${detail.latency.labels.length > 0 ? html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Latency Over Time</h3>
                        <div class="bg-white rounded-lg border border-gray-100 p-4">
                            <div class="text-xs text-gray-500 mb-2">p50 / p95 / p99 response latency</div>
                            <voyant-chart
                                type="line"
                                .data=${{
                                    labels: detail.latency.labels,
                                    datasets: [
                                        { name: 'p50', values: detail.latency.p50 },
                                        { name: 'p95', values: detail.latency.p95 },
                                        { name: 'p99', values: detail.latency.p99 },
                                    ],
                                }}
                                .options=${{
                                    legend: { show: true },
                                    yAxis: {
                                        type: 'value',
                                        name: 'ms',
                                        splitLine: { lineStyle: { color: '#1A1A1A' } },
                                        axisLabel: { color: '#9CA3AF' },
                                    },
                                }}
                                height="260px">
                            </voyant-chart>
                        </div>
                    </div>` : ''}

                    <!-- Alert History -->
                    ${detail.alerts.length > 0 ? html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Alert History</h3>
                        <div class="space-y-2">
                            ${detail.alerts.map(a => html`
                            <div class="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                                <div class="flex-shrink-0 mt-0.5">${this.severityBadge(a.severity)}</div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-sm text-gray-700">${a.message}</div>
                                    <div class="flex items-center gap-2 mt-1">
                                        <span class="text-xs text-gray-500">${new Date(a.timestamp).toLocaleString()}</span>
                                        ${a.feature ? html`<span class="text-xs font-mono text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">${a.feature}</span>` : ''}
                                    </div>
                                </div>
                            </div>`)}
                        </div>
                    </div>` : html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Alert History</h3>
                        <div class="text-sm text-gray-500 py-8 text-center">No alerts recorded</div>
                    </div>`}

                    <!-- Actions Footer -->
                    <div class="flex gap-2 pt-4 border-t border-gray-100">
                        ${dep.status !== 'healthy' ? html`
                        <button class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                            aria-label="Acknowledge drift for ${dep.model_name}"
                            @click=${() => this.acknowledgeDrift(dep.id)}>
                            Acknowledge Drift
                        </button>` : ''}
                        <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                            @click=${() => { this.selectedDeployment = null; }}>
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    }
}
