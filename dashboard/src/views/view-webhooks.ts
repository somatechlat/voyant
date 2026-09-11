import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface Webhook {
    id: string;
    url: string;
    events: string[];
    status: string;
    description: string;
    retry_policy: Record<string, unknown>;
    headers: Record<string, unknown>;
    failure_count: number;
    last_triggered_at: string | null;
}

interface WebhookDelivery {
    id: string;
    webhook_id: string;
    event_type: string;
    payload: Record<string, unknown>;
    status: string;
    attempts: number;
    max_retries: number;
    last_response_code: number | null;
    last_error: string;
    delivered_at: string | null;
}

/* ── Available event types ─────────────────────────────────────────────────── */

const AVAILABLE_EVENTS = [
    'job.completed', 'job.failed', 'job.started',
    'pipeline.completed', 'pipeline.failed',
    'source.connected', 'source.disconnected',
    'drift.detected', 'drift.resolved',
    'alert.fired', 'alert.resolved',
    'model.deployed', 'model.rolled_back',
    'webhook.test',
];

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-webhooks')
export class ViewWebhooks extends LitElement {
    @state() webhooks: Webhook[] = [];
    @state() loading = true;
    @state() error: string | null = null;

    // Detail panel
    @state() selectedWebhook: Webhook | null = null;
    @state() deliveries: WebhookDelivery[] = [];
    @state() deliveriesLoading = false;

