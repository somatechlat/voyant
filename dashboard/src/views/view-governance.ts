import { LitElement, html, nothing } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-graph-view';

/* ──────────────────────────────────────────────────────────────────────
   Interfaces
   ────────────────────────────────────────────────────────────────────── */

interface CatalogColumn {
    name: string;
    type: string;
}

interface CatalogTable {
    name: string;
    columns?: CatalogColumn[];
    loadingColumns?: boolean;
}

type GovernanceTab = 'policies' | 'contracts' | 'quotas' | 'catalog' | 'lineage';

const TABS: Array<{ key: GovernanceTab; label: string }> = [
    { key: 'policies', label: 'Policies' },
    { key: 'contracts', label: 'Contracts' },
    { key: 'quotas', label: 'Quotas' },
    { key: 'catalog', label: 'Catalog' },
    { key: 'lineage', label: 'Lineage' },
];

@customElement('view-governance')
export class ViewGovernance extends LitElement {
    /* ── state ──────────────────────────────────────────────────────── */

    @state() tab: GovernanceTab = 'policies';
    @state() data: Record<string, unknown[]> = { policies: [], contracts: [], quotas: [] };
    @state() loading = true;

    // Catalog state
    @state() catalogSchema = '';
    @state() catalogTables: CatalogTable[] = [];
    @state() catalogLoading = false;
    @state() expandedTable: string | null = null;

    // Lineage state
    @state() lineageUrn = '';
    @state() lineageDepth = 3;
    @state() lineageLoading = false;
    @state() lineageNodes: Array<{ id: string; label: string; type: string; size?: number; color?: string }> = [];
    @state() lineageEdges: Array<{ id: string; source: string; target: string; label?: string }> = [];
    @state() lineageError = '';

    createRenderRoot() { return this; }

    /* ── lifecycle ──────────────────────────────────────────────────── */

    async connectedCallback() {
        super.connectedCallback();
        try {
            const [policies, contracts, quotas] = await Promise.all([
                api.get('/admin/governance/policies'),
                api.get('/admin/governance/contracts'),
                api.get('/admin/governance/quotas'),
            ]);
            this.data = { policies, contracts, quotas };
        } catch { /* empty */ }
        finally { this.loading = false; }
    }

    /* ── catalog helpers ────────────────────────────────────────────── */

    private async loadCatalog() {
        this.catalogLoading = true;
        try {
            const schema = this.catalogSchema || undefined;
            const qs = schema ? `?schema=${encodeURIComponent(schema)}` : '';
            const resp = await api.get<{ tables: string[]; schema: string }>(`/sql/tables${qs}`);
            this.catalogTables = (resp.tables || []).map(t => ({ name: t }));
            if (resp.schema && !this.catalogSchema) {
                this.catalogSchema = resp.schema;
            }
        } catch { this.catalogTables = []; }
        finally { this.catalogLoading = false; }
    }

    private async toggleTableColumns(tableName: string) {
        if (this.expandedTable === tableName) {
            this.expandedTable = null;
            return;
        }
        this.expandedTable = tableName;
        const table = this.catalogTables.find(t => t.name === tableName);
        if (!table || table.columns) return;

        table.loadingColumns = true;
        this.requestUpdate();
        try {
            const schema = this.catalogSchema || undefined;
            const qs = schema ? `?schema=${encodeURIComponent(schema)}` : '';
            const resp = await api.get<{ columns: CatalogColumn[] }>(
                `/sql/tables/${encodeURIComponent(tableName)}/columns${qs}`,
            );
            table.columns = resp.columns || [];
        } catch {
            table.columns = [];
        }
        finally {
            table.loadingColumns = false;
            this.requestUpdate();
        }
    }

    private onTabChange(t: GovernanceTab) {
        this.tab = t;
        if (t === 'catalog' && this.catalogTables.length === 0) {
            this.loadCatalog();
        }
    }

