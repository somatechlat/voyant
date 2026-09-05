import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, type SystemOverview, type ServiceHealth } from '../lib/api';
import '../components/saas-sidebar';
import '../components/saas-stat-card';

@customElement('view-dashboard')
export class ViewDashboard extends LitElement {
    @state() data: SystemOverview | null = null;
    @state() loading = true;
    @state() error = '';

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.load();
    }

    async load() {
        this.loading = true;
        this.error = '';
        try {
            this.data = await api.get<SystemOverview>('/admin/dashboard');
        } catch (e: unknown) {
            this.error = e instanceof Error ? e.message : 'Failed to load dashboard';
        } finally {
            this.loading = false;
        }
    }

    private statusColor(status: string): string {
        if (status === 'healthy' || status === 'closed') return 'green';
        if (status === 'degraded' || status === 'half_open') return 'amber';
        if (status === 'down' || status === 'open') return 'red';
        return 'gray';
    }

    private formatUptime(seconds: number): string {
        if (seconds < 60) return `${seconds}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
        return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin" version="${this.data?.version || '3.0.0'}" env="${this.data?.env || ''}"></saas-sidebar>

        <main class="ml-60 min-h-screen bg-gray-50 p-8">
            <!-- Header -->
            <div class="flex items-center justify-between mb-8">
                <div>
                    <h1 class="text-2xl font-semibold text-gray-900">Dashboard</h1>
                    <p class="text-sm text-gray-500 mt-1">
                        System overview
                        ${this.data ? html` · Up ${this.formatUptime(this.data.uptime_seconds)} · ${this.data.env}` : ''}
                    </p>
                </div>
                <button
                    class="px-4 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                    @click=${() => this.load()}
                >
                    Refresh
                </button>
            </div>

            ${this.loading ? html`
            <div class="flex items-center justify-center h-64">
                <div class="text-gray-400">Loading...</div>
            </div>` : this.error ? html`
            <div class="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
                ${this.error}
            </div>` : this.data ? html`

            <!-- Stats Grid -->
            <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
                <saas-stat-card label="Total Jobs" value="${String(this.data.stats.total_jobs)}" icon="⚡" color="gray"></saas-stat-card>
                <saas-stat-card label="Running" value="${String(this.data.stats.jobs_running)}" icon="▶" color="blue"></saas-stat-card>
                <saas-stat-card label="Queued" value="${String(this.data.stats.jobs_queued)}" icon="⏳" color="amber"></saas-stat-card>
                <saas-stat-card label="Failed" value="${String(this.data.stats.jobs_failed)}" icon="✕" color="red"></saas-stat-card>
                <saas-stat-card label="Sources" value="${String(this.data.stats.sources_active)}/${String(this.data.stats.total_sources)}" icon="🗄" color="green"></saas-stat-card>
                <saas-stat-card label="Capsules" value="${String(this.data.stats.total_capsules)}" icon="📦" color="gray"></saas-stat-card>
                <saas-stat-card label="Tenants" value="${String(this.data.stats.total_tenants)}" icon="👥" color="blue" sub="${String(this.data.stats.active_tenants)} active"></saas-stat-card>
            </div>

            <!-- Service Health -->
            <div class="bg-white rounded-xl border border-gray-100 p-6 mb-8">
                <h2 class="text-lg font-semibold text-gray-900 mb-4">Service Health</h2>
                <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                    ${this.data.services.map((s: ServiceHealth) => html`
                    <div class="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:border-gray-200 transition-colors">
                        <div class="h-2.5 w-2.5 rounded-full ${
                            this.statusColor(s.status) === 'green' ? 'bg-green-500 shadow-[0_0_6px_#22c55e]' :
                            this.statusColor(s.status) === 'amber' ? 'bg-amber-500 shadow-[0_0_6px_#f59e0b]' :
                            this.statusColor(s.status) === 'red' ? 'bg-red-500 shadow-[0_0_6px_#ef4444]' :
                            'bg-gray-300'
                        }"></div>
                        <div>
                            <div class="text-sm font-medium text-gray-700">${s.name}</div>
                            <div class="text-xs text-gray-400">${s.details || s.status}</div>
                        </div>
                    </div>`)}
                </div>
            </div>

            <!-- Audit & Security -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-white rounded-xl border border-gray-100 p-6">
                    <h3 class="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">Audit Events (24h)</h3>
                    <div class="text-3xl font-semibold text-gray-900">${this.data.stats.audit_events_24h}</div>
                </div>
                <div class="bg-white rounded-xl border border-gray-100 p-6">
                    <h3 class="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">Policy Violations (24h)</h3>
                    <div class="text-3xl font-semibold ${this.data.stats.policy_violations_24h > 0 ? 'text-red-600' : 'text-gray-900'}">
                        ${this.data.stats.policy_violations_24h}
                    </div>
                </div>
            </div>
        ` : ''}</main>`;
    }
}
