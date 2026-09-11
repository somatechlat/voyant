import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface AlertRule {
    id: string;
    name: string;
    description: string;
    condition: { metric: string; operator: string; threshold: number; labels?: Record<string, string> };
    severity: string;
    channels: Array<{ type: string; target?: string; url?: string }>;
    status: string;
    enabled: boolean;
    cooldown_seconds: number;
    labels: Record<string, unknown>;
    fire_count: number;
    last_evaluated_at: string | null;
    last_fired_at: string | null;
    created_by: string;
    created_at: string;
    updated_at: string;
}

interface AlertNotification {
    id: string;
    rule_id: string;
    rule_name: string;
    severity: string;
    message: string;
    status: string;
    metric_value: number | null;
    threshold: number | null;
    labels: Record<string, unknown>;
    context: Record<string, unknown>;
    acknowledged_by: string;
    acknowledged_at: string | null;
    resolved_at: string | null;
    channel_results: Array<Record<string, unknown>>;
    created_at: string;
}

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-alerting')
export class ViewAlerting extends LitElement {
    @state() rules: AlertRule[] = [];
    @state() notifications: AlertNotification[] = [];
    @state() loading = true;
    @state() error: string | null = null;

    // Create modal
    @state() showCreateModal = false;
    @state() createForm = {
        name: '', description: '', severity: 'warning',
        metric: '', operator: '>', threshold: 0,
        channel_type: 'log', channel_target: '',
        enabled: true, cooldown_seconds: 300,
    };
    @state() creating = false;