    /* ── render ─────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/governance"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8" role="main" aria-label="Governance management">
            <h1 class="text-2xl font-black font-display tracking-tight mb-6">Governance</h1>
            <div class="flex gap-1 mb-6 bg-white rounded-lg p-1 border border-gray-100 w-fit" role="tablist" aria-label="Governance sections">
                ${TABS.map(t => html`
                <button
                    class="px-4 py-2 text-sm font-semibold rounded-md transition-colors ${this.tab === t.key ? 'bg-brand text-white' : 'text-gray-500 hover:text-ink'}"
                    role="tab" aria-selected=${this.tab === t.key}
                    @click=${() => this.onTabChange(t.key)}
                >${t.label}</button>`)}
            </div>
            ${this.loading
                ? html`<div class="text-center text-gray-500 py-16" role="status" aria-live="polite">Loading...</div>`
                : html`
                <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
                    ${this.tab === 'policies' ? this.renderPoliciesTab() : nothing}
                    ${this.tab === 'contracts' ? this.renderContractsTab() : nothing}
                    ${this.tab === 'quotas' ? this.renderQuotasTab() : nothing}
                    ${this.tab === 'catalog' ? this.renderCatalogTab() : nothing}
                    ${this.tab === 'lineage' ? this.renderLineageTab() : nothing}
                </div>`}
        </main>`;
    }

    /* ══════════════════════════════════════════════════════════════════
       Policies Tab
       ══════════════════════════════════════════════════════════════════ */

