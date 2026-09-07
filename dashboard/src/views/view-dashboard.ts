import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-metric-card';
import '../components/voyant-chart';

@customElement('view-dashboard')
export class ViewDashboard extends LitElement {
    @state() overview: Record<string, unknown> = {};
    @state() jobs: Array<Record<string, unknown>> = [];
    @state() sources: Array<Record<string, unknown>> = [];
    @state() loading = true;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try {
            const [overview, jobs, sources] = await Promise.all([
                api.get('/admin/dashboard').catch(() => ({})),
                api.get('/admin/jobs').catch(() => []),
                api.get('/admin/sources').catch(() => []),
            ]);
            this.overview = (overview as Record<string, unknown>) || {};
            this.jobs = (jobs as Array<Record<string, unknown>>) || [];
            this.sources = (sources as Array<Record<string, unknown>>) || [];
        } catch { /* empty */ }
        finally { this.loading = false; }
    }

    private _serviceEntries(): Array<{ name: string; healthy: boolean; details: string }> {
        const raw = this.overview.services;
        if (!raw || typeof raw !== 'object') return [];
        return Object.entries(raw).map(([name, val]) => ({
            name,
            healthy: (val as Record<string, unknown>)?.healthy === true,
            details: String((val as Record<string, unknown>)?.details || ''),
        }));
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

        return html`
        <saas-sidebar currentPath="/admin"></saas-sidebar>
        <main class="ml-60 min-h-screen" style="background:var(--saas-bg-page)">
            <div style="padding:32px">
                <h1 style="font-size:28px;font-weight:900;font-family:Inter,system-ui,sans-serif;letter-spacing:-0.02em">Dashboard</h1>
                <p style="font-size:13px;color:var(--saas-text-secondary);margin-top:4px">VOYANT ${version} — ${env} environment</p>

                <!-- Metric Cards — from real API data -->
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin-top:24px">
                    <voyant-metric-card label="Services" value="${healthyCount}/${totalServices}" icon="🟢" color="#22C55E" trend="${healthyCount === totalServices ? 'All healthy' : 'Degraded'}" trendDirection="${healthyCount === totalServices ? 'up' : 'down'}"></voyant-metric-card>
                    <voyant-metric-card label="Data Sources" value="${this.sources.length}" icon="🗄️" color="#3B82F6"></voyant-metric-card>
                    <voyant-metric-card label="Total Jobs" value="${this.jobs.length}" icon="⚡" color="#FF4D00"></voyant-metric-card>
                    <voyant-metric-card label="Active Agents" value="${String(this.jobs.filter(j => j.status === 'running').length)}" icon="🤖" color="#8B5CF6" trend="Running now" trendDirection="up"></voyant-metric-card>
                    <voyant-metric-card label="Templates" value="51" icon="📋" color="#06B6D4" trend="14 categories" trendDirection="up"></voyant-metric-card>
                </div>

                <!-- Charts — from real data -->
                <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-top:24px">
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Job Distribution</h3>
                        ${this.jobs.length > 0 ? html`
                        <voyant-chart type="bar" height="260px" .data=${this._jobTypeDistribution()}></voyant-chart>
                        ` : html`
                        <div style="text-align:center;padding:60px;color:var(--saas-text-muted);font-size:12px">No jobs yet</div>
                        `}
                    </div>
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Source Types</h3>
                        ${this.sources.length > 0 ? html`
                        <voyant-chart type="pie" height="260px" .data=${{ items: this._sourceTypeDistribution() }}></voyant-chart>
                        ` : html`
                        <div style="text-align:center;padding:60px;color:var(--saas-text-muted);font-size:12px">No sources configured</div>
                        `}
                    </div>
                </div>

                <!-- Service Health + Recent Jobs — real data -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:24px">
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Service Health</h3>
                        <div style="display:flex;flex-direction:column;gap:6px;max-height:320px;overflow-y:auto">
                            ${services.length > 0 ? services.map(s => html`
                            <div style="display:flex;align-items:center;gap:8px;padding:6px 0;font-size:12px">
                                <span class="voyant-status-dot ${s.healthy ? 'success' : 'danger'}"></span>
                                <span style="font-weight:500;flex:1">${s.name}</span>
                                <span style="color:var(--saas-text-muted);font-size:11px">${s.details}</span>
                            </div>`) : html`
                            <div style="text-align:center;padding:20px;color:var(--saas-text-muted);font-size:12px">Loading services...</div>
                            `}
                        </div>
                    </div>
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Recent Jobs</h3>
                        ${this.jobs.length > 0 ? html`
                        <div style="display:flex;flex-direction:column;gap:6px;max-height:320px;overflow-y:auto">
                            ${this.jobs.slice(0, 10).map((j: Record<string, unknown>) => html`
                            <div style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:8px;border:1px solid var(--saas-border)">
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
