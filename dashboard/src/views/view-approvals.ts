import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface ApprovalRequest {
    id: string;
    request_type: string;
    resource_type: string;
    resource_id: string;
    requester_id: string;
    approver_id: string;
    status: string;
    reason: string;
    approved_at: string | null;
    expires_at: string | null;
    metadata: Record<string, unknown>;
    created_at: string;
    updated_at: string;
}

interface ApprovalRule {
    id: string;
    name: string;
    request_type: string;
    auto_approve_conditions: Record<string, unknown>;
    required_approvers_count: number;
    escalation_timeout_hours: number;
    enabled: boolean;
    created_at: string;
    updated_at: string;
}

/* ── Constants ─────────────────────────────────────────────────────────────── */

const STATUS_COLORS: Record<string, string> = {
    pending: 'bg-amber-50 text-amber-700 border-amber-200',
    approved: 'bg-green-50 text-green-700 border-green-200',
    rejected: 'bg-red-50 text-red-700 border-red-200',
    expired: 'bg-gray-50 text-gray-500 border-gray-200',
};

const REQUEST_TYPE_LABELS: Record<string, string> = {
    action_execution: 'Action Execution',
    model_deployment: 'Model Deployment',
    policy_change: 'Policy Change',
    data_export: 'Data Export',
};

const REQUEST_TYPE_ICONS: Record<string, string> = {
    action_execution: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    model_deployment: '<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>',
    policy_change: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    data_export: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
};

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-approvals')
export class ViewApprovals extends LitElement {
    @state() tab: 'requests' | 'rules' | 'history' = 'requests';
    @state() requests: ApprovalRequest[] = [];
    @state() history: ApprovalRequest[] = [];
    @state() rules: ApprovalRule[] = [];
    @state() loading = true;

    // Filters
    @state() statusFilter: 'all' | 'pending' | 'approved' | 'rejected' = 'pending';

    // Detail panel
    @state() selectedRequest: ApprovalRequest | null = null;
    @state() actionReason = '';
    @state() acting = false;

    // Create rule form
    @state() showCreateRule = false;
    @state() ruleName = '';
    @state() ruleRequestType = 'action_execution';
    @state() ruleApproverCount = 1;
    @state() ruleTimeoutHours = 24;
    @state() ruleEnabled = true;
    @state() creatingRule = false;