    // Create modal
    @state() showCreateModal = false;
    @state() createForm = { url: '', events: [] as string[], secret: '', description: '', max_retries: 3, initial_backoff_seconds: 1, backoff_multiplier: 2 };
    @state() creating = false;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadWebhooks();
    }

    /* ── Data Loading ─────────────────────────────────────────────────────── */

    async loadWebhooks() {
        this.loading = true;
        this.error = null;
        try {
            this.webhooks = await api.get<Webhook[]>('/webhooks/');
        } catch (e) {
            this.error = e instanceof Error ? e.message : 'Failed to load webhooks';
            this.webhooks = [];
        } finally {
            this.loading = false;
        }
    }

    async loadDeliveries(webhookId: string) {
        this.deliveriesLoading = true;
        this.selectedWebhook = this.webhooks.find(w => w.id === webhookId) || null;
        try {
            this.deliveries = await api.get<WebhookDelivery[]>(`/webhooks/${webhookId}/deliveries`);
        } catch {
            this.deliveries = [];
        } finally {
            this.deliveriesLoading = false;
        }
    }

    async createWebhook() {
        this.creating = true;
        try {
            await api.post('/webhooks/', {
                url: this.createForm.url,
                events: this.createForm.events,
                secret: this.createForm.secret || undefined,
                description: this.createForm.description,
                retry_policy: {
                    max_retries: this.createForm.max_retries,
                    initial_backoff_seconds: this.createForm.initial_backoff_seconds,
                    backoff_multiplier: this.createForm.backoff_multiplier,
                },
            });
            this.showCreateModal = false;
            this.createForm = { url: '', events: [], secret: '', description: '', max_retries: 3, initial_backoff_seconds: 1, backoff_multiplier: 2 };
            await this.loadWebhooks();
        } catch { /* empty */ } finally {
            this.creating = false;
        }
    }

    async toggleWebhook(wh: Webhook) {
        const newStatus = wh.status === 'active' ? 'inactive' : 'active';
        try {
            await api.put(`/webhooks/${wh.id}`, { status: newStatus });
            await this.loadWebhooks();
        } catch { /* empty */ }
    }

    async deleteWebhook(id: string) {
        try {
            await api.del(`/webhooks/${id}`);
            if (this.selectedWebhook?.id === id) this.selectedWebhook = null;
            await this.loadWebhooks();
        } catch { /* empty */ }
    }

    /* ── Helpers ──────────────────────────────────────────────────────────── */

    private statusBadge(s: string) {
        const colors: Record<string, string> = {
            active: 'bg-green-50 text-green-700 border-green-200',
            inactive: 'bg-gray-50 text-gray-500 border-gray-200',
        };
        const dot: Record<string, string> = { active: 'bg-green-500', inactive: 'bg-gray-400' };
        return html`<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-medium rounded-full border ${colors[s] || colors.inactive}">
            <span class="inline-block w-1.5 h-1.5 rounded-full ${dot[s] || dot.inactive}"></span>${s}</span>`;
    }

    private deliveryStatusBadge(s: string) {
        const colors: Record<string, string> = {
            success: 'bg-green-50 text-green-700 border-green-200',
            pending: 'bg-blue-50 text-blue-700 border-blue-200',
            failed: 'bg-red-50 text-red-700 border-red-200',
            retrying: 'bg-amber-50 text-amber-700 border-amber-200',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[s] || 'bg-gray-50 text-gray-700 border-gray-200'}">${s}</span>`;
    }

    private toggleEvent(evt: string) {
        const events = [...this.createForm.events];
        const idx = events.indexOf(evt);
        if (idx >= 0) events.splice(idx, 1);
        else events.push(evt);
        this.createForm = { ...this.createForm, events };
    }

    /* ── Render ───────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/webhooks"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Webhooks">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Webhooks</h1>
                    <p class="text-sm text-gray-500 mt-1">Manage webhook subscriptions and monitor delivery history</p>
                </div>
                <div class="flex gap-2">
                    <button class="px-4 py-1.5 text-sm font-semibold border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors flex items-center gap-2"
                        @click=${() => this.loadWebhooks()}>
                        <svg class="w-4 h-4 ${this.loading ? 'animate-spin' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                        Refresh
                    </button>
                    <button class="px-4 py-1.5 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
                        @click=${() => { this.showCreateModal = true; }}>
                        + Create Webhook
                    </button>
                </div>
            </div>

            ${this.error ? html`
            <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <svg class="w-5 h-5 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                    <span class="text-sm text-red-700">${this.error}</span>
                </div>
                <button class="text-sm text-red-600 hover:underline" @click=${() => this.loadWebhooks()}>Retry</button>
            </div>` : ''}

            ${this.loading ? html`
            <div class="text-center py-16" role="status" aria-live="polite">
                <div class="inline-block w-8 h-8 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin mb-3"></div>
                <div class="text-sm text-gray-500">Loading webhooks...</div>
            </div>` : html`
            <!-- Webhooks Table -->
            ${this.renderWebhooksTable()}

            <!-- Delivery History (inline below selected webhook) -->
            ${this.selectedWebhook ? this.renderDeliveryHistory() : ''}
            `}

            <!-- Create Modal -->
            ${this.showCreateModal ? this.renderCreateModal() : ''}
        </main>`;
    }

    /* ── Webhooks Table ───────────────────────────────────────────────────── */

    private renderWebhooksTable() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Webhook Subscriptions</h2>
                <span class="text-xs text-gray-500">${this.webhooks.length} webhooks</span>
            </div>
            <table class="w-full text-sm" role="table" aria-label="Webhooks">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">URL</th>
                    <th class="px-5 py-3">Events</th>
                    <th class="px-5 py-3">Status</th>
                    <th class="px-5 py-3">Last Delivery</th>
                    <th class="px-5 py-3">Failures</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.webhooks.length === 0 ? html`
                <tr><td colspan="6" class="px-5 py-16 text-center text-gray-500">
                    <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
                        <svg class="w-7 h-7 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
                    </div>
                    <div class="text-sm font-semibold text-gray-600">No webhooks configured</div>
                    <div class="text-xs mt-2 text-gray-500">Create a webhook to receive event notifications via HTTP POST.</div>
                </td></tr>` : ''}
                ${this.webhooks.map(wh => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50">
                    <td class="px-5 py-3">
                        <div class="font-mono text-xs truncate max-w-[280px]">${wh.url}</div>
                        ${wh.description ? html`<div class="text-xs text-gray-500 mt-0.5 truncate max-w-[280px]">${wh.description}</div>` : ''}
                    </td>
                    <td class="px-5 py-3">
                        <div class="flex flex-wrap gap-1">
                            ${(wh.events || []).slice(0, 3).map(evt => html`
                            <span class="px-1.5 py-0.5 text-xs bg-gray-100 rounded font-mono">${evt}</span>`)}
                            ${(wh.events || []).length > 3 ? html`<span class="px-1.5 py-0.5 text-xs text-gray-500">+${wh.events.length - 3}</span>` : ''}
                        </div>
                    </td>
                    <td class="px-5 py-3">${this.statusBadge(wh.status)}</td>
                    <td class="px-5 py-3 text-xs text-gray-500">${wh.last_triggered_at ? new Date(wh.last_triggered_at).toLocaleString() : '—'}</td>
                    <td class="px-5 py-3">
                        <span class="text-sm font-semibold ${wh.failure_count > 0 ? 'text-red-600' : 'text-gray-500'}">${wh.failure_count}</span>
                    </td>
                    <td class="px-5 py-3">
                        <div class="flex gap-2">
                            <button class="text-xs text-blue-600 hover:underline"
                                @click=${() => this.loadDeliveries(wh.id)}>Deliveries</button>
                            <button class="text-xs ${wh.status === 'active' ? 'text-amber-600' : 'text-green-600'} hover:underline"
                                @click=${() => this.toggleWebhook(wh)}>
                                ${wh.status === 'active' ? 'Disable' : 'Enable'}
                            </button>
                            <button class="text-xs text-red-600 hover:underline"
                                @click=${() => this.deleteWebhook(wh.id)}>Delete</button>
                        </div>
                    </td>
                </tr>`)}
                </tbody>
            </table>
        </div>`;
    }

    /* ── Delivery History ─────────────────────────────────────────────────── */

    private renderDeliveryHistory() {
        const wh = this.selectedWebhook!;
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden mt-6">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Delivery History — <span class="font-mono text-xs">${wh.url}</span></h2>
                <span class="text-xs text-gray-500">${this.deliveries.length} deliveries</span>
            </div>
            ${this.deliveriesLoading ? html`
            <div class="p-8 text-center text-gray-500">Loading deliveries...</div>` : html`
            ${this.deliveries.length === 0 ? html`
            <div class="p-8 text-center text-gray-500">No deliveries recorded for this webhook.</div>` : html`
            <table class="w-full text-sm">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-2.5">Event Type</th>
                    <th class="px-5 py-2.5">Status</th>
                    <th class="px-5 py-2.5">Attempts</th>
                    <th class="px-5 py-2.5">Response</th>
                    <th class="px-5 py-2.5">Error</th>
                    <th class="px-5 py-2.5">Timestamp</th>
                </tr></thead>
                <tbody>
                ${this.deliveries.map(d => html`
                <tr class="border-b border-gray-50">
                    <td class="px-5 py-2.5"><span class="px-1.5 py-0.5 text-xs bg-gray-100 rounded font-mono">${d.event_type}</span></td>
                    <td class="px-5 py-2.5">${this.deliveryStatusBadge(d.status)}</td>
                    <td class="px-5 py-2.5 text-xs">${d.attempts} / ${d.max_retries}</td>
                    <td class="px-5 py-2.5 text-xs font-mono">${d.last_response_code ?? '—'}</td>
                    <td class="px-5 py-2.5 text-xs text-red-600 truncate max-w-[200px]">${d.last_error || '—'}</td>
                    <td class="px-5 py-2.5 text-xs text-gray-500">${d.delivered_at ? new Date(d.delivered_at).toLocaleString() : '—'}</td>
                </tr>`)}
                </tbody>
            </table>`}`}
        </div>`;
    }

    /* ── Create Modal ─────────────────────────────────────────────────────── */

    private renderCreateModal() {
        return html`
        <div class="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Create webhook"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this.showCreateModal = false; }}>
            <div class="absolute inset-0 bg-black/30" @click=${() => { this.showCreateModal = false; }}></div>
            <div class="relative bg-white rounded-2xl shadow-2xl w-[560px] max-h-[85vh] overflow-y-auto" tabindex="-1">
                <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                    <h2 class="font-bold text-lg">Create Webhook</h2>
                    <button class="text-gray-500 hover:text-ink" @click=${() => { this.showCreateModal = false; }}>✕</button>
                </div>
                <div class="p-6 space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">URL *</label>
                        <input type="url" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="https://example.com/webhook"
                            .value=${this.createForm.url}
                            @input=${(e: Event) => { this.createForm = { ...this.createForm, url: (e.target as HTMLInputElement).value }; }}>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Description</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="What this webhook is for"
                            .value=${this.createForm.description}
                            @input=${(e: Event) => { this.createForm = { ...this.createForm, description: (e.target as HTMLInputElement).value }; }}>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-2">Events *</label>
                        <div class="grid grid-cols-2 gap-1.5">
                            ${AVAILABLE_EVENTS.map(evt => html`
                            <label class="flex items-center gap-2 text-xs cursor-pointer py-1 px-2 rounded hover:bg-gray-50">
                                <input type="checkbox" .checked=${this.createForm.events.includes(evt)}
                                    @change=${() => this.toggleEvent(evt)}>
                                <span class="font-mono">${evt}</span>
                            </label>`)}
                        </div>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Secret (auto-generated if empty)</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10 font-mono"
                            placeholder="Auto-generated HMAC secret"
                            .value=${this.createForm.secret}
                            @input=${(e: Event) => { this.createForm = { ...this.createForm, secret: (e.target as HTMLInputElement).value }; }}>
                    </div>
                    <div class="grid grid-cols-3 gap-3">
                        <div>
                            <label class="block text-xs font-semibold text-gray-600 mb-1">Max Retries</label>
                            <input type="number" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                                .value=${String(this.createForm.max_retries)}
                                @input=${(e: Event) => { this.createForm = { ...this.createForm, max_retries: parseInt((e.target as HTMLInputElement).value) || 3 }; }}>
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-gray-600 mb-1">Initial Backoff (s)</label>
                            <input type="number" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                                .value=${String(this.createForm.initial_backoff_seconds)}
                                @input=${(e: Event) => { this.createForm = { ...this.createForm, initial_backoff_seconds: parseInt((e.target as HTMLInputElement).value) || 1 }; }}>
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-gray-600 mb-1">Backoff Multiplier</label>
                            <input type="number" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                                .value=${String(this.createForm.backoff_multiplier)}
                                @input=${(e: Event) => { this.createForm = { ...this.createForm, backoff_multiplier: parseInt((e.target as HTMLInputElement).value) || 2 }; }}>
                        </div>
                    </div>
                </div>
                <div class="px-6 py-4 border-t border-gray-100 flex items-center justify-end gap-2">
                    <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        @click=${() => { this.showCreateModal = false; }}>Cancel</button>
                    <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors ${this.creating ? 'opacity-50' : ''}"
                        ?disabled=${this.creating || !this.createForm.url.trim() || this.createForm.events.length === 0}
                        @click=${() => this.createWebhook()}>
                        ${this.creating ? 'Creating...' : 'Create Webhook'}
                    </button>
                </div>
            </div>
        </div>`;
    }
}
