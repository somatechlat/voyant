import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import { eventBus, type FilterEvent } from '../lib/event-bus';
import '../components/saas-sidebar';
import '../components/voyant-metric-card';
import '../components/voyant-chart';
import '../components/voyant-pivot-table';

@customElement('view-dashboard')
export class ViewDashboard extends LitElement {
    @state() overview: Record<string, unknown> = {};
    @state() jobs: Array<Record<string, unknown>> = [];
    @state() sources: Array<Record<string, unknown>> = [];
    @state() templates: Array<Record<string, unknown>> = [];
    @state() loading = true;
    @state() activeFilter: FilterEvent | null = null;

    private _unsub: Array<() => void> = [];

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();

        // Subscribe to cross-filter events (FR-5.4.2.3)
        this._unsub.push(
            eventBus.on('filter:apply', (data) => {
                this.activeFilter = data;
            }),
            eventBus.on('filter:clear', () => {
                this.activeFilter = null;
            }),
        );

        try {
            const [overview, jobs, sources, templates] = await Promise.all([
                api.get('/admin/dashboard').catch(() => ({})),
                api.get('/admin/jobs').catch(() => []),
                api.get('/admin/sources').catch(() => []),
                api.get('/admin/templates').catch(() => []),
            ]);
            this.overview = (overview as Record<string, unknown>) || {};
            this.jobs = (jobs as Array<Record<string, unknown>>) || [];
            this.sources = (sources as Array<Record<string, unknown>>) || [];
            this.templates = (templates as Array<Record<string, unknown>>) || [];
        } catch { /* empty */ }
        finally { this.loading = false; }
    }

    disconnectedCallback() {
        this._unsub.forEach(fn => fn());
        this._unsub = [];
        super.disconnectedCallback();
    }

    /**
     * Handle chart click → emit filter:apply to the event bus.
     */
    private _onChartClick(e: CustomEvent) {
        const detail = e.detail;
        if (!detail) return;
        eventBus.emit('filter:apply', {
            field: detail.field,
            value: detail.name,
            source: `chart:${detail.chartType}`,
        });
    }

    /**
     * Return filtered jobs when a cross-filter is active.
     */
    private _filteredJobs(): Array<Record<string, unknown>> {
        if (!this.activeFilter) return this.jobs;
        const { field, value } = this.activeFilter;
        return this.jobs.filter(j => String(j[field] ?? j.job_type ?? '') === String(value));
    }

    private _serviceEntries(): Array<{ name: string; healthy: boolean; details: string }> {
        const raw = this.overview.services;
        const list = Array.isArray(raw)
            ? raw
            : (raw && typeof raw === 'object' ? Object.values(raw as Record<string, unknown>) : []);
        if (!list.length) return [];
        return list.map((s) => {
            const svc = s as Record<string, unknown>;
            return {
                name: String(svc.name || 'unknown'),
                healthy: svc.status === 'healthy',
                details: String(svc.details || svc.circuit_breaker_state || ''),
            };
        });
    }

    private _sourceTypeDistribution(): Array<{ name: string; value: number }> {
        const counts: Record<string, number> = {};
        for (const s of this.sources) {
            const t = String(s.source_type || 'unknown');
            counts[t] = (counts[t] || 0) + 1;
        }
        return Object.entries(counts).map(([name, value]) => ({ name, value }));
    }

    private _jobTypeDistribution(): { labels: string[]; datasets: Array<{ name: string; values: number[] }> } {
        const counts: Record<string, number> = {};
        for (const j of this.jobs) {
            const t = String(j.job_type || 'other');
            counts[t] = (counts[t] || 0) + 1;
        }
        const labels = Object.keys(counts);
        const values = Object.values(counts);
        return { labels, datasets: [{ name: 'Jobs', values }] };
    }

    render() {
        const services = this._serviceEntries();
        const healthyCount = services.filter(s => s.healthy).length;
        const totalServices = services.length || 20;
        const version = String(this.overview.version || '3.0.0');
        const env = String(this.overview.env || 'local');
        const filteredJobs = this._filteredJobs();
        const filterActive = this.activeFilter !== null;

        return html`
        <saas-sidebar currentPath="/admin"></saas-sidebar>
        <main class="ml-60 min-h-screen" style="background:var(--saas-bg-page)" role="main" aria-label="Dashboard overview">
            <div style="padding:32px">
                <h1 style="font-size:28px;font-weight:900;font-family:Inter,system-ui,sans-serif;letter-spacing:-0.02em">Dashboard</h1>
                <p style="font-size:13px;color:var(--saas-text-secondary);margin-top:4px">VOYANT ${version} — ${env} environment</p>

                <!-- Cross-filter banner -->
                ${filterActive ? html`
                <div style="display:flex;align-items:center;gap:12px;margin-top:12px;padding:8px 16px;border-radius:8px;background:rgba(255,77,0,0.1);border:1px solid rgba(255,77,0,0.3);font-size:12px;color:#FF4D00">
                    <span>🔍 Filtered by: <strong>${this.activeFilter!.field}</strong> = <strong>${String(this.activeFilter!.value)}</strong> (from ${this.activeFilter!.source})</span>
                    <button @click=${() => eventBus.emit('filter:clear', {})}
                        style="margin-left:auto;padding:4px 12px;border-radius:6px;border:1px solid rgba(255,77,0,0.3);background:transparent;color:#FF4D00;font-size:11px;cursor:pointer">
                        ✕ Clear filter
                    </button>
                </div>` : ''}

                <!-- Metric Cards — from real API data -->
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin-top:24px" role="group" aria-label="Key metrics">
                    <voyant-metric-card label="Services" value="${healthyCount}/${totalServices}" icon="🟢" color="#22C55E" trend="${healthyCount === totalServices ? 'All healthy' : 'Degraded'}" trendDirection="${healthyCount === totalServices ? 'up' : 'down'}"></voyant-metric-card>
                    <voyant-metric-card label="Data Sources" value="${this.sources.length}" icon="🗄️" color="#3B82F6"></voyant-metric-card>
                    <voyant-metric-card label="Total Jobs" value="${filterActive ? filteredJobs.length : this.jobs.length}" icon="⚡" color="#FF4D00"></voyant-metric-card>
                    <voyant-metric-card label="Active Agents" value="${String(this.jobs.filter(j => j.status === 'running').length)}" icon="🤖" color="#8B5CF6" trend="Running now" trendDirection="up"></voyant-metric-card>
                    <voyant-metric-card label="Templates" value="${String(this.templates?.length ?? 51)}" icon="📋" color="#06B6D4" trend="14 categories" trendDirection="up"></voyant-metric-card>
                </div>

                <!-- Charts — click events wired to cross-filter bus (FR-5.4.2.3) -->
                <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-top:24px">
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px" role="figure" aria-label="Job distribution chart">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Job Distribution ${filterActive ? '(filtered)' : ''}</h3>
                        ${this.jobs.length > 0 ? html`
                        <voyant-chart type="bar" height="260px"
                            .data=${this._jobTypeDistribution()}
                            @chart:click=${this._onChartClick}>
                        </voyant-chart>
                        ` : html`
                        <div style="text-align:center;padding:60px;color:var(--saas-text-muted);font-size:12px">No jobs yet</div>
                        `}
                    </div>
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px" role="figure" aria-label="Source types distribution chart">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Source Types</h3>
                        ${this.sources.length > 0 ? html`
                        <voyant-chart type="pie" height="260px"
                            .data=${{ items: this._sourceTypeDistribution() }}
                            @chart:click=${this._onChartClick}>
                        </voyant-chart>
                        ` : html`
                        <div style="text-align:center;padding:60px;color:var(--saas-text-muted);font-size:12px">No sources configured</div>
                        `}
                    </div>
                </div>

                <!-- Pivot Table (FR-5.4.1.4) — Jobs by type × status -->
                <div style="margin-top:24px;background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px">
                    <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Pivot: Jobs by Type × Status</h3>
                    ${filteredJobs.length > 0 ? html`
                    <voyant-pivot-table
                        .data=${filteredJobs}
                        .rowFields=${['job_type']}
                        .columnFields=${['status']}
                        .valueFields=${[{ field: 'job_id', agg: 'count' }]}>
                    </voyant-pivot-table>
                    ` : html`
                    <div style="text-align:center;padding:40px;color:var(--saas-text-muted);font-size:12px">No data to pivot</div>
                    `}
                </div>

                <!-- Service Health + Recent Jobs — real data, with cross-filter -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:24px">
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px" role="region" aria-label="Service health status" aria-live="polite">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Service Health</h3>
                        <div style="display:flex;flex-direction:column;gap:6px;max-height:320px;overflow-y:auto" role="list" aria-label="Service health list">
                            ${services.length > 0 ? services.map(s => html`
                            <div style="display:flex;align-items:center;gap:8px;padding:6px 0;font-size:12px" role="listitem" aria-label="${s.name}: ${s.healthy ? 'healthy' : 'unhealthy'}">
                                <span class="voyant-status-dot ${s.healthy ? 'success' : 'danger'}"></span>
                                <span style="font-weight:500;flex:1">${s.name}</span>
                                <span style="color:var(--saas-text-muted);font-size:11px">${s.details}</span>
                            </div>`) : html`
                            <div style="text-align:center;padding:20px;color:var(--saas-text-muted);font-size:12px">Loading services...</div>
                            `}
                        </div>
                    </div>
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px" role="region" aria-label="Recent jobs" aria-live="polite">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Recent Jobs ${filterActive ? '(filtered)' : ''}</h3>
                        ${filteredJobs.length > 0 ? html`
                        <div style="display:flex;flex-direction:column;gap:6px;max-height:320px;overflow-y:auto" role="list" aria-label="Recent jobs list">
                            ${filteredJobs.slice(0, 10).map((j: Record<string, unknown>) => html`
                            <div style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:8px;border:1px solid var(--saas-border)" role="listitem" aria-label="Job ${j.job_type || 'Job'}: ${j.status || 'unknown'}">
                                <span class="voyant-status-dot ${j.status === 'succeeded' ? 'success' : j.status === 'running' ? 'warning' : 'danger'}"></span>
                                <div style="flex:1">
                                    <div style="font-size:12px;font-weight:500">${j.job_type || 'Job'}</div>
                                    <div style="font-size:11px;color:var(--saas-text-muted)">${String(j.job_id || '').slice(0, 8)}</div>
                                </div>
                                <span class="voyant-badge ${j.status === 'succeeded' ? 'voyant-badge-success' : j.status === 'running' ? 'voyant-badge-info' : 'voyant-badge-danger'}">${String(j.status || 'unknown')}</span>
                            </div>`)}
                        </div>` : html`
                        <div style="text-align:center;padding:40px;color:var(--saas-text-muted);font-size:12px">No recent jobs</div>
                        `}
                    </div>
                </div>
            </div>
        </main>`;
    }
}
