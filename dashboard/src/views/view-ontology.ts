import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-graph-view';
import '../components/voyant-data-table';
import '../components/voyant-detail-panel';
import '../components/voyant-metric-card';

interface ObjectType {
    id: string;
    name: string;
    description: string;
    version: number;
    property_count: number;
    instance_count: number;
    properties?: Array<{ name: string; type: string; required: boolean }>;
}

interface LinkType {
    id: string;
    name: string;
    source_type: string;
    target_type: string;
    cardinality: string;
}

@customElement('view-ontology')
export class ViewOntology extends LitElement {
    @state() types: ObjectType[] = [];
    @state() links: LinkType[] = [];
    @state() loading = true;
    @state() view: 'graph' | 'table' | 'grid' = 'graph';
    @state() selectedType: ObjectType | null = null;
    @state() detailOpen = false;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this._loadData();
    }

    async _loadData() {
        this.loading = true;
        try {
            const [typesRes, linksRes] = await Promise.all([
                api.get('/admin/ontology/types').catch(() => []),
                api.get('/admin/ontology/links').catch(() => []),
            ]);
            this.types = (typesRes as ObjectType[]) || [];
            this.links = (linksRes as LinkType[]) || [];
        } catch { /* empty */ }
        finally { this.loading = false; }
    }

    private _graphNodes() {
        return this.types.map(t => ({
            id: t.id,
            label: t.name,
            type: 'object_type',
            size: Math.max(8, Math.min(24, (t.instance_count || 0) / 100 + 8)),
            data: t as unknown as Record<string, unknown>,
        }));
    }

    private _graphEdges() {
        return this.links.map((l, i) => ({
            id: l.id || `link-${i}`,
            source: this.types.find(t => t.name === l.source_type)?.id || '',
            target: this.types.find(t => t.name === l.target_type)?.id || '',
            label: l.name,
        })).filter(e => e.source && e.target);
    }

    private _onNodeClick(e: CustomEvent) {
        const node = e.detail;
        this.selectedType = node.data as ObjectType;
        this.detailOpen = true;
    }

    private _tableColumns() {
        return [
            { key: 'name', label: 'Name', sortable: true },
            { key: 'description', label: 'Description', sortable: true },
            { key: 'property_count', label: 'Properties', sortable: true, format: 'number' as const },
            { key: 'instance_count', label: 'Instances', sortable: true, format: 'number' as const },
            { key: 'version', label: 'Version', sortable: true },
        ];
    }

    private _tableRows() {
        return this.types.map(t => ({
            name: t.name,
            description: t.description || '—',
            property_count: t.property_count,
            instance_count: t.instance_count,
            version: `v${t.version}`,
        }));
    }

    render() {
        const totalInstances = this.types.reduce((s, t) => s + (t.instance_count || 0), 0);
        const totalProperties = this.types.reduce((s, t) => s + (t.property_count || 0), 0);

        return html`
        <saas-sidebar currentPath="/admin/ontology"></saas-sidebar>
        <main class="ml-60 min-h-screen" style="background:var(--saas-bg-page)">
            <!-- Header -->
            <div style="padding:32px 32px 0;display:flex;align-items:center;justify-content:space-between">
                <div>
                    <h1 style="font-size:28px;font-weight:900;font-family:Geist,Inter,system-ui,sans-serif;letter-spacing:-0.02em;color:var(--saas-text-primary)">Ontology Explorer</h1>
                    <p style="font-size:13px;color:var(--saas-text-secondary);margin-top:4px">Palantir-grade knowledge graph — ${this.types.length} types, ${this.links.length} relationships, ${totalInstances.toLocaleString()} instances</p>
                </div>
                <div class="voyant-tabs">
                    <button class="voyant-tab ${this.view === 'graph' ? 'active' : ''}" @click=${() => { this.view = 'graph'; }}>🕸️ Graph</button>
                    <button class="voyant-tab ${this.view === 'table' ? 'active' : ''}" @click=${() => { this.view = 'table'; }}>📋 Table</button>
                    <button class="voyant-tab ${this.view === 'grid' ? 'active' : ''}" @click=${() => { this.view = 'grid'; }}>⊞ Grid</button>
                </div>
            </div>

            <!-- Metrics -->
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;padding:24px 32px">
                <voyant-metric-card label="Object Types" value="${this.types.length}" icon="📐" color="#FF4D00"></voyant-metric-card>
                <voyant-metric-card label="Link Types" value="${this.links.length}" icon="🔗" color="#3B82F6"></voyant-metric-card>
                <voyant-metric-card label="Total Properties" value="${totalProperties}" icon="🏷️" color="#8B5CF6"></voyant-metric-card>
                <voyant-metric-card label="Total Instances" value="${totalInstances.toLocaleString()}" icon="📦" color="#22C55E"></voyant-metric-card>
            </div>

            ${this.loading ? html`<div style="text-align:center;padding:80px;color:var(--saas-text-muted)">Loading ontology...</div>` : html`

            <!-- Graph View -->
            ${this.view === 'graph' ? html`
            <div style="padding:0 32px 32px">
                <div class="voyant-card" style="height:560px;overflow:hidden">
                    <voyant-graph-view
                        .nodes=${this._graphNodes()}
                        .edges=${this._graphEdges()}
                        @node-click=${this._onNodeClick}
                        style="height:100%"
                    ></voyant-graph-view>
                </div>
            </div>
            ` : ''}

            <!-- Table View -->
            ${this.view === 'table' ? html`
            <div style="padding:0 32px 32px">
                <div class="voyant-card" style="padding:20px">
                    <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Object Types</h3>
                    <voyant-data-table
                        .columns=${this._tableColumns()}
                        .rows=${this._tableRows()}
                        .exportable=${true}
                        .filterable=${true}
                    ></voyant-data-table>
                </div>
                <div class="voyant-card" style="padding:20px;margin-top:16px">
                    <h3 style="font-size:14px;font-weight:600;margin-bottom:16px">Link Types</h3>
                    <voyant-data-table
                        .columns=${[
                            { key: 'name', label: 'Name', sortable: true },
                            { key: 'source_type', label: 'Source', sortable: true },
                            { key: 'target_type', label: 'Target', sortable: true },
                            { key: 'cardinality', label: 'Cardinality', sortable: true },
                        ]}
                        .rows=${this.links.map(l => ({ name: l.name, source_type: l.source_type, target_type: l.target_type, cardinality: l.cardinality }))}
                        .exportable=${true}
                    ></voyant-data-table>
                </div>
            </div>
            ` : ''}

            <!-- Grid View -->
            ${this.view === 'grid' ? html`
            <div style="padding:0 32px 32px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px">
                ${this.types.map(t => html`
                <div class="voyant-card" style="padding:20px;cursor:pointer" @click=${() => { this.selectedType = t; this.detailOpen = true; }}>
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
                        <div style="width:36px;height:36px;border-radius:10px;background:var(--saas-brand-light);display:flex;align-items:center;justify-content:center;font-size:16px">📐</div>
                        <div>
                            <div style="font-size:14px;font-weight:700;color:var(--saas-text-primary)">${t.name}</div>
                            <div style="font-size:11px;color:var(--saas-text-muted)">v${t.version}</div>
                        </div>
                    </div>
                    <p style="font-size:12px;color:var(--saas-text-secondary);margin-bottom:16px;min-height:32px">${t.description || 'No description'}</p>
                    <div style="display:flex;gap:16px;font-size:11px;color:var(--saas-text-muted)">
                        <span>${t.property_count} properties</span>
                        <span>${(t.instance_count || 0).toLocaleString()} instances</span>
                    </div>
                    <div style="display:flex;gap:6px;margin-top:12px">
                        ${this.links.filter(l => l.source_type === t.name || l.target_type === t.name).slice(0, 3).map(l => html`
                        <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:var(--saas-info-bg);color:var(--saas-info)">${l.name}</span>
                        `)}
                    </div>
                </div>`)}
                ${this.types.length === 0 ? html`<div style="grid-column:1/-1;text-align:center;padding:80px;color:var(--saas-text-muted)">No object types defined. Create your first type to start building your ontology.</div>` : ''}
            </div>
            ` : ''}

            `}

            <!-- Detail Panel -->
            <voyant-detail-panel
                .open=${this.detailOpen}
                .title=${this.selectedType?.name || ''}
                .subtitle=${`Object Type · v${this.selectedType?.version || 1}`}
                @close=${() => { this.detailOpen = false; }}
            >
                ${this.selectedType ? html`
                <div style="font-family:Inter,system-ui,sans-serif">
                    <p style="font-size:13px;color:var(--saas-text-secondary);margin-bottom:24px">${this.selectedType.description || 'No description'}</p>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:24px">
                        <div style="padding:12px;border-radius:8px;background:var(--saas-bg-hover)">
                            <div style="font-size:20px;font-weight:800;color:var(--saas-text-primary)">${this.selectedType.property_count}</div>
                            <div style="font-size:11px;color:var(--saas-text-muted)">Properties</div>
                        </div>
                        <div style="padding:12px;border-radius:8px;background:var(--saas-bg-hover)">
                            <div style="font-size:20px;font-weight:800;color:var(--saas-text-primary)">${(this.selectedType.instance_count || 0).toLocaleString()}</div>
                            <div style="font-size:11px;color:var(--saas-text-muted)">Instances</div>
                        </div>
                    </div>

                    <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Connected Links</h4>
                    <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:24px">
                        ${this.links.filter(l => l.source_type === this.selectedType!.name || l.target_type === this.selectedType!.name).map(l => html`
                        <div style="display:flex;align-items:center;gap:8px;padding:10px;border-radius:8px;border:1px solid var(--saas-border)">
                            <span style="font-size:14px">🔗</span>
                            <div style="flex:1">
                                <div style="font-size:12px;font-weight:600;color:var(--saas-text-primary)">${l.name}</div>
                                <div style="font-size:11px;color:var(--saas-text-muted)">${l.source_type} → ${l.target_type} · ${l.cardinality}</div>
                            </div>
                        </div>`)}
                        ${this.links.filter(l => l.source_type === this.selectedType!.name || l.target_type === this.selectedType!.name).length === 0 ? html`
                        <div style="font-size:12px;color:var(--saas-text-muted);padding:12px;text-align:center">No links defined</div>` : ''}
                    </div>

                    <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Actions</h4>
                    <div style="display:flex;flex-direction:column;gap:8px">
                        <button class="voyant-btn-primary voyant-btn" style="width:100%;justify-content:center">View Objects</button>
                        <button class="voyant-btn" style="width:100%;justify-content:center">Create Object</button>
                        <button class="voyant-btn" style="width:100%;justify-content:center">Execute Action</button>
                        <button class="voyant-btn" style="width:100%;justify-content:center">Run Function</button>
                    </div>
                </div>
                ` : ''}
            </voyant-detail-panel>
        </main>`;
    }
}
