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
    datahub_urn: string | null;
    connection_config: Record<string, unknown> | null;
}

@customElement('view-sources')
export class ViewSources extends LitElement {
    @state() sources: Source[] = [];
    @state() loading = true;
    @state() selectedSource: Source | null = null;
    @state() detailOpen = false;

    // Create form
    @state() showCreate = false;
    @state() createName = '';
    @state() createType = 'postgresql';
    @state() createHost = '';
    @state() createPort = '5432';
    @state() createDatabase = '';
    @state() createUser = '';
    @state() createPassword = '';
    @state() creating = false;
    @state() createResult = '';

    // Edit state
    @state() editing = false;
    @state() editName = '';
    @state() editConfig = '';
    @state() editSaving = false;

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

    async createSource() {
        if (!this.createName.trim() || !this.createHost.trim()) return;
        this.creating = true;
        this.createResult = '';
        try {
            const connection_config: Record<string, string> = {
                host: this.createHost,
                port: this.createPort,
                database: this.createDatabase,
            };
            await api.post('/sources', {
                name: this.createName,
                source_type: this.createType,
                connection_config,
            });
            this.createResult = 'Source created successfully';
            this.showCreate = false;
            this.createName = '';
            this.createHost = '';
            this.createDatabase = '';
            await this.load();
        } catch (e: unknown) {
            this.createResult = `Error: ${e instanceof Error ? e.message : 'Failed'}`;
        } finally { this.creating = false; }
    }

