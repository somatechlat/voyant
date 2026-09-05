import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, type SourceListItem } from '../lib/api';
import '../components/saas-sidebar';

@customElement('view-sources')
export class ViewSources extends LitElement {
    @state() sources: SourceListItem[] = [];
    @state() loading = true;

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

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.load();
    }

    async load() {
        this.loading = true;
        try { this.sources = await api.get<SourceListItem[]>('/admin/sources'); }
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
            const credentials: Record<string, string> = {};
            if (this.createUser) credentials.user = this.createUser;
            if (this.createPassword) credentials.password = this.createPassword;

            await api.post('/v1/sources', {
                name: this.createName,
                source_type: this.createType,
                connection_config,
                credentials: Object.keys(credentials).length > 0 ? credentials : undefined,
            });
            this.createResult = 'Source created successfully';
            this.showCreate = false;
            this.createName = '';
            this.createHost = '';
            this.createDatabase = '';
            this.createUser = '';
            this.createPassword = '';
            await this.load();
        } catch (e: unknown) {
            this.createResult = `Error: ${e instanceof Error ? e.message : 'Failed'}`;
        } finally { this.creating = false; }
    }

    async deleteSource(id: string, name: string) {
        if (!confirm(`Delete source "${name}"? This cannot be undone.`)) return;
        try {
            await api.del(`/admin/sources/${id}`);
            await this.load();
        } catch (e: unknown) {
            alert(`Delete failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
        }
    }

    private statusColor(s: string) {
        if (s === 'connected') return 'bg-green-50 text-green-700 border-green-200';
        if (s === 'error') return 'bg-red-50 text-red-700 border-red-200';
        return 'bg-amber-50 text-amber-700 border-amber-200';
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

            <!-- Sources Table -->
            ${this.loading ? html`<div class="text-center text-gray-400 py-16">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <table class="w-full text-sm">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-400 uppercase tracking-wider">
                        <th class="px-5 py-3">Name</th>
                        <th class="px-5 py-3">Type</th>
                        <th class="px-5 py-3">Tenant</th>
                        <th class="px-5 py-3">Status</th>
                        <th class="px-5 py-3">Created</th>
                        <th class="px-5 py-3">Actions</th>
                    </tr></thead>
                    <tbody>
                    ${this.sources.map(s => html`
                        <tr class="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                            <td class="px-5 py-3 font-semibold">${s.name}</td>
                            <td class="px-5 py-3"><span class="px-2 py-0.5 text-xs bg-gray-100 rounded font-mono">${s.source_type}</span></td>
                            <td class="px-5 py-3 text-gray-500">${s.tenant_id}</td>
                            <td class="px-5 py-3"><span class="px-2 py-0.5 text-xs rounded border ${this.statusColor(s.status)}">${s.status}</span></td>
                            <td class="px-5 py-3 text-gray-400 text-xs">${new Date(s.created_at).toLocaleDateString()}</td>
                            <td class="px-5 py-3">
                                <button class="text-xs text-red-500 hover:underline" @click=${() => this.deleteSource(s.source_id, s.name)}>Delete</button>
                            </td>
                        </tr>`)}
                    </tbody>
                </table>
                ${this.sources.length === 0 ? html`<div class="text-center text-gray-400 py-12">No sources configured</div>` : ''}
            </div>`}
        </main>`;
    }
}