    private renderPoliciesTab() {
        const rows = this.data.policies as Array<Record<string, string>>;
        return html`
        <table class="w-full text-sm" role="table" aria-label="Governance policies">
            <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase tracking-wider">
                <th class="px-5 py-3">Name</th>
                <th class="px-5 py-3">Type</th>
                <th class="px-5 py-3">Status</th>
                <th class="px-5 py-3">Level</th>
                <th class="px-5 py-3">Tenant</th>
            </tr></thead>
            <tbody>
            ${rows.length === 0
                ? html`<tr><td colspan="5" class="px-5 py-8 text-center text-gray-500">No policies found.</td></tr>`
                : rows.map(p => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50">
                    <td class="px-5 py-3 font-semibold">${p.name}</td>
                    <td class="px-5 py-3 text-xs font-mono">${p.policy_type}</td>
                    <td class="px-5 py-3">
                        <span class="inline-block px-2 py-0.5 text-xs font-semibold rounded-full ${p.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}">${p.status}</span>
                    </td>
                    <td class="px-5 py-3">${p.enforcement_level}</td>
                    <td class="px-5 py-3 text-gray-500 text-xs">${p.tenant_id}</td>
                </tr>`)}
            </tbody>
        </table>`;
    }

    /* ══════════════════════════════════════════════════════════════════
       Contracts Tab
       ══════════════════════════════════════════════════════════════════ */

    private renderContractsTab() {
        const rows = this.data.contracts as Array<Record<string, unknown>>;
        return html`
        <table class="w-full text-sm" role="table" aria-label="Governance contracts">
            <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase tracking-wider">
                <th class="px-5 py-3">Name</th>
                <th class="px-5 py-3">Dataset URN</th>
                <th class="px-5 py-3">Status</th>
                <th class="px-5 py-3">Version</th>
            </tr></thead>
            <tbody>
            ${rows.length === 0
                ? html`<tr><td colspan="4" class="px-5 py-8 text-center text-gray-500">No contracts found.</td></tr>`
                : rows.map(c => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50">
                    <td class="px-5 py-3 font-semibold">${c.name}</td>
                    <td class="px-5 py-3 text-xs font-mono">${c.dataset_urn}</td>
                    <td class="px-5 py-3">
                        <span class="inline-block px-2 py-0.5 text-xs font-semibold rounded-full ${c.status === 'active' ? 'bg-green-100 text-green-700' : c.status === 'draft' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-500'}">${c.status}</span>
                    </td>
                    <td class="px-5 py-3 text-xs font-mono">v${c.version}</td>
                </tr>`)}
            </tbody>
        </table>`;
    }

    /* ══════════════════════════════════════════════════════════════════
       Quotas Tab
       ══════════════════════════════════════════════════════════════════ */

    private renderQuotasTab() {
        const rows = this.data.quotas as Array<Record<string, unknown>>;
        return html`
        <table class="w-full text-sm" role="table" aria-label="Tenant quotas">
            <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase tracking-wider">
                <th class="px-5 py-3">Tenant</th>
                <th class="px-5 py-3">Tier</th>
                <th class="px-5 py-3">Jobs</th>
                <th class="px-5 py-3">Artifacts</th>
                <th class="px-5 py-3">Sources</th>
            </tr></thead>
            <tbody>
            ${rows.length === 0
                ? html`<tr><td colspan="5" class="px-5 py-8 text-center text-gray-500">No quota data found.</td></tr>`
                : rows.map(q => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50">
                    <td class="px-5 py-3 font-semibold">${q.tenant_id}</td>
                    <td class="px-5 py-3">
                        <span class="inline-block px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-700">${q.tier}</span>
                    </td>
                    <td class="px-5 py-3 text-xs">${q.jobs_today}/${q.jobs_limit}</td>
                    <td class="px-5 py-3 text-xs">${q.artifacts_gb}GB/${q.artifacts_limit_gb}GB</td>
                    <td class="px-5 py-3 text-xs">${q.sources_count}/${q.sources_limit}</td>
                </tr>`)}
            </tbody>
        </table>`;
    }

    /* ══════════════════════════════════════════════════════════════════
       Catalog Tab
       ══════════════════════════════════════════════════════════════════ */

    private renderCatalogTab() {
        return html`
        <div class="p-5">
            <div class="flex items-center gap-3 mb-4" role="search" aria-label="Browse database catalog">
                <label class="text-sm font-semibold text-gray-600" for="catalog-schema-input">Schema:</label>
                <input
                    type="text"
                    id="catalog-schema-input"
                    class="border border-gray-200 rounded-md px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-brand/40"
                    placeholder="default"
                    aria-label="Schema name"
                    .value=${this.catalogSchema}
                    @change=${(e: Event) => { this.catalogSchema = (e.target as HTMLInputElement).value; }}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter') this.loadCatalog(); }}
                />
                <button
                    class="px-3 py-1.5 text-sm font-semibold bg-brand text-white rounded-md hover:bg-brand/90 transition-colors"
                    aria-label="Browse schema tables"
                    @click=${() => this.loadCatalog()}
                >Browse</button>
            </div>
            ${this.catalogLoading
                ? html`<div class="text-center text-gray-500 py-12">Loading tables...</div>`
                : this.catalogTables.length === 0
                    ? html`<div class="text-center text-gray-500 py-12">No tables found. Enter a schema and click Browse.</div>`
                    : html`
                    <div class="text-xs text-gray-500 uppercase tracking-wider mb-3">
                        ${this.catalogTables.length} table${this.catalogTables.length !== 1 ? 's' : ''}
                        in <span class="font-mono text-gray-600">${this.catalogSchema || 'default'}</span>
                    </div>
                    <div class="border border-gray-100 rounded-lg overflow-hidden divide-y divide-gray-50">
                        ${this.catalogTables.map(t => html`
                        <div>
                            <button
                                class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                                aria-expanded=${this.expandedTable === t.name}
                                aria-label="Table ${t.name}: ${this.expandedTable === t.name ? 'collapse' : 'expand'} columns"
                                @click=${() => this.toggleTableColumns(t.name)}
                            >
                                <span class="flex items-center gap-2">
                                    <span class="text-gray-500 text-xs">
                                        ${this.expandedTable === t.name ? '&#9660;' : '&#9654;'}
                                    </span>
                                    <span class="font-semibold text-sm">${t.name}</span>
                                </span>
                                <span class="text-xs text-gray-500 font-mono">
                                    ${t.columns ? `${t.columns.length} columns` : ''}
                                </span>
                            </button>
                            ${this.expandedTable === t.name ? html`
                            <div class="bg-gray-50 border-t border-gray-100">
                                ${t.loadingColumns
                                    ? html`<div class="px-6 py-3 text-xs text-gray-500">Loading columns...</div>`
                                    : t.columns && t.columns.length > 0
                                        ? html`
                                        <table class="w-full text-xs">
                                            <thead><tr class="text-left text-gray-500 uppercase tracking-wider border-b border-gray-100">
                                                <th class="px-6 py-2">Column</th>
                                                <th class="px-6 py-2">Type</th>
                                            </tr></thead>
                                            <tbody>
                                            ${t.columns.map(col => html`
                                                <tr class="border-b border-gray-100 last:border-0 hover:bg-white transition-colors">
                                                    <td class="px-6 py-1.5 font-mono text-ink">${col.name}</td>
                                                    <td class="px-6 py-1.5 text-gray-500 font-mono">${col.type}</td>
                                                </tr>`)}
                                            </tbody>
                                        </table>`
                                        : html`<div class="px-6 py-3 text-xs text-gray-500">No columns found</div>`}
                            </div>` : nothing}
                        </div>`)}
                    </div>`}
        </div>`;
    }

    /* ══════════════════════════════════════════════════════════════════
       Lineage Tab
       ══════════════════════════════════════════════════════════════════ */

    private async loadLineage() {
        if (!this.lineageUrn.trim()) return;
        this.lineageLoading = true;
        this.lineageError = '';
        try {
            const result = await api.get<{
                nodes: Array<{ urn: string; name: string; node_type: string; platform?: string }>;
                edges: Array<{ source_urn: string; target_urn: string; relationship?: string }>;
            }>(`/governance/lineage/${encodeURIComponent(this.lineageUrn)}?depth=${this.lineageDepth}`);

            this.lineageNodes = (result.nodes || []).map(n => ({
                id: n.urn,
                label: n.name || n.urn.split('::').pop() || n.urn,
                type: n.node_type || n.platform || 'entity',
                size: 10,
                color: n.node_type === 'dataset' ? '#3B82F6' : n.node_type === 'transformation' ? '#8B5CF6' : '#22C55E',
            }));

            this.lineageEdges = (result.edges || []).map((e, i) => ({
                id: `le-${i}`,
                source: e.source_urn,
                target: e.target_urn,
                label: e.relationship || '',
            }));
        } catch (err) {
            this.lineageError = 'Failed to load lineage. Check the URN and try again.';
            this.lineageNodes = [];
            this.lineageEdges = [];
        } finally {
            this.lineageLoading = false;
        }
    }

    private renderLineageTab() {
        return html`
        <div class="p-5">
            <!-- Search bar -->
            <div class="flex items-center gap-3 mb-4">
                <input
                    type="text"
                    placeholder="Enter dataset URN (e.g. urn:li:dataset:...)"
                    .value=${this.lineageUrn}
                    @input=${(e: Event) => { this.lineageUrn = (e.target as HTMLInputElement).value; }}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter') this.loadLineage(); }}
                    class="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-brand"
                    aria-label="Lineage URN input"
                />
                <select .value=${String(this.lineageDepth)}
                    @change=${(e: Event) => { this.lineageDepth = Number((e.target as HTMLSelectElement).value); }}
                    class="px-3 py-2 border border-gray-200 rounded-lg text-sm" aria-label="Lineage depth">
                    <option value="1">Depth: 1</option>
                    <option value="2">Depth: 2</option>
                    <option value="3" selected>Depth: 3</option>
                    <option value="5">Depth: 5</option>
                </select>
                <button
                    class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                    @click=${() => this.loadLineage()}
                    ?disabled=${this.lineageLoading || !this.lineageUrn.trim()}
                    aria-label="Load lineage graph"
                >${this.lineageLoading ? 'Loading...' : 'Load Lineage'}</button>
            </div>

            ${this.lineageError ? html`<div class="text-red-500 text-sm mb-4" role="alert">${this.lineageError}</div>` : ''}

            ${this.lineageNodes.length > 0 ? html`
            <div class="mb-3 text-xs text-gray-500">
                ${this.lineageNodes.length} nodes · ${this.lineageEdges.length} relationships
            </div>
            <voyant-graph-view
                .nodes=${this.lineageNodes}
                .edges=${this.lineageEdges}
                apiUrl="/v1"
            ></voyant-graph-view>
            ` : !this.lineageLoading && !this.lineageError ? html`
            <div class="text-center py-16">
                <div class="text-4xl opacity-20 mb-3">🔗</div>
                <div class="text-gray-500 text-sm">Enter a dataset URN to visualize its upstream and downstream lineage graph.</div>
                <div class="text-gray-500 text-xs mt-2">Example: urn:li:dataset:(urn:li:dataPlatform:postgres,my_table,PROD)</div>
            </div>` : ''}
        </div>`;
    }
}