    async deleteSource(id: string, name: string) {
        if (!confirm(`Delete source "${name}"? This cannot be undone.`)) return;
        try {
            await api.del(`/admin/sources/${id}`);
            if (this.selectedSource?.source_id === id) {
                this.detailOpen = false;
                this.selectedSource = null;
            }
            await this.load();
        } catch (e: unknown) {
            alert(`Delete failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
        }
    }

    openDetail(source: Source) {
        this.selectedSource = source;
        this.editing = false;
        this.editName = source.name;
        this.editConfig = JSON.stringify(source.connection_config || {}, null, 2);
        this.detailOpen = true;
    }

    async saveEdit() {
        if (!this.selectedSource) return;
        this.editSaving = true;
        try {
            let config: Record<string, unknown> | undefined;
            try { config = JSON.parse(this.editConfig); } catch { config = undefined; }

            await api.put(`/sources/${this.selectedSource.source_id}`, {
                name: this.editName,
                connection_config: config,
            });
            this.editing = false;
            await this.load();
            // Refresh selected source
            this.selectedSource = this.sources.find(s => s.source_id === this.selectedSource?.source_id) || null;
        } catch (e: unknown) {
            alert(`Save failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
        } finally { this.editSaving = false; }
    }

    private statusColor(s: string): string {
        if (s === 'active' || s === 'connected') return 'bg-green-50 text-green-700 border-green-200';
        if (s === 'error' || s === 'failed') return 'bg-red-50 text-red-700 border-red-200';
        return 'bg-amber-50 text-amber-700 border-amber-200';
    }

    private typeIcon(t: string): string {
        const icons: Record<string, string> = {
            postgresql: '🐘', mysql: '🐬', mongodb: '🍃', csv: '📄',
            s3: '☁️', api: '🔗', trino: '⚡', redis: '🔴',
            elasticsearch: '🔍', milvus: '🧲', kafka: '📡',
            search_engine: '🌐', vector_knowledge: '📚', web: '🕷️',
        };
        return icons[t] || '🗄️';
    }

    private typeDefaults(t: string) {
        const d: Record<string, { port: string; placeholder: string }> = {
            postgresql: { port: '5432', placeholder: 'localhost' },
            mysql: { port: '3306', placeholder: 'localhost' },
            mongodb: { port: '27017', placeholder: 'localhost' },
            csv: { port: '', placeholder: '/path/to/file.csv' },
            s3: { port: '', placeholder: 's3://bucket/path' },
            api: { port: '', placeholder: 'https://api.example.com' },
        };
        return d[t] || d.postgresql;
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/sources"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Sources</h1>
                    <p class="text-sm text-gray-400 mt-1">${this.sources.length} data sources configured</p>
                    ${this.createResult ? html`<p class="text-sm mt-1 ${this.createResult.startsWith('Error') ? 'text-red-600' : 'text-green-600'}">${this.createResult}</p>` : ''}
                </div>
                <button class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors" @click=${() => { this.showCreate = !this.showCreate; }}>+ New Source</button>
            </div>

            <!-- Create Source Form -->
            ${this.showCreate ? html`
            <div class="bg-white rounded-xl border border-gray-100 p-6 mb-6">
                <h3 class="text-sm font-semibold text-gray-500 mb-4">Create New Source</h3>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Name *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" placeholder="My Database" .value=${this.createName} @input=${(e: Event) => { this.createName = (e.target as HTMLInputElement).value; }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Type</label>
                        <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white" .value=${this.createType} @change=${(e: Event) => { this.createType = (e.target as HTMLSelectElement).value; this.createPort = this.typeDefaults(this.createType).port; }}>
                            <option value="postgresql">PostgreSQL</option>
                            <option value="mysql">MySQL</option>
                            <option value="mongodb">MongoDB</option>
                            <option value="csv">CSV File</option>
                            <option value="s3">S3 Bucket</option>
                            <option value="api">REST API</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Host/Path *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono" .value=${this.createHost} placeholder=${this.typeDefaults(this.createType).placeholder} @input=${(e: Event) => { this.createHost = (e.target as HTMLInputElement).value; }} />
                    </div>
                    ${this.createType !== 'csv' && this.createType !== 's3' && this.createType !== 'api' ? html`
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Port</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono" .value=${this.createPort} @input=${(e: Event) => { this.createPort = (e.target as HTMLInputElement).value; }} />
                    </div>` : html`<div></div>`}
                </div>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    ${this.createType !== 'csv' && this.createType !== 's3' ? html`
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Database</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono" placeholder="mydb" .value=${this.createDatabase} @input=${(e: Event) => { this.createDatabase = (e.target as HTMLInputElement).value; }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Username</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono" .value=${this.createUser} @input=${(e: Event) => { this.createUser = (e.target as HTMLInputElement).value; }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Password</label>
                        <input type="password" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" .value=${this.createPassword} @input=${(e: Event) => { this.createPassword = (e.target as HTMLInputElement).value; }} />
                    </div>` : html`<div></div><div></div><div></div>`}
                    <div class="flex items-end">
                        <button class="w-full px-4 py-2 text-sm font-bold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.creating ? 'opacity-50' : ''}" ?disabled=${this.creating} @click=${() => this.createSource()}>
                            ${this.creating ? 'Creating...' : 'Create Source'}
                        </button>
                    </div>
                </div>
            </div>` : ''}

            <!-- Sources Grid -->
            ${this.loading ? html`<div class="text-center text-gray-400 py-16">Loading...</div>` : html`
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                ${this.sources.map(s => html`
                <div class="bg-white rounded-xl border border-gray-100 p-5 cursor-pointer hover:border-brand hover:shadow-md transition-all"
                    @click=${() => this.openDetail(s)}>
                    <div class="flex items-center gap-3 mb-3">
                        <div class="w-10 h-10 rounded-lg bg-gray-50 flex items-center justify-center text-lg">${this.typeIcon(s.source_type)}</div>
                        <div class="flex-1 min-w-0">
                            <div class="text-sm font-bold truncate">${s.name}</div>
                            <div class="text-xs text-gray-400">${s.source_type}</div>
                        </div>
                        <span class="px-2 py-0.5 text-[10px] font-semibold rounded border ${this.statusColor(s.status)}">${s.status}</span>
                    </div>
                    <div class="flex items-center gap-3 text-[11px] text-gray-400">
                        <span>${s.tenant_id}</span>
                        <span>·</span>
                        <span>${new Date(s.created_at).toLocaleDateString()}</span>
                        ${s.connection_config?.description ? html`
                        <span>·</span>
                        <span class="truncate">${String(s.connection_config.description).slice(0, 40)}</span>
                        ` : ''}
                    </div>
                </div>`)}
            </div>
            ${this.sources.length === 0 ? html`<div class="text-center text-gray-400 py-16">No sources configured. Click "+ New Source" to add one.</div>` : ''}
            `}

            <!-- Detail Panel -->
            <voyant-detail-panel
                .open=${this.detailOpen}
                .title=${this.selectedSource?.name || ''}
                .subtitle=${this.selectedSource?.source_type || ''}
                .width=${500}
                @close=${() => { this.detailOpen = false; this.editing = false; }}
            >
                ${this.selectedSource ? html`
                <div>
                    <!-- Status badge -->
                    <div class="flex items-center gap-3 mb-5">
                        <span class="px-3 py-1 text-xs font-semibold rounded-full border ${this.statusColor(this.selectedSource.status)}">${this.selectedSource.status}</span>
                        <span class="text-xs text-gray-400">${this.selectedSource.tenant_id}</span>
                        <span class="text-xs text-gray-400">Created ${new Date(this.selectedSource.created_at).toLocaleString()}</span>
                    </div>

                    ${this.editing ? html`
                    <!-- Edit mode -->
                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Name</h4>
                    <input class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm mb-4" .value=${this.editName} @input=${(e: Event) => { this.editName = (e.target as HTMLInputElement).value; }}>

                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Connection Config (JSON)</h4>
                    <textarea class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono mb-4" rows="10" .value=${this.editConfig} @input=${(e: Event) => { this.editConfig = (e.target as HTMLTextAreaElement).value; }}></textarea>

                    <div class="flex gap-2">
                        <button class="flex-1 px-4 py-2 text-sm font-bold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.editSaving ? 'opacity-50' : ''}"
                            ?disabled=${this.editSaving} @click=${() => this.saveEdit()}>
                            ${this.editSaving ? 'Saving...' : '💾 Save'}
                        </button>
                        <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50" @click=${() => { this.editing = false; }}>Cancel</button>
                    </div>
                    ` : html`
                    <!-- View mode -->
                    <div class="flex gap-2 mb-5">
                        <button class="px-4 py-2 text-sm font-semibold border border-gray-200 rounded-lg hover:border-brand hover:text-brand transition-colors"
                            @click=${() => { this.editing = true; this.editName = this.selectedSource!.name; this.editConfig = JSON.stringify(this.selectedSource!.connection_config || {}, null, 2); }}>✏️ Edit</button>
                        <button class="px-4 py-2 text-sm font-semibold border border-red-200 text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                            @click=${() => this.deleteSource(this.selectedSource!.source_id, this.selectedSource!.name)}>🗑️ Delete</button>
                    </div>

                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Connection Config</h4>
                    <div class="bg-gray-50 rounded-lg p-3 mb-5 max-h-48 overflow-auto">
                        <pre class="text-xs font-mono text-gray-700 whitespace-pre-wrap">${JSON.stringify(this.selectedSource.connection_config || {}, null, 2)}</pre>
                    </div>

                    ${this.selectedSource.datahub_urn ? html`
                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">DataHub URN</h4>
                    <div class="px-3 py-2 rounded-lg bg-gray-50 font-mono text-xs mb-5">${this.selectedSource.datahub_urn}</div>
                    ` : ''}
                    `}
                </div>
                ` : ''}
            </voyant-detail-panel>
        </main>`;
    }
}
