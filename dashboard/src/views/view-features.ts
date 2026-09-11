import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface FeatureGroup {
    id: string;
    name: string;
    description: string;
    entity_key: string;
    online_enabled: boolean;
    batch_enabled: boolean;
    schedule: string;
    tags: Record<string, unknown>;
    feature_count: number;
    created_by: string;
    created_at: string;
    updated_at: string;
}

interface Feature {
    id: string;
    name: string;
    data_type: string;
    description: string;
    source_expression: string;
    statistics: Record<string, number>;
    ordinal_position: number;
}

interface FeatureGroupDetail extends FeatureGroup {
    features: Feature[];
}

interface FeatureValue {
    id: string;
    feature_name: string;
    feature_group: string;
    entity_key_value: string;
    value: unknown;
    computed_at: string;
}

interface GroupStatistics {
    group_id: string;
    group_name: string;
    features: Array<{
        name: string;
        data_type: string;
        statistics: Record<string, number>;
    }>;
}

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-features')
export class ViewFeatures extends LitElement {
    @state() groups: FeatureGroup[] = [];
    @state() loading = true;
    @state() error: string | null = null;

    // Detail panel
    @state() selectedGroup: FeatureGroupDetail | null = null;
    @state() detailLoading = false;

    // Statistics
    @state() groupStats: GroupStatistics | null = null;
    @state() statsLoading = false;

    // Query panel
    @state() queryEntityKeyValue = '';
    @state() queryResults: FeatureValue[] = [];
    @state() queryLoading = false;

