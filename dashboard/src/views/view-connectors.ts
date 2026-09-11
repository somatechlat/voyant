import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface Connection {
    id: string;
    name: string;
    source_type: string;
    status: string;
    last_sync: string | null;
    datasets_count: number;
    config: Record<string, unknown>;
}

interface DatasetSchema {
    name: string;
    namespace: string;
    description: string;
    row_count: number | null;
}

interface ConnectionTestResult {
    healthy: boolean;
    message: string;
    latency_ms: number;
    details: Record<string, unknown>;
}

interface ConnectorType {
    id: string;
    label: string;
    icon: string;
    fields: Array<{ key: string; label: string; type: string; placeholder: string; required: boolean }>;
}

/* ── Connector type definitions ────────────────────────────────────────────── */

const CONNECTOR_TYPES: ConnectorType[] = [
    {
        id: 'postgresql', label: 'PostgreSQL', icon: 'database',
        fields: [
            { key: 'host', label: 'Host', type: 'text', placeholder: 'localhost', required: true },
            { key: 'port', label: 'Port', type: 'number', placeholder: '5432', required: true },
            { key: 'database', label: 'Database', type: 'text', placeholder: 'mydb', required: true },
            { key: 'user', label: 'User', type: 'text', placeholder: 'postgres', required: true },
            { key: 'password', label: 'Password', type: 'password', placeholder: '••••••••', required: true },
            { key: 'schema', label: 'Schema', type: 'text', placeholder: 'public', required: false },
        ],
    },
    {
        id: 'mysql', label: 'MySQL', icon: 'database',
        fields: [
            { key: 'host', label: 'Host', type: 'text', placeholder: 'localhost', required: true },
            { key: 'port', label: 'Port', type: 'number', placeholder: '3306', required: true },
            { key: 'database', label: 'Database', type: 'text', placeholder: 'mydb', required: true },
            { key: 'user', label: 'User', type: 'text', placeholder: 'root', required: true },
            { key: 'password', label: 'Password', type: 'password', placeholder: '••••••••', required: true },
        ],
    },
    {
        id: 's3', label: 'Amazon S3', icon: 'cloud',
        fields: [
            { key: 'bucket', label: 'Bucket', type: 'text', placeholder: 'my-data-bucket', required: true },
            { key: 'prefix', label: 'Prefix', type: 'text', placeholder: 'data/', required: false },
            { key: 'region', label: 'Region', type: 'text', placeholder: 'us-east-1', required: true },
            { key: 'access_key', label: 'Access Key', type: 'text', placeholder: 'AKIA...', required: true },
            { key: 'secret_key', label: 'Secret Key', type: 'password', placeholder: '••••••••', required: true },
            { key: 'endpoint_url', label: 'Endpoint URL (optional)', type: 'text', placeholder: 'https://minio.local', required: false },
        ],
    },
    {
        id: 'rest_api', label: 'REST API', icon: 'globe',
        fields: [
            { key: 'base_url', label: 'Base URL', type: 'text', placeholder: 'https://api.example.com', required: true },
            { key: 'auth_type', label: 'Auth Type', type: 'text', placeholder: 'bearer / api_key / none', required: false },
            { key: 'auth_token', label: 'Auth Token / Key', type: 'password', placeholder: '••••••••', required: false },
        ],
    },
];

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-connectors')
export class ViewConnectors extends LitElement {
    @state() connections: Connection[] = [];
    @state() loading = true;
    @state() error: string | null = null;

    // Detail panel
    @state() selectedConnection: Connection | null = null;
    @state() detailDatasets: DatasetSchema[] = [];
    @state() detailLoading = false;

