import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-detail-panel';

interface Source {
    source_id: string;
    tenant_id: string;
    name: string;
    source_type: string;
    status: string;
    created_at: string;
    connection_config: Record<string, unknown> | null;
}

@customElement('view-sources')
export class ViewSources extends LitElement {
    @state() sources: Source[] = [];
    @state() loading = true;
    @state() selectedSource: Source | null = null;
    @state() detailOpen = false;

    // Action state
    @state() actionTab: 'info' | 'query' | 'search' | 'index' = 'info';
    @state() sqlQuery = '';
    @state() sqlResult: Record<string, unknown> | null = null;
    @state() sqlRunning = false;
    @state() searchQuery = '';
    @state() searchResults: Array<Record<string, unknown>> = [];
    @state() searchRunning = false;
    @state() indexText = '';
    @state() indexStatus = '';

    // Create form
    @state() showCreate = false;
    @state() createName = '';
    @state() createType = 'postgresql';
    @state() createHost = '';
    @state() createPort = '5432';
    @state() createDatabase = '';
    @state() creating = false;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.load();
    }

    async load() {
        this.loading = true;
        try { this.sources = await api.get<Source[]>('/admin/sources'); }
        catch { this.sources = []; }
        finally { this.loading = false; }
    }

    // ── Actions ─────────────────────────────────────────────────────────

    openSource(source: Source) {
        this.selectedSource = source;
        this.actionTab = 'info';
        this.sqlResult = null;
        this.searchResults = [];
        this.indexStatus = '';
        this.detailOpen = true;

        // Auto-set SQL query based on source type
        const cfg = source.connection_config || {};
        if (source.source_type === 'csv' && cfg.table_name) {
            this.sqlQuery = `SELECT * FROM ${cfg.table_name} LIMIT 20`;
        } else if (source.source_type === 'postgresql') {
            this.sqlQuery = 'SELECT * FROM information_schema.tables LIMIT 20';
        } else {
            this.sqlQuery = '';
        }
    }

    async runSQL() {
        if (!this.sqlQuery.trim()) return;
        this.sqlRunning = true;
        this.sqlResult = null;
        try {
            const res = await api.post('/admin/sql/execute', { sql: this.sqlQuery });
            this.sqlResult = res as Record<string, unknown>;
        } catch (e: unknown) {
            this.sqlResult = { error: (e as Error).message };
        } finally { this.sqlRunning = false; }
    }

    async runSearch() {
        if (!this.searchQuery.trim()) return;
        this.searchRunning = true;
        this.searchResults = [];
        try {
            this.searchResults = await api.post('/search/query', {
                query: this.searchQuery,
                limit: 10,
            }) as Array<Record<string, unknown>>;
        } catch { this.searchResults = []; }
        finally { this.searchRunning = false; }
    }

    async indexDocument() {
        if (!this.indexText.trim()) return;
        try {
            await api.post('/search/index', {
                text: this.indexText,
                metadata: { source: this.selectedSource?.name || '' },
            });
            this.indexStatus = 'Indexed successfully';
            this.indexText = '';
        } catch { this.indexStatus = 'Indexing failed'; }
    }

    async createSource() {
        if (!this.createName.trim() || !this.createHost.trim()) return;
        this.creating = true;
        try {
            await api.post('/sources', {
                name: this.createName,
                source_type: this.createType,
                connection_config: { host: this.createHost, port: this.createPort, database: this.createDatabase },
            });
            this.showCreate = false;
            this.createName = '';
            this.createHost = '';
            this.createDatabase = '';
            await this.load();
        } catch (e: unknown) {
            alert(`Create failed: ${(e as Error).message}`);
        } finally { this.creating = false; }
    }

    async deleteSource(id: string, name: string) {
        if (!confirm(`Delete "${name}"?`)) return;
        try {
            await api.del(`/sources/${id}`);
            if (this.selectedSource?.source_id === id) { this.detailOpen = false; }
            await this.load();
        } catch (e: unknown) { alert(`Delete failed: ${(e as Error).message}`); }
    }

    // ── Helpers ─────────────────────────────────────────────────────────

    private typeIcon(t: string): string {
        const m: Record<string, string> = {
            postgresql: '🐘', mysql: '🐬', mongodb: '🍃', csv: '📄',
            s3: '☁️', api: '🔗', trino: '⚡', redis: '🔴',
            elasticsearch: '🔍', milvus: '🧲', kafka: '📡',
            search_engine: '🌐', vector_knowledge: '📚', web: '🕷️',
        };
        return m[t] || '🗄️';
    }

    private statusBadge(s: string) {
        if (s === 'active' || s === 'connected') return html`<span class="voyant-badge voyant-badge-success">${s}</span>`;
        if (s === 'error' || s === 'failed') return html`<span class="voyant-badge voyant-badge-danger">${s}</span>`;
        return html`<span class="voyant-badge voyant-badge-warning">${s}</span>`;
    }

    private typeDefaults(t: string) {
        const d: Record<string, { port: string; ph: string }> = {
            postgresql: { port: '5432', ph: 'localhost' },
            mysql: { port: '3306', ph: 'localhost' },
            mongodb: { port: '27017', ph: 'localhost' },
            csv: { port: '', ph: '/path/to/file.csv' },
            s3: { port: '', ph: 's3://bucket' },
            api: { port: '', ph: 'https://api.example.com' },
        };
        return d[t] || d.postgresql;
    }

    // ── Render ──────────────────────────────────────────────────────────

    render() {
        return html`
        <saas-sidebar currentPath="/admin/sources"></saas-sidebar>
        <main class="ml-60 min-h-screen" style="background:var(--saas-bg-page)" role="main" aria-label="Data sources management">
            <!-- Header -->
            <div style="padding:32px 32px 0;display:flex;align-items:center;justify-content:space-between">
                <div>
                    <h1 style="font-size:28px;font-weight:900;font-family:Inter,system-ui,sans-serif;letter-spacing:-0.02em">Sources</h1>
                    <p style="font-size:13px;color:var(--saas-text-secondary);margin-top:4px">${this.sources.length} data sources · Click a source to query, search, or index</p>
                </div>
                <button class="voyant-btn voyant-btn-primary" aria-expanded=${this.showCreate} aria-label="Create new source" @click=${() => { this.showCreate = !this.showCreate; }}>+ New Source</button>
            </div>

            <!-- Create Form -->
            ${this.showCreate ? html`
            <div style="margin:16px 32px;padding:20px;background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px">
                <h3 style="font-size:13px;font-weight:600;margin-bottom:12px">Create New Source</h3>
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px">
                    <div><label style="font-size:11px;color:var(--saas-text-muted);display:block;margin-bottom:4px">Name *</label>
                    <input class="voyant-input" placeholder="My Database" .value=${this.createName} @input=${(e: Event) => { this.createName = (e.target as HTMLInputElement).value; }}></div>
                    <div><label style="font-size:11px;color:var(--saas-text-muted);display:block;margin-bottom:4px">Type</label>
                    <select class="voyant-input" .value=${this.createType} @change=${(e: Event) => { this.createType = (e.target as HTMLSelectElement).value; this.createPort = this.typeDefaults(this.createType).port; }}>
                        <option value="postgresql">PostgreSQL</option><option value="mysql">MySQL</option><option value="mongodb">MongoDB</option><option value="csv">CSV File</option><option value="s3">S3</option><option value="api">REST API</option>
                    </select></div>
                    <div><label style="font-size:11px;color:var(--saas-text-muted);display:block;margin-bottom:4px">Host *</label>
                    <input class="voyant-input" .value=${this.createHost} placeholder=${this.typeDefaults(this.createType).ph} @input=${(e: Event) => { this.createHost = (e.target as HTMLInputElement).value; }}></div>
                    <div style="display:flex;align-items:flex-end;gap:8px">
                        <button class="voyant-btn voyant-btn-primary" ?disabled=${this.creating} @click=${() => this.createSource()}>Create</button>
                        <button class="voyant-btn" @click=${() => { this.showCreate = false; }}>Cancel</button>
                    </div>
                </div>
            </div>` : ''}

            <!-- Source Cards -->
            ${this.loading ? html`<div role="status" aria-live="polite" style="text-align:center;padding:60px;color:var(--saas-text-muted)">Loading...</div>` : html`
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;padding:0 32px 32px" aria-live="polite">
                ${this.sources.map(s => html`
                <div class="voyant-card" role="button" tabindex="0" aria-label="Source: ${s.name}, type ${s.source_type}, status ${s.status}" style="padding:20px;cursor:pointer" @click=${() => this.openSource(s)} @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.openSource(s); } }}>
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
                        <div style="width:40px;height:40px;border-radius:10px;background:var(--saas-brand-light);display:flex;align-items:center;justify-content:center;font-size:18px">${this.typeIcon(s.source_type)}</div>
                        <div style="flex:1;min-width:0">
                            <div style="font-size:14px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${s.name}</div>
                            <div style="font-size:11px;color:var(--saas-text-muted)">${s.source_type}</div>
                        </div>
                        ${this.statusBadge(s.status)}
                    </div>
                    ${s.connection_config?.description ? html`
                    <p style="font-size:12px;color:var(--saas-text-secondary);margin-bottom:8px;line-height:1.4">${String(s.connection_config.description).slice(0, 80)}</p>
                    ` : ''}
                    <div style="display:flex;gap:6px;flex-wrap:wrap">
                        ${['postgresql', 'trino', 'csv', 'web', 'vector_knowledge'].includes(s.source_type) ? html`
                        <span style="font-size:10px;padding:2px 8px;border-radius:4px;background:var(--saas-info-bg);color:var(--saas-info)">Queryable</span>` : ''}
                        ${s.source_type === 'vector_knowledge' ? html`
                        <span style="font-size:10px;padding:2px 8px;border-radius:4px;background:var(--saas-success-bg);color:var(--saas-success)">Searchable</span>` : ''}
                        ${s.source_type === 'csv' || s.source_type === 'web' ? html`
                        <span style="font-size:10px;padding:2px 8px;border-radius:4px;background:var(--saas-warning-bg);color:var(--saas-warning)">Indexable</span>` : ''}
                    </div>
                </div>`)}
            </div>`}

            <!-- Detail Panel -->
            <voyant-detail-panel
                .open=${this.detailOpen}
                .title=${this.selectedSource?.name || ''}
                .subtitle=${this.selectedSource?.source_type || ''}
                .width=${560}
                @close=${() => { this.detailOpen = false; }}
            >
                ${this.selectedSource ? html`
                <div>
                    <!-- Action tabs -->
                    <div class="voyant-tabs" role="tablist" aria-label="Source action tabs" style="margin-bottom:16px">
                        <button class="voyant-tab ${this.actionTab === 'info' ? 'active' : ''}" role="tab" aria-selected=${this.actionTab === 'info'} @click=${() => { this.actionTab = 'info'; }}>Info</button>
                        <button class="voyant-tab ${this.actionTab === 'query' ? 'active' : ''}" role="tab" aria-selected=${this.actionTab === 'query'} @click=${() => { this.actionTab = 'query'; }}>SQL Query</button>
                        <button class="voyant-tab ${this.actionTab === 'search' ? 'active' : ''}" role="tab" aria-selected=${this.actionTab === 'search'} @click=${() => { this.actionTab = 'search'; }}>Search</button>
                        <button class="voyant-tab ${this.actionTab === 'index' ? 'active' : ''}" role="tab" aria-selected=${this.actionTab === 'index'} @click=${() => { this.actionTab = 'index'; }}>Index</button>
                    </div>

                    <!-- INFO TAB -->
                    ${this.actionTab === 'info' ? html`
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px">
                        <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover)"><div style="font-size:11px;color:var(--saas-text-muted)">Type</div><div style="font-size:13px;font-weight:600">${this.selectedSource.source_type}</div></div>
                        <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover)"><div style="font-size:11px;color:var(--saas-text-muted)">Status</div><div style="font-size:13px;font-weight:600">${this.selectedSource.status}</div></div>
                        <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover)"><div style="font-size:11px;color:var(--saas-text-muted)">Tenant</div><div style="font-size:13px;font-weight:600">${this.selectedSource.tenant_id}</div></div>
                        <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover)"><div style="font-size:11px;color:var(--saas-text-muted)">Created</div><div style="font-size:13px;font-weight:600">${new Date(this.selectedSource.created_at).toLocaleDateString()}</div></div>
                    </div>
                    <h4 style="font-size:11px;font-weight:700;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Connection Config</h4>
                    <div style="background:var(--saas-bg-hover);border-radius:8px;padding:12px;margin-bottom:16px;max-height:200px;overflow:auto">
                        <pre style="font-size:11px;font-family:JetBrains Mono,monospace;white-space:pre-wrap;color:var(--saas-text-primary);margin:0">${JSON.stringify(this.selectedSource.connection_config || {}, null, 2)}</pre>
                    </div>
                    <button class="voyant-btn" style="color:#EF4444;border-color:#FCA5A5" @click=${() => this.deleteSource(this.selectedSource!.source_id, this.selectedSource!.name)}>Delete Source</button>
                    ` : ''}

                    <!-- SQL QUERY TAB -->
                    ${this.actionTab === 'query' ? html`
                    <div>
                        <textarea class="voyant-input" style="font-family:JetBrains Mono,monospace;font-size:12px;height:100px;resize:vertical;margin-bottom:8px"
                            placeholder="SELECT * FROM table_name LIMIT 10"
                            .value=${this.sqlQuery}
                            @input=${(e: Event) => { this.sqlQuery = (e.target as HTMLTextAreaElement).value; }}></textarea>
                        <button class="voyant-btn voyant-btn-primary" style="margin-bottom:12px" ?disabled=${this.sqlRunning} @click=${() => this.runSQL()}>
                            ${this.sqlRunning ? 'Running...' : '▶ Run Query'}
                        </button>
                        ${this.sqlResult ? html`
                        <div style="background:var(--saas-bg-hover);border-radius:8px;padding:12px;max-height:300px;overflow:auto">
                            ${this.sqlResult.error ? html`
                            <div style="color:#EF4444;font-size:12px">${String(this.sqlResult.error)}</div>
                            ` : html`
                            <div style="font-size:11px;color:var(--saas-text-muted);margin-bottom:8px">${(this.sqlResult as Record<string, unknown>).row_count || 0} rows · ${(this.sqlResult as Record<string, unknown>).execution_time_ms || 0}ms</div>
                            <table role="table" aria-label="SQL query results" style="width:100%;font-size:11px;font-family:JetBrains Mono,monospace;border-collapse:collapse">
                                <thead><tr>${((this.sqlResult as Record<string, unknown>).columns as string[] || []).map((c: string) => html`<th style="padding:4px 8px;text-align:left;border-bottom:1px solid var(--saas-border);font-weight:600">${c}</th>`)}</tr></thead>
                                <tbody>${((this.sqlResult as Record<string, unknown>).rows as unknown[][] || []).slice(0, 20).map((r: unknown[]) => html`
                                    <tr>${(r as unknown[]).map((v: unknown) => html`<td style="padding:4px 8px;border-bottom:1px solid var(--saas-border-subtle)">${v ?? '—'}</td>`)}</tr>`)}</tbody>
                            </table>`}
                        </div>` : ''}
                    </div>
                    ` : ''}

                    <!-- SEARCH TAB -->
                    ${this.actionTab === 'search' ? html`
                    <div>
                        <div style="display:flex;gap:8px;margin-bottom:12px" role="search" aria-label="Semantic search">
                            <input class="voyant-input" style="flex:1" placeholder="Semantic search query..." aria-label="Search query" .value=${this.searchQuery}
                                @input=${(e: Event) => { this.searchQuery = (e.target as HTMLInputElement).value; }}
                                @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter') this.runSearch(); }}>
                            <button class="voyant-btn voyant-btn-primary" ?disabled=${this.searchRunning} aria-label="Run search" @click=${() => this.runSearch()}>Search</button>
                        </div>
                        ${this.searchResults.length > 0 ? html`
                        <div style="display:flex;flex-direction:column;gap:8px">
                            ${this.searchResults.map(r => html`
                            <div style="padding:12px;border-radius:8px;border:1px solid var(--saas-border)">
                                <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                                    <span style="font-size:11px;font-family:JetBrains Mono,monospace;color:var(--saas-text-muted)">${r.id}</span>
                                    <span style="font-size:11px;font-weight:600;color:var(--saas-brand)">${((r.score as number) * 100).toFixed(1)}%</span>
                                </div>
                                <!-- TODO: text_preview not guaranteed in search result schema; stringify fallback is acceptable -->
                                <p style="font-size:12px;color:var(--saas-text-primary);line-height:1.4">${(r.metadata as Record<string, unknown>)?.text_preview || JSON.stringify(r.metadata).slice(0, 200)}</p>
                            </div>`)}
                        </div>` : this.searchQuery ? html`<div style="text-align:center;padding:20px;color:var(--saas-text-muted);font-size:12px">No results</div>` : ''}
                    </div>
                    ` : ''}

                    <!-- INDEX TAB -->
                    ${this.actionTab === 'index' ? html`
                    <div>
                        <p style="font-size:12px;color:var(--saas-text-secondary);margin-bottom:12px">Index text into the vector search engine. Agents and humans can then search it semantically.</p>
                        <textarea class="voyant-input" style="font-family:JetBrains Mono,monospace;font-size:12px;height:120px;resize:vertical;margin-bottom:8px"
                            placeholder="Paste text to index..."
                            .value=${this.indexText}
                            @input=${(e: Event) => { this.indexText = (e.target as HTMLTextAreaElement).value; }}></textarea>
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <span style="font-size:11px;color:${this.indexStatus.includes('success') ? 'var(--saas-success)' : 'var(--saas-text-muted)'}">${this.indexStatus}</span>
                            <button class="voyant-btn voyant-btn-primary" @click=${() => this.indexDocument()}>Index Document</button>
                        </div>
                    </div>
                    ` : ''}
                </div>
                ` : ''}
            </voyant-detail-panel>
        </main>`;
    }
}