    // Create modal
    @state() showCreateModal = false;
    @state() createForm = { name: '', description: '', entity_key: 'entity_id', online_enabled: false, batch_enabled: true, schedule: '' };
    @state() creating = false;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadGroups();
    }

    /* ── Data Loading ─────────────────────────────────────────────────────── */

    async loadGroups() {
        this.loading = true;
        this.error = null;
        try {
            this.groups = await api.get<FeatureGroup[]>('/features/groups');
        } catch (e) {
            this.error = e instanceof Error ? e.message : 'Failed to load feature groups';
            this.groups = [];
        } finally {
            this.loading = false;
        }
    }

    async loadGroupDetail(groupId: string) {
        this.detailLoading = true;
        this.groupStats = null;
        try {
            const detail = await api.get<FeatureGroupDetail>(`/features/groups/${groupId}`);
            this.selectedGroup = detail;
        } catch {
            this.selectedGroup = null;
        } finally {
            this.detailLoading = false;
        }
    }

    async loadGroupStatistics(groupId: string) {
        this.statsLoading = true;
        try {
            this.groupStats = await api.get<GroupStatistics>(`/features/groups/${groupId}/statistics`);
        } catch {
            this.groupStats = null;
        } finally {
            this.statsLoading = false;
        }
    }

    async queryFeatures() {
        if (!this.queryEntityKeyValue.trim()) return;
        this.queryLoading = true;
        try {
            this.queryResults = await api.get<FeatureValue[]>(`/features/query?entity_key_value=${encodeURIComponent(this.queryEntityKeyValue.trim())}`);
        } catch {
            this.queryResults = [];
        } finally {
            this.queryLoading = false;
        }
    }

    async createGroup() {
        this.creating = true;
        try {
            await api.post('/features/groups', this.createForm);
            this.showCreateModal = false;
            this.createForm = { name: '', description: '', entity_key: 'entity_id', online_enabled: false, batch_enabled: true, schedule: '' };
            await this.loadGroups();
        } catch { /* empty */ } finally {
            this.creating = false;
        }
    }

    async computeFeatures(groupId: string) {
        try {
            await api.post('/features/compute', { feature_group_id: groupId });
            if (this.selectedGroup?.id === groupId) {
                await this.loadGroupDetail(groupId);
                await this.loadGroupStatistics(groupId);
            }
        } catch { /* empty */ }
    }

    /* ── Helpers ──────────────────────────────────────────────────────────── */

    private dataTypeBadge(dt: string) {
        const colors: Record<string, string> = {
            string: 'bg-purple-50 text-purple-700 border-purple-200',
            integer: 'bg-blue-50 text-blue-700 border-blue-200',
            float: 'bg-cyan-50 text-cyan-700 border-cyan-200',
            boolean: 'bg-amber-50 text-amber-700 border-amber-200',
            timestamp: 'bg-green-50 text-green-700 border-green-200',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[dt] || 'bg-gray-50 text-gray-700 border-gray-200'}">${dt}</span>`;
    }

    private servingBadge(enabled: boolean, label: string) {
        return enabled
            ? html`<span class="px-2 py-0.5 text-xs font-medium rounded bg-green-50 text-green-700 border border-green-200">${label}</span>`
            : html`<span class="px-2 py-0.5 text-xs font-medium rounded bg-gray-50 text-gray-400 border border-gray-200">${label}</span>`;
    }

    /* ── Render ───────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/features"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Feature Store">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Feature Store</h1>
                    <p class="text-sm text-gray-400 mt-1">Manage feature groups, compute statistics, and serve features online</p>
                </div>
                <div class="flex gap-2">
                    <button class="px-4 py-1.5 text-sm font-semibold border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors flex items-center gap-2"
                        @click=${() => this.loadGroups()}>
                        <svg class="w-4 h-4 ${this.loading ? 'animate-spin' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                        Refresh
                    </button>
                    <button class="px-4 py-1.5 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
                        @click=${() => { this.showCreateModal = true; }}>
                        + Create Feature Group
                    </button>
                </div>
            </div>

            ${this.error ? html`
            <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <svg class="w-5 h-5 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                    <span class="text-sm text-red-700">${this.error}</span>
                </div>
                <button class="text-sm text-red-600 hover:underline" @click=${() => this.loadGroups()}>Retry</button>
            </div>` : ''}

            ${this.loading ? html`
            <div class="text-center py-16" role="status" aria-live="polite">
                <div class="inline-block w-8 h-8 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin mb-3"></div>
                <div class="text-sm text-gray-400">Loading feature groups...</div>
            </div>` : html`
            <!-- Query Panel -->
            ${this.renderQueryPanel()}

            <!-- Feature Groups Table -->
            ${this.renderGroupsTable()}
            `}

            <!-- Detail Panel -->
            ${this.selectedGroup || this.detailLoading ? this.renderDetailPanel() : ''}

            <!-- Create Modal -->
            ${this.showCreateModal ? this.renderCreateModal() : ''}
        </main>`;
    }

    /* ── Query Panel ──────────────────────────────────────────────────────── */

    private renderQueryPanel() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 p-5 mb-6">
            <h2 class="text-sm font-semibold text-gray-700 mb-3">Query Features by Entity</h2>
            <div class="flex gap-3">
                <input type="text" class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                    placeholder="Enter entity_key_value (e.g. cust_12345)"
                    .value=${this.queryEntityKeyValue}
                    @input=${(e: Event) => { this.queryEntityKeyValue = (e.target as HTMLInputElement).value; }}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter') this.queryFeatures(); }}>
                <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors ${this.queryLoading ? 'opacity-50' : ''}"
                    ?disabled=${this.queryLoading}
                    @click=${() => this.queryFeatures()}>
                    ${this.queryLoading ? 'Querying...' : 'Query'}
                </button>
            </div>
            ${this.queryResults.length > 0 ? html`
            <div class="mt-4 overflow-x-auto">
                <table class="w-full text-sm" role="table" aria-label="Query results">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                        <th class="px-3 py-2">Feature</th>
                        <th class="px-3 py-2">Group</th>
                        <th class="px-3 py-2">Value</th>
                        <th class="px-3 py-2">Computed At</th>
                    </tr></thead>
                    <tbody>
                    ${this.queryResults.map(v => html`
                    <tr class="border-b border-gray-50">
                        <td class="px-3 py-2 font-medium">${v.feature_name}</td>
                        <td class="px-3 py-2 text-gray-500">${v.feature_group}</td>
                        <td class="px-3 py-2 font-mono text-xs">${JSON.stringify(v.value)}</td>
                        <td class="px-3 py-2 text-xs text-gray-400">${new Date(v.computed_at).toLocaleString()}</td>
                    </tr>`)}
                    </tbody>
                </table>
            </div>` : this.queryEntityKeyValue && !this.queryLoading ? html`
            <div class="mt-3 text-sm text-gray-400 text-center py-4">No features found for this entity.</div>` : ''}
        </div>`;
    }

    /* ── Groups Table ─────────────────────────────────────────────────────── */

    private renderGroupsTable() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Feature Groups</h2>
                <span class="text-xs text-gray-400">${this.groups.length} groups</span>
            </div>
            <table class="w-full text-sm" role="table" aria-label="Feature groups">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">Name</th>
                    <th class="px-5 py-3">Entity Key</th>
                    <th class="px-5 py-3">Features</th>
                    <th class="px-5 py-3">Serving</th>
                    <th class="px-5 py-3">Schedule</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.groups.length === 0 ? html`
                <tr><td colspan="6" class="px-5 py-16 text-center text-gray-400">
                    <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
                        <svg class="w-7 h-7 text-gray-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
                    </div>
                    <div class="text-sm font-semibold text-gray-600">No feature groups yet</div>
                    <div class="text-xs mt-2 text-gray-400">Create a feature group to start organizing and serving features.</div>
                </td></tr>` : ''}
                ${this.groups.map(g => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                    role="button" tabindex="0"
                    aria-label="Feature group: ${g.name}"
                    @click=${() => this.loadGroupDetail(g.id)}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.loadGroupDetail(g.id); } }}>
                    <td class="px-5 py-3">
                        <div class="font-semibold">${g.name}</div>
                        ${g.description ? html`<div class="text-xs text-gray-400 mt-0.5 truncate max-w-[300px]">${g.description}</div>` : ''}
                    </td>
                    <td class="px-5 py-3"><span class="px-2 py-0.5 text-xs bg-gray-100 rounded font-mono">${g.entity_key}</span></td>
                    <td class="px-5 py-3"><span class="text-sm font-semibold">${g.feature_count}</span></td>
                    <td class="px-5 py-3">
                        <div class="flex gap-1">${this.servingBadge(g.online_enabled, 'Online')}${this.servingBadge(g.batch_enabled, 'Batch')}</div>
                    </td>
                    <td class="px-5 py-3 text-xs text-gray-500 font-mono">${g.schedule || '—'}</td>
                    <td class="px-5 py-3" @click=${(e: Event) => e.stopPropagation()}>
                        <div class="flex gap-2">
                            <button class="text-xs text-blue-600 hover:underline" @click=${() => this.loadGroupDetail(g.id)}>Details</button>
                            <button class="text-xs text-green-600 hover:underline" @click=${() => this.computeFeatures(g.id)}>Compute</button>
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
            <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Loading feature group details">
                <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedGroup = null; }}></div>
                <div class="relative w-[720px] bg-white h-full flex items-center justify-center shadow-2xl border-l border-gray-200">
                    <div class="text-gray-400" role="status" aria-live="polite">Loading feature group details...</div>
                </div>
            </div>`;
        }

        const group = this.selectedGroup!;

        return html`
        <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Feature group: ${group.name}"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') { this.selectedGroup = null; } }}>
            <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedGroup = null; }}></div>
            <div class="relative w-[720px] bg-white h-full overflow-y-auto shadow-2xl border-l border-gray-200" tabindex="-1">
                <!-- Header -->
                <div class="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between z-10">
                    <div>
                        <h2 class="font-bold text-lg">${group.name}</h2>
                        <div class="flex items-center gap-2 mt-1">
                            <span class="px-2 py-0.5 text-xs bg-gray-100 rounded font-mono">${group.entity_key}</span>
                            ${this.servingBadge(group.online_enabled, 'Online')}
                            ${this.servingBadge(group.batch_enabled, 'Batch')}
                        </div>
                    </div>
                    <button class="text-gray-400 hover:text-ink" aria-label="Close" @click=${() => { this.selectedGroup = null; }}>✕</button>
                </div>

                <div class="p-6 space-y-8">
                    <!-- Group Info -->
                    <div class="grid grid-cols-3 gap-4">
                        <div class="p-3 bg-gray-50 rounded-lg">
                            <div class="text-xs text-gray-400">Features</div>
                            <div class="text-sm font-semibold mt-1">${group.features?.length ?? group.feature_count}</div>
                        </div>
                        <div class="p-3 bg-gray-50 rounded-lg">
                            <div class="text-xs text-gray-400">Schedule</div>
                            <div class="text-sm font-mono mt-1">${group.schedule || 'Manual'}</div>
                        </div>
                        <div class="p-3 bg-gray-50 rounded-lg">
                            <div class="text-xs text-gray-400">Created</div>
                            <div class="text-sm mt-1">${new Date(group.created_at).toLocaleDateString()}</div>
                        </div>
                    </div>

                    ${group.description ? html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-2">Description</h3>
                        <p class="text-sm text-gray-600">${group.description}</p>
                    </div>` : ''}

                    <!-- Features List -->
                    ${group.features && group.features.length > 0 ? html`
                    <div>
                        <div class="flex items-center justify-between mb-3">
                            <h3 class="text-xs font-semibold text-gray-500 uppercase">Features</h3>
                            <button class="text-xs text-blue-600 hover:underline"
                                @click=${() => this.loadGroupStatistics(group.id)}>
                                ${this.statsLoading ? 'Loading stats...' : 'Load Statistics'}
                            </button>
                        </div>
                        <div class="bg-white rounded-lg border border-gray-100 overflow-hidden">
                            <table class="w-full text-sm" role="table" aria-label="Features in group">
                                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                                    <th class="px-4 py-2.5">Name</th>
                                    <th class="px-4 py-2.5">Type</th>
                                    <th class="px-4 py-2.5">Source Expression</th>
                                </tr></thead>
                                <tbody>
                                ${group.features.map(f => html`
                                <tr class="border-b border-gray-50">
                                    <td class="px-4 py-2.5 font-medium">${f.name}</td>
                                    <td class="px-4 py-2.5">${this.dataTypeBadge(f.data_type)}</td>
                                    <td class="px-4 py-2.5 text-xs font-mono text-gray-500 truncate max-w-[300px]">${f.source_expression || '—'}</td>
                                </tr>`)}
                                </tbody>
                            </table>
                        </div>
                    </div>` : html`
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Features</h3>
                        <div class="text-sm text-gray-400 py-8 text-center">No features defined in this group.</div>
                    </div>`}

                    <!-- Statistics Section -->
                    ${this.groupStats ? this.renderStatistics() : ''}

                    <!-- Actions -->
                    <div class="flex gap-2 pt-4 border-t border-gray-100">
                        <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
                            @click=${() => this.computeFeatures(group.id)}>
                            Compute Features
                        </button>
                        <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                            @click=${() => { this.selectedGroup = null; }}>
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    /* ── Statistics ───────────────────────────────────────────────────────── */

    private renderStatistics() {
        const stats = this.groupStats!;
        if (!stats.features || stats.features.length === 0) {
            return html`
            <div>
                <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Statistics</h3>
                <div class="text-sm text-gray-400 py-8 text-center">No statistics available.</div>
            </div>`;
        }

        return html`
        <div>
            <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Feature Statistics</h3>
            <div class="bg-white rounded-lg border border-gray-100 overflow-x-auto">
                <table class="w-full text-sm" role="table" aria-label="Feature statistics">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                        <th class="px-4 py-2.5">Feature</th>
                        <th class="px-4 py-2.5">Mean</th>
                        <th class="px-4 py-2.5">Std</th>
                        <th class="px-4 py-2.5">Min</th>
                        <th class="px-4 py-2.5">Max</th>
                        <th class="px-4 py-2.5">Nulls %</th>
                    </tr></thead>
                    <tbody>
                    ${stats.features.map(f => html`
                    <tr class="border-b border-gray-50">
                        <td class="px-4 py-2.5 font-medium">${f.name}</td>
                        <td class="px-4 py-2.5 font-mono text-xs">${f.statistics?.mean != null ? f.statistics.mean.toFixed(4) : '—'}</td>
                        <td class="px-4 py-2.5 font-mono text-xs">${f.statistics?.std != null ? f.statistics.std.toFixed(4) : '—'}</td>
                        <td class="px-4 py-2.5 font-mono text-xs">${f.statistics?.min != null ? f.statistics.min.toFixed(4) : '—'}</td>
                        <td class="px-4 py-2.5 font-mono text-xs">${f.statistics?.max != null ? f.statistics.max.toFixed(4) : '—'}</td>
                        <td class="px-4 py-2.5 font-mono text-xs">${f.statistics?.nulls_pct != null ? f.statistics.nulls_pct.toFixed(2) + '%' : '—'}</td>
                    </tr>`)}
                    </tbody>
                </table>
            </div>
        </div>`;
    }

    /* ── Create Modal ─────────────────────────────────────────────────────── */

    private renderCreateModal() {
        return html`
        <div class="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Create feature group"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') { this.showCreateModal = false; } }}>
            <div class="absolute inset-0 bg-black/30" @click=${() => { this.showCreateModal = false; }}></div>
            <div class="relative bg-white rounded-2xl shadow-2xl w-[520px] max-h-[80vh] overflow-y-auto" tabindex="-1">
                <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                    <h2 class="font-bold text-lg">Create Feature Group</h2>
                    <button class="text-gray-400 hover:text-ink" @click=${() => { this.showCreateModal = false; }}>✕</button>
                </div>
                <div class="p-6 space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Name *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="e.g. customer_risk"
                            .value=${this.createForm.name}
                            @input=${(e: Event) => { this.createForm = { ...this.createForm, name: (e.target as HTMLInputElement).value }; }}>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Description</label>
                        <textarea class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10" rows="2"
                            placeholder="Human-readable description"
                            .value=${this.createForm.description}
                            @input=${(e: Event) => { this.createForm = { ...this.createForm, description: (e.target as HTMLTextAreaElement).value }; }}></textarea>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Entity Key *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="e.g. customer_id"
                            .value=${this.createForm.entity_key}
                            @input=${(e: Event) => { this.createForm = { ...this.createForm, entity_key: (e.target as HTMLInputElement).value }; }}>
                    </div>
                    <div class="flex gap-6">
                        <label class="flex items-center gap-2 text-sm cursor-pointer">
                            <input type="checkbox" .checked=${this.createForm.online_enabled}
                                @change=${(e: Event) => { this.createForm = { ...this.createForm, online_enabled: (e.target as HTMLInputElement).checked }; }}>
                            Online Enabled
                        </label>
                        <label class="flex items-center gap-2 text-sm cursor-pointer">
                            <input type="checkbox" .checked=${this.createForm.batch_enabled}
                                @change=${(e: Event) => { this.createForm = { ...this.createForm, batch_enabled: (e.target as HTMLInputElement).checked }; }}>
                            Batch Enabled
                        </label>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-600 mb-1">Schedule (cron)</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                            placeholder="e.g. 0 */6 * * * (every 6 hours)"
                            .value=${this.createForm.schedule}
                            @input=${(e: Event) => { this.createForm = { ...this.createForm, schedule: (e.target as HTMLInputElement).value }; }}>
                    </div>
                </div>
                <div class="px-6 py-4 border-t border-gray-100 flex items-center justify-end gap-2">
                    <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        @click=${() => { this.showCreateModal = false; }}>Cancel</button>
                    <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors ${this.creating ? 'opacity-50' : ''}"
                        ?disabled=${this.creating || !this.createForm.name.trim()}
                        @click=${() => this.createGroup()}>
                        ${this.creating ? 'Creating...' : 'Create Group'}
                    </button>
                </div>
            </div>
        </div>`;
    }
}