    // Add connection wizard
    @state() wizardStep = 0; // 0=select type, 1=config, 2=test, 3=datasets
    @state() wizardType: ConnectorType | null = null;
    @state() wizardConfig: Record<string, string> = {};
    @state() wizardTestResult: ConnectionTestResult | null = null;
    @state() wizardTesting = false;
    @state() wizardName = '';
    @state() wizardSaving = false;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadConnections();
    }

    /* ── Data Loading ─────────────────────────────────────────────────────── */

    async loadConnections() {
        this.loading = true;
        this.error = null;
        try {
            // Use the ingestion connect API and source listing
            this.connections = await api.get<Connection[]>('/ingestion/connections');
        } catch (e) {
            // Graceful fallback — the endpoint may not exist yet
            this.error = e instanceof Error ? e.message : 'Failed to load connections';
            this.connections = [];
        } finally {
            this.loading = false;
        }
    }

    async testConnection() {
        if (!this.wizardType) return;
        this.wizardTesting = true;
        this.wizardTestResult = null;
        try {
            this.wizardTestResult = await api.post<ConnectionTestResult>('/ingestion/connections/test', {
                source_type: this.wizardType.id,
                config: this.wizardConfig,
            });
        } catch (e) {
            this.wizardTestResult = {
                healthy: false,
                message: e instanceof Error ? e.message : 'Connection test failed',
                latency_ms: 0,
                details: {},
            };
        } finally {
            this.wizardTesting = false;
        }
    }

    async loadConnectionDetail(connId: string) {
        this.detailLoading = true;
        this.selectedConnection = this.connections.find(c => c.id === connId) || null;
        try {
            this.detailDatasets = await api.get<DatasetSchema[]>(`/ingestion/connections/${connId}/datasets`);
        } catch {
            this.detailDatasets = [];
        } finally {
            this.detailLoading = false;
        }
    }

    async saveConnection() {
        if (!this.wizardType || !this.wizardName.trim()) return;
        this.wizardSaving = true;
        try {
            await api.post('/ingestion/connections', {
                name: this.wizardName,
                source_type: this.wizardType.id,
                config: this.wizardConfig,
            });
            this.resetWizard();
            await this.loadConnections();
        } catch { /* empty */ } finally {
            this.wizardSaving = false;
        }
    }

    private resetWizard() {
        this.wizardStep = 0;
        this.wizardType = null;
        this.wizardConfig = {};
        this.wizardTestResult = null;
        this.wizardName = '';
    }

    /* ── Helpers ──────────────────────────────────────────────────────────── */

    private sourceTypeBadge(t: string) {
        const colors: Record<string, string> = {
            postgresql: 'bg-blue-50 text-blue-700 border-blue-200',
            postgres: 'bg-blue-50 text-blue-700 border-blue-200',
            mysql: 'bg-orange-50 text-orange-700 border-orange-200',
            s3: 'bg-yellow-50 text-yellow-700 border-yellow-200',
            rest_api: 'bg-purple-50 text-purple-700 border-purple-200',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[t] || 'bg-gray-50 text-gray-700 border-gray-200'}">${t}</span>`;
    }

    private statusDot(s: string) {
        const colors: Record<string, string> = {
            connected: 'bg-green-500', active: 'bg-green-500', running: 'bg-green-500',
            connecting: 'bg-amber-500', starting: 'bg-amber-500',
            error: 'bg-red-500', failed: 'bg-red-500',
            disconnected: 'bg-gray-400', inactive: 'bg-gray-400', stopped: 'bg-gray-400',
        };
        return html`<span class="inline-block w-2 h-2 rounded-full ${colors[s] || 'bg-gray-400'}"></span>`;
    }

    /* ── Render ───────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/connectors"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Data Connectors">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Data Connectors</h1>
                    <p class="text-sm text-gray-400 mt-1">Manage data source connections, test connectivity, and discover datasets</p>
                </div>
                <div class="flex gap-2">
                    <button class="px-4 py-1.5 text-sm font-semibold border border-gray-200 rounded-lg bg-white hover:bg-gray-50 transition-colors flex items-center gap-2"
                        @click=${() => this.loadConnections()}>
                        <svg class="w-4 h-4 ${this.loading ? 'animate-spin' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                        Refresh
                    </button>
                    <button class="px-4 py-1.5 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
                        @click=${() => { this.resetWizard(); }}>
                        + Add Connection
                    </button>
                </div>
            </div>

            ${this.error ? html`
            <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <svg class="w-5 h-5 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                    <span class="text-sm text-red-700">${this.error}</span>
                </div>
                <button class="text-sm text-red-600 hover:underline" @click=${() => this.loadConnections()}>Retry</button>
            </div>` : ''}

            ${this.loading ? html`
            <div class="text-center py-16" role="status" aria-live="polite">
                <div class="inline-block w-8 h-8 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin mb-3"></div>
                <div class="text-sm text-gray-400">Loading connections...</div>
            </div>` : html`
            <!-- Connections Table -->
            ${this.renderConnectionsTable()}
            `}

            <!-- Detail Panel -->
            ${this.selectedConnection ? this.renderDetailPanel() : ''}

            <!-- Wizard -->
            ${this.wizardStep > 0 || this.wizardType ? this.renderWizard() : ''}
        </main>`;
    }

    /* ── Connections Table ────────────────────────────────────────────────── */

    private renderConnectionsTable() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
            <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700">Connections</h2>
                <span class="text-xs text-gray-400">${this.connections.length} connections</span>
            </div>
            <table class="w-full text-sm" role="table" aria-label="Data connections">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">Name</th>
                    <th class="px-5 py-3">Type</th>
                    <th class="px-5 py-3">Status</th>
                    <th class="px-5 py-3">Last Sync</th>
                    <th class="px-5 py-3">Datasets</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.connections.length === 0 ? html`
                <tr><td colspan="6" class="px-5 py-16 text-center text-gray-400">
                    <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
                        <svg class="w-7 h-7 text-gray-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                    </div>
                    <div class="text-sm font-semibold text-gray-600">No connections configured</div>
                    <div class="text-xs mt-2 text-gray-400">Add a data connector to start ingesting data from external sources.</div>
                </td></tr>` : ''}
                ${this.connections.map(c => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                    role="button" tabindex="0"
                    @click=${() => this.loadConnectionDetail(c.id)}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.loadConnectionDetail(c.id); } }}>
                    <td class="px-5 py-3 font-semibold">${c.name}</td>
                    <td class="px-5 py-3">${this.sourceTypeBadge(c.source_type)}</td>
                    <td class="px-5 py-3">
                        <span class="inline-flex items-center gap-1.5 text-xs">${this.statusDot(c.status)} ${c.status}</span>
                    </td>
                    <td class="px-5 py-3 text-xs text-gray-500">${c.last_sync ? new Date(c.last_sync).toLocaleString() : '—'}</td>
                    <td class="px-5 py-3 text-sm font-semibold">${c.datasets_count}</td>
                    <td class="px-5 py-3" @click=${(e: Event) => e.stopPropagation()}>
                        <div class="flex gap-2">
                            <button class="text-xs text-blue-600 hover:underline" @click=${() => this.loadConnectionDetail(c.id)}>Details</button>
                        </div>
                    </td>
                </tr>`)}
                </tbody>
            </table>
        </div>`;
    }

    /* ── Detail Panel ─────────────────────────────────────────────────────── */

    private renderDetailPanel() {
        const conn = this.selectedConnection!;

        return html`
        <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Connection: ${conn.name}"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this.selectedConnection = null; }}>
            <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedConnection = null; }}></div>
            <div class="relative w-[640px] bg-white h-full overflow-y-auto shadow-2xl border-l border-gray-200" tabindex="-1">
                <div class="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between z-10">
                    <div>
                        <h2 class="font-bold text-lg">${conn.name}</h2>
                        <div class="flex items-center gap-2 mt-1">
                            ${this.sourceTypeBadge(conn.source_type)}
                            <span class="inline-flex items-center gap-1.5 text-xs">${this.statusDot(conn.status)} ${conn.status}</span>
                        </div>
                    </div>
                    <button class="text-gray-400 hover:text-ink" @click=${() => { this.selectedConnection = null; }}>✕</button>
                </div>

                <div class="p-6 space-y-6">
                    <!-- Config -->
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Configuration</h3>
                        <div class="grid grid-cols-2 gap-3">
                            ${Object.entries(conn.config || {}).filter(([k]) => k !== 'password' && k !== 'secret_key').map(([k, v]) => html`
                            <div class="p-3 bg-gray-50 rounded-lg">
                                <div class="text-xs text-gray-400">${k}</div>
                                <div class="text-sm font-mono mt-1 truncate">${String(v)}</div>
                            </div>`)}
                        </div>
                    </div>

                    <!-- Datasets -->
                    <div>
                        <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3">Discovered Datasets</h3>
                        ${this.detailLoading ? html`<div class="text-sm text-gray-400 py-4 text-center">Loading datasets...</div>` : html`
                        ${this.detailDatasets.length === 0 ? html`
                        <div class="text-sm text-gray-400 py-8 text-center">No datasets discovered. Test the connection to discover available datasets.</div>` : html`
                        <div class="bg-white rounded-lg border border-gray-100 overflow-hidden">
                            <table class="w-full text-sm">
                                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                                    <th class="px-4 py-2.5">Name</th>
                                    <th class="px-4 py-2.5">Namespace</th>
                                    <th class="px-4 py-2.5">Description</th>
                                    <th class="px-4 py-2.5">Rows</th>
                                </tr></thead>
                                <tbody>
                                ${this.detailDatasets.map(ds => html`
                                <tr class="border-b border-gray-50">
                                    <td class="px-4 py-2.5 font-medium">${ds.name}</td>
                                    <td class="px-4 py-2.5 text-xs font-mono text-gray-500">${ds.namespace}</td>
                                    <td class="px-4 py-2.5 text-xs text-gray-500 truncate max-w-[200px]">${ds.description || '—'}</td>
                                    <td class="px-4 py-2.5 text-xs">${ds.row_count != null ? ds.row_count.toLocaleString() : '—'}</td>
                                </tr>`)}
                                </tbody>
                            </table>
                        </div>`}`}
                    </div>

                    <div class="flex gap-2 pt-4 border-t border-gray-100">
                        <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                            @click=${() => { this.selectedConnection = null; }}>Close</button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    /* ── Add Connection Wizard ────────────────────────────────────────────── */

    private renderWizard() {
        return html`
        <div class="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Add connection"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this.resetWizard(); }}>
            <div class="absolute inset-0 bg-black/30" @click=${() => this.resetWizard()}></div>
            <div class="relative bg-white rounded-2xl shadow-2xl w-[580px] max-h-[85vh] overflow-y-auto" tabindex="-1">
                <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                    <h2 class="font-bold text-lg">Add Connection — Step ${this.wizardStep + 1} of 4</h2>
                    <button class="text-gray-400 hover:text-ink" @click=${() => this.resetWizard()}>✕</button>
                </div>

                <div class="p-6">
                    ${this.wizardStep === 0 ? this.renderWizardStep1() : ''}
                    ${this.wizardStep === 1 ? this.renderWizardStep2() : ''}
                    ${this.wizardStep === 2 ? this.renderWizardStep3() : ''}
                    ${this.wizardStep === 3 ? this.renderWizardStep4() : ''}
                </div>
            </div>
        </div>`;
    }

    private renderWizardStep1() {
        return html`
        <div>
            <h3 class="text-sm font-semibold text-gray-700 mb-4">Select Connector Type</h3>
            <div class="grid grid-cols-2 gap-3">
                ${CONNECTOR_TYPES.map(ct => html`
                <button class="p-4 border-2 rounded-xl text-left transition-colors ${this.wizardType?.id === ct.id ? 'border-gray-900 bg-gray-50' : 'border-gray-200 hover:border-gray-300'}"
                    @click=${() => { this.wizardType = ct; this.wizardConfig = {}; }}>
                    <div class="font-semibold text-sm">${ct.label}</div>
                    <div class="text-xs text-gray-400 mt-1">${ct.fields.length} fields</div>
                </button>`)}
            </div>
            <div class="flex justify-end mt-6">
                <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors ${!this.wizardType ? 'opacity-50' : ''}"
                    ?disabled=${!this.wizardType}
                    @click=${() => { this.wizardStep = 1; }}>Next</button>
            </div>
        </div>`;
    }

    private renderWizardStep2() {
        const ct = this.wizardType!;
        return html`
        <div>
            <h3 class="text-sm font-semibold text-gray-700 mb-1">${ct.label} Configuration</h3>
            <div class="space-y-3 mt-4">
                <div>
                    <label class="block text-xs font-semibold text-gray-600 mb-1">Connection Name *</label>
                    <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                        placeholder="e.g. Production DB"
                        .value=${this.wizardName}
                        @input=${(e: Event) => { this.wizardName = (e.target as HTMLInputElement).value; }}>
                </div>
                ${ct.fields.map(f => html`
                <div>
                    <label class="block text-xs font-semibold text-gray-600 mb-1">${f.label} ${f.required ? '*' : ''}</label>
                    <input type="${f.type}" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900/10"
                        placeholder="${f.placeholder}"
                        .value=${this.wizardConfig[f.key] || ''}
                        @input=${(e: Event) => { this.wizardConfig = { ...this.wizardConfig, [f.key]: (e.target as HTMLInputElement).value }; }}>
                </div>`)}
            </div>
            <div class="flex justify-between mt-6">
                <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                    @click=${() => { this.wizardStep = 0; }}>Back</button>
                <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
                    @click=${() => { this.wizardStep = 2; }}>Next</button>
            </div>
        </div>`;
    }

    private renderWizardStep3() {
        return html`
        <div>
            <h3 class="text-sm font-semibold text-gray-700 mb-4">Test Connection</h3>
            <div class="text-center py-6">
                ${this.wizardTesting ? html`
                <div class="inline-block w-8 h-8 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin mb-3"></div>
                <div class="text-sm text-gray-400">Testing connection...</div>` : html`
                ${this.wizardTestResult ? html`
                <div class="p-4 rounded-lg ${this.wizardTestResult.healthy ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}">
                    <div class="font-semibold text-sm ${this.wizardTestResult.healthy ? 'text-green-700' : 'text-red-700'}">
                        ${this.wizardTestResult.healthy ? 'Connection Successful' : 'Connection Failed'}
                    </div>
                    <div class="text-xs mt-1 ${this.wizardTestResult.healthy ? 'text-green-600' : 'text-red-600'}">
                        ${this.wizardTestResult.message}
                    </div>
                    ${this.wizardTestResult.latency_ms > 0 ? html`
                    <div class="text-xs text-gray-500 mt-1">Latency: ${this.wizardTestResult.latency_ms.toFixed(1)}ms</div>` : ''}
                </div>` : html`
                <button class="px-6 py-3 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
                    @click=${() => this.testConnection()}>Test Connection</button>`}`}
            </div>
            <div class="flex justify-between mt-6">
                <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                    @click=${() => { this.wizardStep = 1; this.wizardTestResult = null; }}>Back</button>
                <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors ${!this.wizardTestResult?.healthy ? 'opacity-50' : ''}"
                    ?disabled=${!this.wizardTestResult?.healthy}
                    @click=${() => { this.wizardStep = 3; }}>Next</button>
            </div>
        </div>`;
    }

    private renderWizardStep4() {
        return html`
        <div>
            <h3 class="text-sm font-semibold text-gray-700 mb-4">Save Connection</h3>
            <div class="bg-gray-50 rounded-lg p-4 mb-4">
                <div class="text-xs text-gray-500">Name</div>
                <div class="text-sm font-semibold">${this.wizardName}</div>
                <div class="text-xs text-gray-500 mt-2">Type</div>
                <div class="text-sm">${this.wizardType?.label}</div>
            </div>
            <p class="text-sm text-gray-500">The connection will be saved and datasets will be discovered automatically.</p>
            <div class="flex justify-between mt-6">
                <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                    @click=${() => { this.wizardStep = 2; }}>Back</button>
                <button class="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-black transition-colors ${this.wizardSaving ? 'opacity-50' : ''}"
                    ?disabled=${this.wizardSaving}
                    @click=${() => this.saveConnection()}>
                    ${this.wizardSaving ? 'Saving...' : 'Save Connection'}
                </button>
            </div>
        </div>`;
    }
}
