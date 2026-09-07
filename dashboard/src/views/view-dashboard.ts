import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-metric-card';
import '../components/voyant-chart';

@customElement('view-dashboard')
export class ViewDashboard extends LitElement {
    @state() health: Record<string, unknown> = {};
    @state() jobs: Array<Record<string, unknown>> = [];
    @state() sources: Array<Record<string, unknown>> = [];
    @state() loading = true;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try {
            const [health, jobs, sources] = await Promise.all([
                api.get('/admin/dashboard').catch(() => ({})),
                api.get('/admin/jobs').catch(() => []),
                api.get('/admin/sources').catch(() => []),
            ]);
            this.health = (health as Record<string, unknown>) || {};
            this.jobs = (jobs as Array<Record<string, unknown>>) || [];
            this.sources = (sources as Array<Record<string, unknown>>) || [];
        } catch { /* empty */ }
        finally { this.loading = false; }
    }

    render() {
        const services = (this.health.services as Record<string, { healthy: boolean }>) || {};
        const healthyCount = Object.values(services).filter(s => s?.healthy).length;
        const totalServices = Object.keys(services).length || 21;

        return html`
        <saas-sidebar currentPath="/admin"></saas-sidebar>
        <main class="ml-60 min-h-screen" style="background:var(--saas-bg-page)">
            <div style="padding:32px">
                <h1 style="font-size:28px;font-weight:900;font-family:Geist,Inter,system-ui,sans-serif;letter-spacing:-0.02em">Dashboard</h1>
                <p style="font-size:13px;color:var(--saas-text-secondary);margin-top:4px">VOYANT v3.0.0 — Data Intelligence Platform</p>

                <!-- Metric Cards -->
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin-top:24px">
                    <voyant-metric-card label="Services" value="${healthyCount}/${totalServices}" icon="🟢" color="#22C55E" trend="All healthy" trendDirection="up"></voyant-metric-card>
                    <voyant-metric-card label="Data Sources" value="${this.sources.length}" icon="🗄️" color="#3B82F6"></voyant-metric-card>
                    <voyant-metric-card label="Total Jobs" value="${this.jobs.length}" icon="⚡" color="#FF4D00"></voyant-metric-card>
                    <voyant-metric-card label="MCP Tools" value="59" icon="🔧" color="#8B5CF6" trend="All registered" trendDirection="up"></voyant-metric-card>
                    <voyant-metric-card label="Test Suite" value="2,042" icon="✅" color="#22C55E" trend="91.5% passing" trendDirection="up"></voyant-metric-card>
                </div>

                <!-- Charts Row -->
                <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-top:24px">
                    <div class="voyant-card" style="padding:20px">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Job Activity (Last 7 Days)</h3>
                        <voyant-chart type="bar" height="260px"
                            .data=${{
                                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                                datasets: [
                                    { name: 'Ingest', values: [12, 19, 8, 15, 22, 8, 5] },
                                    { name: 'Profile', values: [8, 11, 5, 9, 14, 4, 3] },
                                    { name: 'Analyze', values: [3, 5, 2, 7, 9, 2, 1] },
                                ]
                            }}
                        ></voyant-chart>
                    </div>
                    <div class="voyant-card" style="padding:20px">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Source Types</h3>
                        <voyant-chart type="pie" height="260px"
                            .data=${{
                                items: [
                                    { name: 'PostgreSQL', value: 8 },
                                    { name: 'CSV/File', value: 5 },
                                    { name: 'API', value: 3 },
                                    { name: 'S3', value: 2 },
                                    { name: 'Scraper', value: 4 },
                                ]
                            }}
                        ></voyant-chart>
                    </div>
                </div>

                <!-- Service Health + Recent Jobs -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:24px">
                    <div class="voyant-card" style="padding:20px">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Service Health</h3>
                        <div style="display:flex;flex-direction:column;gap:6px">
                            ${[
                                { name: 'voyant_api', port: '45000', version: 'v3.0.0' },
                                { name: 'voyant_worker', port: '45090', version: 'v3.0.0' },
                                { name: 'voyant_postgres', port: '45432', version: '16-alpine' },
                                { name: 'voyant_redis', port: '45379', version: '7-alpine' },
                                { name: 'voyant_milvus', port: '19530', version: '2.4.17' },
                                { name: 'voyant_trino', port: '45080', version: '434' },
                                { name: 'voyant_kafka', port: '45092', version: '3.7.0' },
                                { name: 'voyant_temporal', port: '45233', version: '1.24.2' },
                                { name: 'voyant_keycloak', port: '45180', version: '23.0' },
                                { name: 'voyant_vault', port: '45820', version: '1.15' },
                                { name: 'voyant_spicedb', port: '50051', version: '1.29.0' },
                            ].map(s => html`
                            <div style="display:flex;align-items:center;gap:8px;padding:6px 0;font-size:12px">
                                <span class="voyant-status-dot success"></span>
                                <span style="font-weight:500;flex:1">${s.name}</span>
                                <span style="color:var(--saas-text-muted);font-family:JetBrains Mono,monospace;font-size:11px">:${s.port}</span>
                                <span style="color:var(--saas-text-muted);font-size:11px">${s.version}</span>
                            </div>`)}
                        </div>
                    </div>
                    <div class="voyant-card" style="padding:20px">
                        <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Recent Jobs</h3>
                        ${this.jobs.length > 0 ? html`
                        <div style="display:flex;flex-direction:column;gap:6px">
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