    // Toast
    @state() toast = '';

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadRequests();
    }

    /* ── Data loading ──────────────────────────────────────────────────────── */

    async loadRequests() {
        this.loading = true;
        try {
            const all = await api.get<ApprovalRequest[]>('/approvals');
            if (this.statusFilter === 'all') {
                this.requests = all;
            } else {
                this.requests = all.filter(r => r.status === this.statusFilter);
            }
        } catch { this.requests = []; }
        finally { this.loading = false; }
    }

    async loadHistory() {
        this.loading = true;
        try {
            this.history = await api.get<ApprovalRequest[]>('/approvals/history');
        } catch { this.history = []; }
        finally { this.loading = false; }
    }

    async loadRules() {
        this.loading = true;
        try {
            this.rules = await api.get<ApprovalRule[]>('/approvals/rules');
        } catch { this.rules = []; }
        finally { this.loading = false; }
    }

    /* ── Actions ───────────────────────────────────────────────────────────── */

    async approveRequest() {
        if (!this.selectedRequest) return;
        this.acting = true;
        try {
            await api.put(`/approvals/${this.selectedRequest.id}/approve`, {
                reason: this.actionReason,
            });
            this.showToast('Request approved');
            this.selectedRequest = null;
            this.actionReason = '';
            await this.loadRequests();
        } catch { this.showToast('Failed to approve'); }
        finally { this.acting = false; }
    }

    async rejectRequest() {
        if (!this.selectedRequest) return;
        this.acting = true;
        try {
            await api.put(`/approvals/${this.selectedRequest.id}/reject`, {
                reason: this.actionReason,
            });
            this.showToast('Request rejected');
            this.selectedRequest = null;
            this.actionReason = '';
            await this.loadRequests();
        } catch { this.showToast('Failed to reject'); }
        finally { this.acting = false; }
    }

    async createRule() {
        if (!this.ruleName.trim()) return;
        this.creatingRule = true;
        try {
            await api.post('/approvals/rules', {
                name: this.ruleName,
                request_type: this.ruleRequestType,
                required_approvers_count: this.ruleApproverCount,
                escalation_timeout_hours: this.ruleTimeoutHours,
                enabled: this.ruleEnabled,
            });
            this.showCreateRule = false;
            this.ruleName = '';
            this.showToast('Rule created');
            await this.loadRules();
        } catch { this.showToast('Failed to create rule'); }
        finally { this.creatingRule = false; }
    }

    /* ── Helpers ───────────────────────────────────────────────────────────── */

    private showToast(msg: string) {
        this.toast = msg;
        setTimeout(() => { this.toast = ''; }, 3000);
    }

    private relativeTime(iso: string): string {
        const diff = Date.now() - new Date(iso).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        const days = Math.floor(hrs / 24);
        return `${days}d ago`;
    }

    private get pendingCount() {
        return this.requests.filter(r => r.status === 'pending').length;
    }

    private get approvedTodayCount() {
        const today = new Date().toISOString().slice(0, 10);
        return this.history.filter(r => r.status === 'approved' && r.approved_at?.startsWith(today)).length;
    }

    private get rejectedTodayCount() {
        const today = new Date().toISOString().slice(0, 10);
        return this.history.filter(r => r.status === 'rejected' && r.approved_at?.startsWith(today)).length;
    }

    /* ── Render ────────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/approvals"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Approval Center">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Approvals</h1>
                    <p class="text-sm text-gray-400 mt-1">Review and manage approval requests</p>
                </div>
            </div>

            <!-- Tabs -->
            <div class="flex gap-1 mb-6 bg-white rounded-lg p-1 border border-gray-100 w-fit" role="tablist">
                ${(['requests', 'rules', 'history'] as const).map(t => html`
                <button class="px-4 py-2 text-sm font-semibold rounded-md transition-colors ${this.tab === t ? 'bg-brand text-white' : 'text-gray-500 hover:text-ink'}"
                    role="tab" aria-selected=${this.tab === t}
                    @click=${() => {
                        this.tab = t;
                        if (t === 'requests') this.loadRequests();
                        if (t === 'rules') this.loadRules();
                        if (t === 'history') this.loadHistory();
                    }}>
                    ${t === 'requests' ? 'Requests' : t === 'rules' ? 'Rules' : 'History'}
                </button>`)}
            </div>

            ${this.tab === 'requests' ? this.renderRequestsTab() : ''}
            ${this.tab === 'rules' ? this.renderRulesTab() : ''}
            ${this.tab === 'history' ? this.renderHistoryTab() : ''}

            <!-- Detail Panel -->
            ${this.selectedRequest ? this.renderDetailPanel() : ''}

            <!-- Create Rule Modal -->
            ${this.showCreateRule ? this.renderCreateRuleModal() : ''}

            <!-- Toast -->
            ${this.toast ? html`
            <div class="fixed bottom-6 right-6 px-4 py-3 rounded-xl shadow-lg text-sm font-semibold z-50 bg-green-600 text-white">
                ${this.toast}
            </div>` : ''}
        </main>`;
    }

    /* ── Requests Tab ──────────────────────────────────────────────────────── */

    private renderRequestsTab() {
        return html`
            <!-- Summary Cards -->
            <div class="grid grid-cols-4 gap-4 mb-6">
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Pending</div>
                    <div class="text-2xl font-bold text-amber-600">${this.pendingCount}</div>
                </div>
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Approved Today</div>
                    <div class="text-2xl font-bold text-green-600">${this.approvedTodayCount}</div>
                </div>
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Rejected Today</div>
                    <div class="text-2xl font-bold text-red-600">${this.rejectedTodayCount}</div>
                </div>
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Total</div>
                    <div class="text-2xl font-bold">${this.requests.length}</div>
                </div>
            </div>

            <!-- Filter -->
            <div class="flex gap-2 mb-4">
                <select class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
                    aria-label="Filter by status"
                    @change=${(e: Event) => { this.statusFilter = (e.target as HTMLSelectElement).value as 'all' | 'pending' | 'approved' | 'rejected'; this.loadRequests(); }}>
                    <option value="pending" ?selected=${this.statusFilter === 'pending'}>Pending</option>
                    <option value="approved" ?selected=${this.statusFilter === 'approved'}>Approved</option>
                    <option value="rejected" ?selected=${this.statusFilter === 'rejected'}>Rejected</option>
                    <option value="all" ?selected=${this.statusFilter === 'all'}>All</option>
                </select>
                <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                    aria-label="Refresh approvals" @click=${() => this.loadRequests()}>Refresh</button>
            </div>

            ${this.loading ? html`<div class="text-center text-gray-400 py-16" role="status" aria-live="polite">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
                <table class="w-full text-sm" role="table" aria-label="Approval requests">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                        <th class="px-5 py-3">Type</th>
                        <th class="px-5 py-3">Resource</th>
                        <th class="px-5 py-3">Requester</th>
                        <th class="px-5 py-3">Status</th>
                        <th class="px-5 py-3">Created</th>
                        <th class="px-5 py-3">Actions</th>
                    </tr></thead>
                    <tbody>
                    ${this.requests.length === 0 ? html`
                    <tr><td colspan="6" class="px-5 py-12 text-center text-gray-400">
                        No approval requests found
                    </td></tr>` : ''}
                    ${this.requests.map(r => html`
                    <tr class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer" role="button" tabindex="0"
                        aria-label="${REQUEST_TYPE_LABELS[r.request_type] || r.request_type} by ${r.requester_id}"
                        @click=${() => { this.selectedRequest = r; this.actionReason = ''; }}
                        @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.selectedRequest = r; this.actionReason = ''; } }}>
                        <td class="px-5 py-3">
                            <div class="flex items-center gap-2">
                                <svg class="w-4 h-4 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <g innerHTML="${REQUEST_TYPE_ICONS[r.request_type] || REQUEST_TYPE_ICONS.action_execution}"></g>
                                </svg>
                                <span class="text-xs font-mono">${REQUEST_TYPE_LABELS[r.request_type] || r.request_type}</span>
                            </div>
                        </td>
                        <td class="px-5 py-3 text-xs">${r.resource_type}:${r.resource_id.slice(0, 8)}</td>
                        <td class="px-5 py-3 font-mono text-xs">${r.requester_id}</td>
                        <td class="px-5 py-3"><span class="px-2 py-0.5 text-xs font-medium rounded border ${STATUS_COLORS[r.status] || STATUS_COLORS.pending}">${r.status}</span></td>
                        <td class="px-5 py-3 text-xs text-gray-500">${this.relativeTime(r.created_at)}</td>
                        <td class="px-5 py-3" @click=${(e: Event) => e.stopPropagation()}>
                            ${r.status === 'pending' ? html`
                            <div class="flex gap-2">
                                <button class="text-xs text-green-600 hover:underline"
                                    @click=${() => { this.selectedRequest = r; this.actionReason = ''; }}>Review</button>
                            </div>` : html`
                            <span class="text-xs text-gray-400">—</span>`}
                        </td>
                    </tr>`)}
                    </tbody>
                </table>
            </div>`}
        `;
    }

    /* ── Rules Tab ─────────────────────────────────────────────────────────── */

    private renderRulesTab() {
        return html`
            <div class="flex gap-2 mb-4">
                <button class="px-4 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                    @click=${() => { this.showCreateRule = true; }}>+ New Rule</button>
                <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                    @click=${() => this.loadRules()}>Refresh</button>
            </div>

            ${this.loading ? html`<div class="text-center text-gray-400 py-16" role="status">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <table class="w-full text-sm" role="table" aria-label="Approval rules">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                        <th class="px-5 py-3">Name</th>
                        <th class="px-5 py-3">Request Type</th>
                        <th class="px-5 py-3">Approvers</th>
                        <th class="px-5 py-3">Timeout (hrs)</th>
                        <th class="px-5 py-3">Status</th>
                        <th class="px-5 py-3">Created</th>
                    </tr></thead>
                    <tbody>
                    ${this.rules.length === 0 ? html`
                    <tr><td colspan="6" class="px-5 py-12 text-center text-gray-400">
                        No approval rules configured. Create one to get started.
                    </td></tr>` : ''}
                    ${this.rules.map(r => html`
                    <tr class="border-b border-gray-50 hover:bg-gray-50">
                        <td class="px-5 py-3 font-semibold">${r.name}</td>
                        <td class="px-5 py-3 text-xs font-mono">${REQUEST_TYPE_LABELS[r.request_type] || r.request_type}</td>
                        <td class="px-5 py-3">${r.required_approvers_count}</td>
                        <td class="px-5 py-3">${r.escalation_timeout_hours}</td>
                        <td class="px-5 py-3">
                            <span class="px-2 py-0.5 text-xs rounded border ${r.enabled ? 'bg-green-50 text-green-700 border-green-200' : 'bg-gray-50 text-gray-500 border-gray-200'}">
                                ${r.enabled ? 'Enabled' : 'Disabled'}
                            </span>
                        </td>
                        <td class="px-5 py-3 text-xs text-gray-500">${new Date(r.created_at).toLocaleDateString()}</td>
                    </tr>`)}
                    </tbody>
                </table>
            </div>`}
        `;
    }

    /* ── History Tab ───────────────────────────────────────────────────────── */

    private renderHistoryTab() {
        return html`
            <div class="flex gap-2 mb-4">
                <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                    @click=${() => this.loadHistory()}>Refresh</button>
            </div>

            ${this.loading ? html`<div class="text-center text-gray-400 py-16" role="status">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <table class="w-full text-sm" role="table" aria-label="Approval history">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                        <th class="px-5 py-3">Type</th>
                        <th class="px-5 py-3">Resource</th>
                        <th class="px-5 py-3">Requester</th>
                        <th class="px-5 py-3">Approver</th>
                        <th class="px-5 py-3">Status</th>
                        <th class="px-5 py-3">Reason</th>
                        <th class="px-5 py-3">Resolved</th>
                    </tr></thead>
                    <tbody>
                    ${this.history.length === 0 ? html`
                    <tr><td colspan="7" class="px-5 py-12 text-center text-gray-400">
                        No resolved approvals
                    </td></tr>` : ''}
                    ${this.history.map(r => html`
                    <tr class="border-b border-gray-50 hover:bg-gray-50">
                        <td class="px-5 py-3 text-xs font-mono">${REQUEST_TYPE_LABELS[r.request_type] || r.request_type}</td>
                        <td class="px-5 py-3 text-xs">${r.resource_type}:${r.resource_id.slice(0, 8)}</td>
                        <td class="px-5 py-3 font-mono text-xs">${r.requester_id}</td>
                        <td class="px-5 py-3 font-mono text-xs">${r.approver_id || '—'}</td>
                        <td class="px-5 py-3"><span class="px-2 py-0.5 text-xs font-medium rounded border ${STATUS_COLORS[r.status] || STATUS_COLORS.pending}">${r.status}</span></td>
                        <td class="px-5 py-3 text-xs text-gray-500 max-w-xs truncate">${r.reason || '—'}</td>
                        <td class="px-5 py-3 text-xs text-gray-500">${r.approved_at ? this.relativeTime(r.approved_at) : '—'}</td>
                    </tr>`)}
                    </tbody>
                </table>
            </div>`}
        `;
    }

    /* ── Detail Panel ──────────────────────────────────────────────────────── */

    private renderDetailPanel() {
        const r = this.selectedRequest!;
        const isPending = r.status === 'pending';

        return html`
        <div class="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true" aria-label="Approval request detail">
            <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedRequest = null; }}></div>
            <div class="relative w-full max-w-lg bg-white shadow-2xl flex flex-col overflow-hidden">
                <!-- Panel Header -->
                <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <div>
                        <h2 class="text-lg font-bold">Approval Request</h2>
                        <p class="text-xs text-gray-400 font-mono">${r.id}</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-0.5 text-xs font-medium rounded border ${STATUS_COLORS[r.status] || STATUS_COLORS.pending}">${r.status}</span>
                        <button class="text-gray-400 hover:text-ink text-xl" aria-label="Close panel" @click=${() => { this.selectedRequest = null; }}>✕</button>
                    </div>
                </div>

                <!-- Panel Body -->
                <div class="flex-1 overflow-y-auto p-6 space-y-5">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Request Type</div>
                            <div class="flex items-center gap-2">
                                <svg class="w-4 h-4 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <g innerHTML="${REQUEST_TYPE_ICONS[r.request_type] || REQUEST_TYPE_ICONS.action_execution}"></g>
                                </svg>
                                <span class="text-sm font-semibold">${REQUEST_TYPE_LABELS[r.request_type] || r.request_type}</span>
                            </div>
                        </div>
                        <div>
                            <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Status</div>
                            <span class="px-2 py-0.5 text-xs font-medium rounded border ${STATUS_COLORS[r.status] || STATUS_COLORS.pending}">${r.status}</span>
                        </div>
                        <div>
                            <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Resource</div>
                            <div class="text-sm font-mono">${r.resource_type}:${r.resource_id.slice(0, 12)}</div>
                        </div>
                        <div>
                            <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Requester</div>
                            <div class="text-sm font-mono">${r.requester_id}</div>
                        </div>
                        ${r.approver_id ? html`
                        <div>
                            <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Approver</div>
                            <div class="text-sm font-mono">${r.approver_id}</div>
                        </div>` : ''}
                        <div>
                            <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Created</div>
                            <div class="text-sm">${new Date(r.created_at).toLocaleString()}</div>
                        </div>
                        ${r.approved_at ? html`
                        <div>
                            <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Resolved</div>
                            <div class="text-sm">${new Date(r.approved_at).toLocaleString()}</div>
                        </div>` : ''}
                        ${r.expires_at ? html`
                        <div>
                            <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Expires</div>
                            <div class="text-sm">${new Date(r.expires_at).toLocaleString()}</div>
                        </div>` : ''}
                    </div>

                    ${r.reason ? html`
                    <div>
                        <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Reason</div>
                        <div class="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">${r.reason}</div>
                    </div>` : ''}

                    ${Object.keys(r.metadata).length > 0 ? html`
                    <div>
                        <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Metadata</div>
                        <pre class="text-xs font-mono text-gray-600 bg-gray-50 rounded-lg p-3 overflow-x-auto">${JSON.stringify(r.metadata, null, 2)}</pre>
                    </div>` : ''}

                    <!-- Action Section (pending only) -->
                    ${isPending ? html`
                    <div class="border-t border-gray-100 pt-5">
                        <div class="text-xs text-gray-400 uppercase tracking-wider mb-2">Take Action</div>
                        <textarea class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg h-20 resize-none mb-3"
                            placeholder="Reason for approval or rejection (optional for approve, recommended for reject)"
                            .value=${this.actionReason}
                            @input=${(e: Event) => { this.actionReason = (e.target as HTMLTextAreaElement).value; }}></textarea>
                        <div class="flex gap-2">
                            <button class="flex-1 px-4 py-2 text-sm font-semibold bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors ${this.acting ? 'opacity-50 pointer-events-none' : ''}"
                                @click=${() => this.approveRequest()}>
                                ${this.acting ? 'Processing...' : 'Approve'}
                            </button>
                            <button class="flex-1 px-4 py-2 text-sm font-semibold bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors ${this.acting ? 'opacity-50 pointer-events-none' : ''}"
                                @click=${() => this.rejectRequest()}>
                                ${this.acting ? 'Processing...' : 'Reject'}
                            </button>
                        </div>
                    </div>` : ''}
                </div>
            </div>
        </div>`;
    }

    /* ── Create Rule Modal ─────────────────────────────────────────────────── */

    private renderCreateRuleModal() {
        return html`
        <div class="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Create Approval Rule"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this.showCreateRule = false; }}>
            <div class="absolute inset-0 bg-black/30" @click=${() => { this.showCreateRule = false; }}></div>
            <div class="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden" tabindex="-1">
                <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <h2 class="text-lg font-bold">Create Approval Rule</h2>
                    <button class="text-gray-400 hover:text-ink text-xl" aria-label="Close" @click=${() => { this.showCreateRule = false; }}>✕</button>
                </div>
                <div class="p-6 space-y-4">
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Name *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            placeholder="e.g. Production Deployment Approval"
                            .value=${this.ruleName}
                            @input=${(e: Event) => { this.ruleName = (e.target as HTMLInputElement).value; }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Request Type *</label>
                        <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white"
                            .value=${this.ruleRequestType}
                            @change=${(e: Event) => { this.ruleRequestType = (e.target as HTMLSelectElement).value; }}>
                            <option value="action_execution">Action Execution</option>
                            <option value="model_deployment">Model Deployment</option>
                            <option value="policy_change">Policy Change</option>
                            <option value="data_export">Data Export</option>
                        </select>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">Required Approvers</label>
                            <input type="number" min="1" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                                .value=${String(this.ruleApproverCount)}
                                @input=${(e: Event) => { this.ruleApproverCount = parseInt((e.target as HTMLInputElement).value) || 1; }} />
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">Timeout (hours)</label>
                            <input type="number" min="1" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                                .value=${String(this.ruleTimeoutHours)}
                                @input=${(e: Event) => { this.ruleTimeoutHours = parseInt((e.target as HTMLInputElement).value) || 24; }} />
                        </div>
                    </div>
                    <div class="flex items-center gap-3">
                        <label class="text-xs font-medium text-gray-500">Enabled:</label>
                        <button class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${this.ruleEnabled ? 'bg-brand' : 'bg-gray-200'}"
                            role="switch" aria-checked=${this.ruleEnabled} aria-label="Toggle rule enabled"
                            @click=${() => { this.ruleEnabled = !this.ruleEnabled; }}>
                            <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${this.ruleEnabled ? 'translate-x-4.5' : 'translate-x-0.5'}"></span>
                        </button>
                        <span class="text-xs text-gray-500">${this.ruleEnabled ? 'Active' : 'Disabled'}</span>
                    </div>
                </div>
                <div class="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 bg-gray-50">
                    <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        @click=${() => { this.showCreateRule = false; }}>Cancel</button>
                    <button class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.creatingRule || !this.ruleName.trim() ? 'opacity-50 pointer-events-none' : ''}"
                        @click=${() => this.createRule()}>
                        ${this.creatingRule ? 'Creating...' : 'Create Rule'}
                    </button>
                </div>
            </div>
        </div>`;
    }
}