    // Ack state
    @state() acknowledgingId: string | null = null;

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
            const [rulesResp, notifsResp] = await Promise.all([
                api.get<{ rules: AlertRule[]; total: number }>('/alerting/rules'),
                api.get<{ notifications: AlertNotification[]; total: number }>('/alerting/notifications'),
            ]);
            this.rules = rulesResp.rules || [];
            this.notifications = notifsResp.notifications || [];
        } catch (e) {
            this.error = e instanceof Error ? e.message : 'Failed to load alerting data';
            this.rules = [];
            this.notifications = [];
        } finally {
            this.loading = false;
        }
    }

    async createRule() {
        this.creating = true;
        try {
            const channels = [];
            if (this.createForm.channel_type === 'webhook' && this.createForm.channel_target) {
                channels.push({ type: 'webhook', url: this.createForm.channel_target });
            } else if (this.createForm.channel_type === 'email' && this.createForm.channel_target) {
                channels.push({ type: 'email', target: this.createForm.channel_target });
            } else {
                channels.push({ type: 'log' });
            }

            await api.post('/alerting/rules', {
                name: this.createForm.name,
                description: this.createForm.description,
                severity: this.createForm.severity,
                condition: {
                    metric: this.createForm.metric,
                    operator: this.createForm.operator,
                    threshold: this.createForm.threshold,
                },
                channels,
                enabled: this.createForm.enabled,
                cooldown_seconds: this.createForm.cooldown_seconds,
            });
            this.showCreateModal = false;
            this.createForm = {
                name: '', description: '', severity: 'warning',
                metric: '', operator: '>', threshold: 0,
                channel_type: 'log', channel_target: '',
                enabled: true, cooldown_seconds: 300,
            };
            await this.loadData();
        } catch { /* empty */ } finally {
            this.creating = false;
        }
    }

    async acknowledgeNotification(notifId: string) {
        this.acknowledgingId = notifId;
        try {
            await api.post(`/alerting/notifications/${notifId}/acknowledge`, { acknowledged_by: 'admin' });
            await this.loadData();
        } catch { /* empty */ } finally {
            this.acknowledgingId = null;
        }
    }

    async toggleRule(rule: AlertRule) {
        try {
            await api.put(`/alerting/rules/${rule.id}`, { enabled: !rule.enabled });
            await this.loadData();
        } catch { /* empty */ }
    }

    async deleteRule(ruleId: string) {
        try {
            await api.del(`/alerting/rules/${ruleId}`);
            await this.loadData();
        } catch { /* empty */ }
    }

    /* ── Helpers ──────────────────────────────────────────────────────────── */

    private severityBadge(s: string) {
        const colors: Record<string, string> = {
            info: 'bg-blue-50 text-blue-700 border-blue-200',
            warning: 'bg-amber-50 text-amber-700 border-amber-200',
            error: 'bg-red-50 text-red-700 border-red-200',
            critical: 'bg-red-100 text-red-800 border-red-300',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[s] || colors.info}">${s}</span>`;
    }

    private notifStatusBadge(s: string) {
        const colors: Record<string, string> = {
            firing: 'bg-red-50 text-red-700 border-red-200',
            acknowledged: 'bg-amber-50 text-amber-700 border-amber-200',
            resolved: 'bg-green-50 text-green-700 border-green-200',
            silenced: 'bg-gray-50 text-gray-500 border-gray-200',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[s] || 'bg-gray-50 text-gray-700 border-gray-200'}">${s}</span>`;
    }

    private conditionText(condition: AlertRule['condition']): string {
        if (!condition || !condition.metric) return '—';
        return `${condition.metric} ${condition.operator} ${condition.threshold}`;
    }

    private channelText(channels: AlertRule['channels']): string {
        if (!channels || channels.length === 0) return 'log';
        return channels.map(c => c.type).join(', ');
    }

    /* ── Render ───────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/alerting"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Alert Rules">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Alert Rules</h1>
                    <p class="text-sm text-gray-500 mt-1">Define alerting conditions, manage notification channels, and track alerts</p>
                </div>
                <div class="flex gap-2">
                    <button class="px-4 py-1.5 text-sm font-semibold border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors flex items-center gap-2"
                        @click=${() => this.loadData()}>
                        <svg class="w-4 h-4 ${this.loading ? 'animate-spin' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                        Refresh
                    </button>
                    <button class="px-4 py-1.5 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
                        @click=${() => { this.showCreateModal = true; }}>
                        + Create Rule
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
                <div class="text-sm text-gray-500">Loading alert rules and notifications...</div>
            </div>` : html`
            <!-- Rules Table -->
            ${this.renderRulesTable()}

            <!-- Notifications Table -->
            ${this.renderNotificationsTable()}
            `}

            <!-- Create Modal -->
            ${this.showCreateModal ? this.renderCreateModal() : ''}
        </main>`;
    }

    /* ── Rules Table ──────────────────────────────────────────────────────── */

    private renderRulesTable() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden mb-6" aria-live="polite">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Rules</h2>
                <span class="text-xs text-gray-500">${this.rules.length} rules</span>
            </div>
            <table class="w-full text-sm" role="table" aria-label="Alert rules">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">Name</th>
                    <th class="px-5 py-3">Severity</th>
                    <th class="px-5 py-3">Condition</th>
                    <th class="px-5 py-3">Channels</th>
                    <th class="px-5 py-3">Enabled</th>
                    <th class="px-5 py-3">Fires</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.rules.length === 0 ? html`
                <tr><td colspan="7" class="px-5 py-16 text-center text-gray-500">
                    <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
                        <svg class="w-7 h-7 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
                    </div>
                    <div class="text-sm font-semibold text-gray-600">No alert rules configured</div>
                    <div class="text-xs mt-2 text-gray-500">Create a rule to start monitoring metrics and receiving alerts.</div>
                </td></tr>` : ''}
                ${this.rules.map(r => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50">
                    <td class="px-5 py-3">
                        <div class="font-semibold">${r.name}</div>
                        ${r.description ? html`<div class="text-xs text-gray-500 mt-0.5 truncate max-w-[250px]">${r.description}</div>` : ''}
                    </td>
                    <td class="px-5 py-3">${this.severityBadge(r.severity)}</td>
                    <td class="px-5 py-3">
                        <span class="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded">${this.conditionText(r.condition)}</span>
                    </td>
                    <td class="px-5 py-3 text-xs text-gray-500">${this.channelText(r.channels)}</td>
                    <td class="px-5 py-3">
                        <button class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${r.enabled ? 'bg-green-500' : 'bg-gray-300'}"
                            role="switch" aria-checked="${r.enabled}" aria-label="Toggle rule ${r.name}"
                            @click=${() => this.toggleRule(r)}>
                            <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${r.enabled ? 'translate-x-4' : 'translate-x-0.5'}"></span>
                        </button>
                    </td>
                    <td class="px-5 py-3">
                        <span class="text-sm font-semibold ${r.fire_count > 0 ? 'text-amber-600' : 'text-gray-500'}">${r.fire_count}</span>
                    </td>
                    <td class="px-5 py-3">
                        <div class="flex gap-2">
                            <button class="text-xs text-red-600 hover:underline"
                                @click=${() => this.deleteRule(r.id)}>Delete</button>
                        </div>
                    </td>
                </tr>`)}
                </tbody>
            </table>
        </div>`;
    }

    /* ── Notifications Table ──────────────────────────────────────────────── */

    private renderNotificationsTable() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Notifications</h2>
                <span class="text-xs text-gray-500">${this.notifications.length} notifications</span>
            </div>
            <table class="w-full text-sm" role="table" aria-label="Alert notifications">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">Rule</th>
                    <th class="px-5 py-3">Severity</th>
                    <th class="px-5 py-3">Message</th>
                    <th class="px-5 py-3">Status</th>
                    <th class="px-5 py-3">Acknowledged</th>
                    <th class="px-5 py-3">Time</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.notifications.length === 0 ? html`
                <tr><td colspan="7" class="px-5 py-12 text-center text-gray-500">
                    <div class="text-sm font-semibold text-gray-600">No notifications</div>
                    <div class="text-xs mt-1 text-gray-500">Alert notifications will appear here when rules fire.</div>
                </td></tr>` : ''}
                ${this.notifications.map(n => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50">
                    <td class="px-5 py-3 font-semibold">${n.rule_name || '—'}</td>
                    <td class="px-5 py-3">${this.severityBadge(n.severity)}</td>
                    <td class="px-5 py-3 text-xs truncate max-w-[300px]">${n.message}</td>
                    <td class="px-5 py-3">${this.notifStatusBadge(n.status)}</td>
                    <td class="px-5 py-3 text-xs text-gray-500">
                        ${n.acknowledged_by ? html`
                        <div>${n.acknowledged_by}</div>
                        <div class="text-gray-500">${n.acknowledged_at ? new Date(n.acknowledged_at).toLocaleString() : ''}</div>` : '—'}
                    </td>
                    <td class="px-5 py-3 text-xs text-gray-500">${new Date(n.created_at).toLocaleString()}</td>
                    <td class="px-5 py-3">
                        ${n.status === 'firing' ? html`
                        <button class="text-xs text-blue-600 hover:underline ${this.acknowledgingId === n.id ? 'opacity-50' : ''}"
                            ?disabled=${this.acknowledgingId === n.id}
                            @click=${() => this.acknowledgeNotification(n.id)}>
                            ${this.acknowledgingId === n.id ? 'Ack...' : 'Acknowledge'}
                        </button>` : '—'}
                    </td>
                </tr>`)}
                </tbody>
            </table>
        </div>`;
    }

    /* ── Create Modal ─────────────────────────────────────────────────────── */

    private renderCreateModal() {
        return html`
        <div class="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Create alert rule"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this.showCreateModal = false; }}>
            <div class="absolute inset-0 bg-black/30" @click=${() => { this.showCreateModal = false; }}></div>
            <div class="relative bg-white rounded-2xl shadow-2xl w-[560px] max-h-[85vh] overflow-y-auto" tabindex="-1">
                <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                    <h2 class="font-bold text-lg">Create Alert Rule</h2>
                    <button class="text-gray-500 hover:text-ink" @click=${() => { this.showCreateModal = false; }}>✕</button>
                </div>
                <div class="p-6 space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Name *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="e.g. High Error Rate"
                            .value=${this.createForm.name}
                            @input=${(e: Event) => { this.createForm = { ...this.createForm, name: (e.target as HTMLInputElement).value }; }}>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Description</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="What this rule monitors"
                            .value=${this.createForm.description}
                            @input=${(e: Event) => { this.createForm = { ...this.createForm, description: (e.target as HTMLInputElement).value }; }}>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Severity</label>
                        <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            .value=${this.createForm.severity}
                            @change=${(e: Event) => { this.createForm = { ...this.createForm, severity: (e.target as HTMLSelectElement).value }; }}>
                            <option value="info">Info</option>
                            <option value="warning">Warning</option>
                            <option value="error">Error</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>

                    <div class="border-t border-gray-100 pt-4">
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Condition</h3>
                        <div class="grid grid-cols-3 gap-3">
                            <div>
                                <label class="block text-xs text-gray-600 mb-1">Metric *</label>
                                <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono"
                                    placeholder="voyant_jobs_failed"
                                    .value=${this.createForm.metric}
                                    @input=${(e: Event) => { this.createForm = { ...this.createForm, metric: (e.target as HTMLInputElement).value }; }}>
                            </div>
                            <div>
                                <label class="block text-xs text-gray-600 mb-1">Operator</label>
                                <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                                    .value=${this.createForm.operator}
                                    @change=${(e: Event) => { this.createForm = { ...this.createForm, operator: (e.target as HTMLSelectElement).value }; }}>
                                    <option value=">">&gt; greater than</option>
                                    <option value=">=">&ge; greater or equal</option>
                                    <option value="<">&lt; less than</option>
                                    <option value="<=">&le; less or equal</option>
                                    <option value="==">== equal</option>
                                    <option value="!=">!= not equal</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-xs text-gray-600 mb-1">Threshold *</label>
                                <input type="number" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                                    .value=${String(this.createForm.threshold)}
                                    @input=${(e: Event) => { this.createForm = { ...this.createForm, threshold: parseFloat((e.target as HTMLInputElement).value) || 0 }; }}>
                            </div>
                        </div>
                    </div>

                    <div class="border-t border-gray-100 pt-4">
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Notification Channel</h3>
                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="block text-xs text-gray-600 mb-1">Channel Type</label>
                                <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                                    .value=${this.createForm.channel_type}
                                    @change=${(e: Event) => { this.createForm = { ...this.createForm, channel_type: (e.target as HTMLSelectElement).value }; }}>
                                    <option value="log">Log</option>
                                    <option value="email">Email</option>
                                    <option value="webhook">Webhook</option>
                                </select>
                            </div>
                            ${this.createForm.channel_type !== 'log' ? html`
                            <div>
                                <label class="block text-xs text-gray-600 mb-1">Target</label>
                                <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                                    placeholder="${this.createForm.channel_type === 'email' ? 'ops@company.com' : 'https://hooks.example.com/alert'}"
                                    .value=${this.createForm.channel_target}
                                    @input=${(e: Event) => { this.createForm = { ...this.createForm, channel_target: (e.target as HTMLInputElement).value }; }}>
                            </div>` : ''}
                        </div>
                    </div>

                    <div class="flex gap-6 pt-2">
                        <label class="flex items-center gap-2 text-sm cursor-pointer">
                            <input type="checkbox" .checked=${this.createForm.enabled}
                                @change=${(e: Event) => { this.createForm = { ...this.createForm, enabled: (e.target as HTMLInputElement).checked }; }}>
                            Enabled
                        </label>
                        <div class="flex items-center gap-2">
                            <label class="text-xs text-gray-600">Cooldown (s)</label>
                            <input type="number" class="w-20 px-2 py-1 text-sm border border-gray-200 rounded-lg"
                                .value=${String(this.createForm.cooldown_seconds)}
                                @input=${(e: Event) => { this.createForm = { ...this.createForm, cooldown_seconds: parseInt((e.target as HTMLInputElement).value) || 300 }; }}>
                        </div>
                    </div>
                </div>
                <div class="px-6 py-4 border-t border-gray-100 flex items-center justify-end gap-2">
                    <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        @click=${() => { this.showCreateModal = false; }}>Cancel</button>
                    <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors ${this.creating ? 'opacity-50' : ''}"
                        ?disabled=${this.creating || !this.createForm.name.trim() || !this.createForm.metric.trim()}
                        @click=${() => this.createRule()}>
                        ${this.creating ? 'Creating...' : 'Create Rule'}
                    </button>
                </div>
            </div>
        </div>`;
    }
}
