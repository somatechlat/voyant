import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface McpTool {
    name: string;
    category: string;
    description: string;
    params: Record<string, unknown>;
}

interface ToolResult {
    success: boolean;
    data: unknown;
    duration_ms: number;
    timestamp: string;
}

/* ── MCP Tool Catalog (extracted from tools_*.py) ──────────────────────────── */

const MCP_TOOLS: McpTool[] = [
    // ── Data Ops ──
    { name: 'voyant.sql', category: 'Data Ops', description: 'Execute read-only SQL via Trino', params: { type: 'object', properties: { sql: { type: 'string', description: 'SQL query to execute' }, limit: { type: 'integer', default: 1000, description: 'Max rows to return' } }, required: ['sql'] } },
    { name: 'voyant.search', category: 'Data Ops', description: 'Semantic vector search across indexed data', params: { type: 'object', properties: { query: { type: 'string', description: 'Search query' }, limit: { type: 'integer', default: 5 } }, required: ['query'] } },
    { name: 'voyant.kpi', category: 'Data Ops', description: 'Run KPI queries and return aggregated results', params: { type: 'object', properties: { kpis: { type: 'array', items: { type: 'object' }, description: 'List of KPI definitions with SQL' }, limit: { type: 'integer', default: 1000 } }, required: ['kpis'] } },
    { name: 'voyant.tables.list', category: 'Data Ops', description: 'List available tables in the data warehouse', params: { type: 'object', properties: { schema: { type: 'string', description: 'Schema name (optional)' } } } },
    { name: 'voyant.tables.columns', category: 'Data Ops', description: 'List columns for a given table', params: { type: 'object', properties: { table: { type: 'string', description: 'Table name' }, schema: { type: 'string' } }, required: ['table'] } },
    // ── Catalog ──
    { name: 'voyant.sources.list', category: 'Catalog', description: 'List all data sources for a tenant', params: { type: 'object', properties: {} } },
    { name: 'voyant.sources.get', category: 'Catalog', description: 'Get a data source with connection config', params: { type: 'object', properties: { source_id: { type: 'string' } }, required: ['source_id'] } },
    { name: 'voyant.sources.delete', category: 'Catalog', description: 'Delete a data source', params: { type: 'object', properties: { source_id: { type: 'string' } }, required: ['source_id'] } },
    { name: 'voyant.discover', category: 'Catalog', description: 'Auto-detect source type from a URL or DSN hint', params: { type: 'object', properties: { hint: { type: 'string' } }, required: ['hint'] } },
    { name: 'voyant.connect', category: 'Catalog', description: 'Register a new data source', params: { type: 'object', properties: { name: { type: 'string' }, source_type: { type: 'string' }, connection_config: { type: 'object' } }, required: ['name', 'source_type', 'connection_config'] } },
    { name: 'voyant.discovery.services.list', category: 'Catalog', description: 'List registered microservice definitions', params: { type: 'object', properties: { tag: { type: 'string' } } } },
    { name: 'voyant.discovery.services.get', category: 'Catalog', description: 'Get a microservice definition by name', params: { type: 'object', properties: { name: { type: 'string' } }, required: ['name'] } },
    { name: 'voyant.discovery.services.register', category: 'Catalog', description: 'Register a new microservice', params: { type: 'object', properties: { name: { type: 'string' }, base_url: { type: 'string' }, spec_url: { type: 'string' }, version: { type: 'string' }, owner: { type: 'string' }, tags: { type: 'array' } }, required: ['name', 'base_url'] } },
    { name: 'voyant.discovery.scan', category: 'Catalog', description: 'Scan an OpenAPI spec URL for endpoints', params: { type: 'object', properties: { url: { type: 'string' } }, required: ['url'] } },
    { name: 'voyant.lineage', category: 'Catalog', description: 'Fetch upstream/downstream data lineage from DataHub', params: { type: 'object', properties: { urn: { type: 'string' }, direction: { type: 'string', enum: ['both', 'UPSTREAM', 'DOWNSTREAM'], default: 'both' }, depth: { type: 'integer', default: 3, maximum: 10 } }, required: ['urn'] } },
    // ── Scraper ──
    { name: 'scrape.fetch', category: 'Scraper', description: 'Fetch a web page with JS rendering support (Playwright/httpx/Scrapy)', params: { type: 'object', properties: { url: { type: 'string' }, engine: { type: 'string', enum: ['playwright', 'httpx', 'scrapy'], default: 'playwright' }, wait_for: { type: 'string' }, scroll: { type: 'boolean', default: false }, timeout: { type: 'integer', default: 30 } }, required: ['url'] } },
    { name: 'scrape.deep_archive', category: 'Scraper', description: 'Deep archival scrape for SPAs with tab navigation', params: { type: 'object', properties: { url: { type: 'string' }, interaction_selectors: { type: 'array', items: { type: 'string' } }, download_patterns: { type: 'array', items: { type: 'string' } }, target_dir: { type: 'string', default: 'scrapes/unknown' } }, required: ['url'] } },
    { name: 'scrape.extract', category: 'Scraper', description: 'Extract structured data from HTML using CSS/XPath selectors', params: { type: 'object', properties: { html: { type: 'string' }, selectors: { type: 'object' }, url: { type: 'string' } }, required: ['html', 'selectors'] } },
    { name: 'scrape.ocr', category: 'Scraper', description: 'Run Tesseract OCR on image URLs or file paths', params: { type: 'object', properties: { images: { type: 'array', items: { type: 'string' } }, language: { type: 'string', default: 'spa+eng' } }, required: ['images'] } },
    { name: 'scrape.parse_pdf', category: 'Scraper', description: 'Parse PDF for text, metadata, and tables', params: { type: 'object', properties: { pdf_url: { type: 'string' }, extract_tables: { type: 'boolean', default: false } }, required: ['pdf_url'] } },
    { name: 'scrape.transcribe', category: 'Scraper', description: 'Transcribe audio/video to text via Whisper', params: { type: 'object', properties: { media_urls: { type: 'array', items: { type: 'string' } }, language: { type: 'string', default: 'es' } }, required: ['media_urls'] } },
    { name: 'voyant.scraper.templates.list', category: 'Scraper', description: 'List all scraper templates', params: { type: 'object', properties: { category: { type: 'string' } } } },
    { name: 'voyant.scraper.templates.get', category: 'Scraper', description: 'Get full template details including selectors and workflow', params: { type: 'object', properties: { template_id: { type: 'string' } }, required: ['template_id'] } },
    { name: 'voyant.scraper.templates.search', category: 'Scraper', description: 'Search templates by name, description, or site pattern', params: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] } },
    { name: 'voyant.scraper.templates.create', category: 'Scraper', description: 'Create a new scraper template', params: { type: 'object', properties: { name: { type: 'string' }, category: { type: 'string' }, site_pattern: { type: 'string' }, workflow: { type: 'array' }, selectors: { type: 'object' }, description: { type: 'string' } }, required: ['name', 'category', 'site_pattern', 'workflow'] } },
    { name: 'voyant.scraper.templates.validate', category: 'Scraper', description: 'Validate a template definition against schema', params: { type: 'object', properties: { template: { type: 'object' } }, required: ['template'] } },
    { name: 'voyant.scraper.templates.run', category: 'Scraper', description: 'Run a scraper template with parameters', params: { type: 'object', properties: { template_id: { type: 'string' }, parameters: { type: 'object' } }, required: ['template_id'] } },
    { name: 'voyant.scraper.templates.generate', category: 'Scraper', description: 'Auto-generate template from a URL', params: { type: 'object', properties: { url: { type: 'string' }, name: { type: 'string' } }, required: ['url'] } },
    { name: 'voyant.scraper.templates.export', category: 'Scraper', description: 'Export template as JSON or Python code', params: { type: 'object', properties: { template_id: { type: 'string' }, format: { type: 'string', enum: ['json', 'python'], default: 'json' } }, required: ['template_id'] } },
    { name: 'voyant.templates.execute', category: 'Scraper', description: 'Execute a UPTP template via the execution engine', params: { type: 'object', properties: { template_id: { type: 'string' }, category: { type: 'string' }, tenant_id: { type: 'string' }, params: { type: 'object' } }, required: ['template_id', 'category', 'tenant_id', 'params'] } },
    // ── Ontology ──
    { name: 'voyant.ontology.types.list', category: 'Ontology', description: 'List all object types with property and instance counts', params: { type: 'object', properties: {} } },
    { name: 'voyant.ontology.types.get', category: 'Ontology', description: 'Get an object type with its full property definitions', params: { type: 'object', properties: { type_id: { type: 'string' } }, required: ['type_id'] } },
    { name: 'voyant.ontology.types.create', category: 'Ontology', description: 'Create a new object type with optional property definitions', params: { type: 'object', properties: { name: { type: 'string' }, description: { type: 'string' }, properties: { type: 'array' } }, required: ['name'] } },
    { name: 'voyant.ontology.objects.list', category: 'Ontology', description: 'List object instances, optionally filtered by type', params: { type: 'object', properties: { type_id: { type: 'string' }, limit: { type: 'integer', default: 100 } } } },
    { name: 'voyant.ontology.objects.create', category: 'Ontology', description: 'Create a new object instance with schema validation', params: { type: 'object', properties: { type_id: { type: 'string' }, properties: { type: 'object' } }, required: ['type_id', 'properties'] } },
    { name: 'voyant.ontology.objects.get', category: 'Ontology', description: 'Get object instance with properties and links', params: { type: 'object', properties: { object_id: { type: 'string' } }, required: ['object_id'] } },
    { name: 'voyant.ontology.objects.update', category: 'Ontology', description: 'Update an object instance with optimistic concurrency', params: { type: 'object', properties: { object_id: { type: 'string' }, properties: { type: 'object' }, version: { type: 'integer' } }, required: ['object_id', 'properties'] } },
    { name: 'voyant.ontology.objects.batch_create', category: 'Ontology', description: 'Batch create 1000+ object instances', params: { type: 'object', properties: { type_id: { type: 'string' }, items: { type: 'array' } }, required: ['type_id', 'items'] } },
    { name: 'voyant.ontology.links.create', category: 'Ontology', description: 'Create a link between two objects', params: { type: 'object', properties: { link_type_id: { type: 'string' }, source_object_id: { type: 'string' }, target_object_id: { type: 'string' }, properties: { type: 'object' } }, required: ['link_type_id', 'source_object_id', 'target_object_id'] } },
    { name: 'voyant.ontology.links.delete', category: 'Ontology', description: 'Delete a link between two objects', params: { type: 'object', properties: { link_id: { type: 'string' } }, required: ['link_id'] } },
    { name: 'voyant.ontology.traverse', category: 'Ontology', description: 'Traverse links from an object up to 10 hops', params: { type: 'object', properties: { object_id: { type: 'string' }, direction: { type: 'string', enum: ['outgoing', 'incoming', 'both'], default: 'outgoing' }, max_depth: { type: 'integer', default: 1, maximum: 10 }, link_type_name: { type: 'string' } }, required: ['object_id'] } },
    { name: 'voyant.ontology.interfaces.list', category: 'Ontology', description: 'List all interfaces (polymorphic type abstractions)', params: { type: 'object', properties: {} } },
    { name: 'voyant.ontology.actions.execute', category: 'Ontology', description: 'Execute an action type on an object instance', params: { type: 'object', properties: { action_type_id: { type: 'string' }, object_id: { type: 'string' }, params: { type: 'object' } }, required: ['action_type_id', 'object_id'] } },
    { name: 'voyant.ontology.functions.run', category: 'Ontology', description: 'Run an ontology function in a sandboxed environment', params: { type: 'object', properties: { function_id: { type: 'string' }, input_data: { type: 'object' } }, required: ['function_id'] } },
    // ── Governance ──
    { name: 'voyant.governance.schema', category: 'Governance', description: 'Fetch governance schema metadata from DataHub', params: { type: 'object', properties: { urn: { type: 'string' } }, required: ['urn'] } },
    { name: 'voyant.quotas.tiers', category: 'Governance', description: 'List all quota tiers with descriptions', params: { type: 'object', properties: {} } },
    { name: 'voyant.quotas.usage', category: 'Governance', description: 'Get current quota usage for a tenant', params: { type: 'object', properties: {} } },
    { name: 'voyant.quotas.limits', category: 'Governance', description: 'Get quota limits for the current tenant', params: { type: 'object', properties: {} } },
    { name: 'voyant.quotas.set_tier', category: 'Governance', description: 'Set the quota tier for a tenant', params: { type: 'object', properties: { tier: { type: 'string', enum: ['free', 'pro', 'enterprise'] } }, required: ['tier'] } },
    { name: 'voyant.presets.list', category: 'Governance', description: 'List preset jobs', params: { type: 'object', properties: {} } },
    { name: 'voyant.presets.get', category: 'Governance', description: 'Get a preset job by ID', params: { type: 'object', properties: { job_id: { type: 'string' } }, required: ['job_id'] } },
    { name: 'voyant.preset', category: 'Governance', description: 'Create and queue a preset job', params: { type: 'object', properties: { preset_name: { type: 'string' }, payload: { type: 'object' } }, required: ['preset_name', 'payload'] } },
    // ── ML ──
    { name: 'voyant.ingest', category: 'ML', description: 'Start data ingestion workflow for a source', params: { type: 'object', properties: { source_id: { type: 'string' }, mode: { type: 'string', enum: ['full', 'incremental'], default: 'full' }, tables: { type: 'array', items: { type: 'string' } } }, required: ['source_id'] } },
    { name: 'voyant.profile', category: 'ML', description: 'Run data profiling on a source or table', params: { type: 'object', properties: { source_id: { type: 'string' }, table: { type: 'string' }, sample_size: { type: 'integer', default: 10000 } }, required: ['source_id'] } },
    { name: 'voyant.quality', category: 'ML', description: 'Run quality checks on data', params: { type: 'object', properties: { source_id: { type: 'string' }, table: { type: 'string' }, checks: { type: 'array' } }, required: ['source_id'] } },
    { name: 'voyant.analyze', category: 'ML', description: 'Run full analysis pipeline (profile + quality + anomalies)', params: { type: 'object', properties: { source_id: { type: 'string' }, table: { type: 'string' }, analyzers: { type: 'array' }, sample_size: { type: 'integer', default: 10000 } }, required: ['source_id'] } },
    { name: 'voyant.status', category: 'ML', description: 'Check status and progress of a job', params: { type: 'object', properties: { job_id: { type: 'string' } }, required: ['job_id'] } },
    { name: 'voyant.artifact', category: 'ML', description: 'Get artifact metadata by ID', params: { type: 'object', properties: { artifact_id: { type: 'string' } }, required: ['artifact_id'] } },
    { name: 'voyant.artifacts.list', category: 'ML', description: 'List artifacts for a given job', params: { type: 'object', properties: { job_id: { type: 'string' } }, required: ['job_id'] } },
    { name: 'voyant.vector.search', category: 'ML', description: 'Hybrid dense + sparse vector search', params: { type: 'object', properties: { query: { type: 'string' }, limit: { type: 'integer', default: 5 } }, required: ['query'] } },
    { name: 'voyant.vector.index', category: 'ML', description: 'Index text into the vector store', params: { type: 'object', properties: { text: { type: 'string' }, metadata: { type: 'object' }, item_id: { type: 'string' } }, required: ['text'] } },
    // ── Streaming ──
    { name: 'voyant.jobs.list', category: 'Streaming', description: 'List jobs with optional status/type filters', params: { type: 'object', properties: { status: { type: 'string' }, job_type: { type: 'string' }, limit: { type: 'integer', default: 50 } } } },
    { name: 'voyant.jobs.cancel', category: 'Streaming', description: 'Cancel a running or queued job', params: { type: 'object', properties: { job_id: { type: 'string' } }, required: ['job_id'] } },
    { name: 'voyant.kpi_templates.list', category: 'Streaming', description: 'List KPI templates', params: { type: 'object', properties: { category: { type: 'string' } } } },
    { name: 'voyant.kpi_templates.categories', category: 'Streaming', description: 'List available KPI template categories', params: { type: 'object', properties: {} } },
    { name: 'voyant.kpi_templates.get', category: 'Streaming', description: 'Get a KPI template by name', params: { type: 'object', properties: { name: { type: 'string' } }, required: ['name'] } },
    { name: 'voyant.kpi_templates.render', category: 'Streaming', description: 'Render a KPI template to SQL with parameters', params: { type: 'object', properties: { name: { type: 'string' }, params: { type: 'object' } }, required: ['name', 'params'] } },
];

const TOOL_CATEGORIES = ['Data Ops', 'Catalog', 'Scraper', 'Ontology', 'Governance', 'ML', 'Streaming'];

const CATEGORY_ICONS: Record<string, string> = {
    'Data Ops': '⚡',
    'Catalog': '📚',
    'Scraper': '🕷️',
    'Ontology': '🧬',
    'Governance': '🛡️',
    'ML': '🤖',
    'Streaming': '📡',
};

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-mcp')
export class ViewMcp extends LitElement {
    @state() selectedCategory = '';
    @state() selectedTool: McpTool | null = null;
    @state() searchQuery = '';
    @state() tools: McpTool[] = MCP_TOOLS;

    // Test panel
    @state() paramValues: Record<string, unknown> = {};
    @state() paramJson = '';
    @state() running = false;
    @state() result: ToolResult | null = null;
    @state() resultHistory: ToolResult[] = [];

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this._loadTools();
    }

    private async _loadTools() {
        try {
            const data = await api.get<McpTool[]>('/admin/mcp/tools');
            if (Array.isArray(data) && data.length > 0) {
                this.tools = data;
            }
        } catch {
            // Keep the hardcoded MCP_TOOLS catalog as fallback
        }
    }

    private get categoryTree(): Record<string, McpTool[]> {
        const tree: Record<string, McpTool[]> = {};
        for (const cat of TOOL_CATEGORIES) {
            tree[cat] = this.tools.filter(t => t.category === cat);
        }
        return tree;
    }

    private get filteredTools(): McpTool[] {
        let tools = this.selectedCategory
            ? this.tools.filter(t => t.category === this.selectedCategory)
            : this.tools;
        if (this.searchQuery) {
            const q = this.searchQuery.toLowerCase();
            tools = tools.filter(t => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q));
        }
        return tools;
    }

    private selectTool(tool: McpTool) {
        this.selectedTool = tool;
        this.result = null;
        // Initialize param values from schema
        const props = (tool.params as Record<string, Record<string, unknown>>)?.properties || {};
        const defaults: Record<string, unknown> = {};
        for (const [key, schema] of Object.entries(props)) {
            if (schema.default !== undefined) defaults[key] = schema.default;
            else if (schema.type === 'boolean') defaults[key] = false;
            else if (schema.type === 'integer' || schema.type === 'number') defaults[key] = 0;
            else defaults[key] = '';
        }
        this.paramValues = defaults;
        this.paramJson = JSON.stringify(defaults, null, 2);
    }

    private async runTool() {
        if (!this.selectedTool) return;
        this.running = true;
        this.result = null;
        const start = performance.now();

        let params: Record<string, unknown>;
        try {
            params = JSON.parse(this.paramJson);
        } catch {
            params = this.paramValues;
        }

        try {
            // Try the planned MCP invoke endpoint first, fallback to direct API
            let data: unknown;
            try {
                data = await api.post(`/mcp/tools/${this.selectedTool.name}/invoke`, { params });
            } catch {
                // Fallback: use the tool-specific API endpoints
                data = await this.invokeViaRest(this.selectedTool.name, params);
            }
            const elapsed = Math.round(performance.now() - start);
            this.result = {
                success: true,
                data,
                duration_ms: elapsed,
                timestamp: new Date().toISOString(),
            };
        } catch (e: unknown) {
            const elapsed = Math.round(performance.now() - start);
            this.result = {
                success: false,
                data: { error: e instanceof Error ? e.message : 'Tool invocation failed' },
                duration_ms: elapsed,
                timestamp: new Date().toISOString(),
            };
        } finally {
            this.running = false;
            if (this.result) {
                this.resultHistory = [this.result, ...this.resultHistory.slice(0, 19)];
            }
        }
    }

    private async invokeViaRest(toolName: string, params: Record<string, unknown>): Promise<unknown> {
        // Map known tools to their REST API equivalents
        const mappings: Record<string, () => Promise<unknown>> = {
            'voyant.sql': () => api.post('/sql/query', { sql: params.sql, limit: params.limit }),
            'voyant.search': () => api.post('/search/query', { query: params.query, limit: params.limit }),
            'voyant.tables.list': () => api.get('/sql/tables'),
            'voyant.sources.list': () => api.get('/sources'),
            'voyant.sources.get': () => api.get(`/sources/${params.source_id}`),
            'voyant.jobs.list': () => api.get('/jobs'),
            'voyant.ontology.types.list': () => api.get('/ontology/types'),
            'voyant.ontology.types.get': () => api.get(`/ontology/types/${params.type_id}`),
            'voyant.ontology.objects.list': () => api.get(`/ontology/objects${params.type_id ? `?type_id=${params.type_id}` : ''}`),
            'voyant.ontology.objects.get': () => api.get(`/ontology/objects/${params.object_id}`),
            'voyant.ingest': () => api.post('/jobs/ingest', { source_id: params.source_id, mode: params.mode }),
            'voyant.profile': () => api.post('/jobs/profile', { source_id: params.source_id, table: params.table, sample_size: params.sample_size }),
            'voyant.quality': () => api.post('/jobs/quality', { source_id: params.source_id, table: params.table }),
            'voyant.analyze': () => api.post('/analyze', { source_id: params.source_id, table: params.table, sample_size: params.sample_size }),
            'voyant.status': () => api.get(`/jobs/${params.job_id}`),
        };

        const fn = mappings[toolName];
        if (fn) return fn();

        // Generic fallback: try POST to /mcp/invoke
        return api.post('/mcp/invoke', { tool: toolName, params });
    }

    private handleParamInput(key: string, value: string) {
        // Update both the structured and JSON representations
        const updated = { ...this.paramValues, [key]: value };
        this.paramValues = updated;
        this.paramJson = JSON.stringify(updated, null, 2);
    }

    /* ── Render ─────────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/mcp"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50" role="main" aria-label="MCP Playground">
            <div class="p-8">
                <div class="flex items-center justify-between mb-6">
                    <div>
                        <h1 class="text-2xl font-black font-display tracking-tight">MCP Playground</h1>
                        <p class="text-sm text-gray-500 mt-1">Explore and test ${this.tools.length} MCP tools across ${TOOL_CATEGORIES.length} categories</p>
                    </div>
                </div>

                <div class="flex gap-6" style="height: calc(100vh - 180px);">
                    <!-- Left Panel: Category Tree + Tool List -->
                    <div class="w-80 flex flex-col gap-4 flex-shrink-0">
                        <!-- Search -->
                        <div class="relative" role="search" aria-label="Search MCP tools">
                            <input type="text" class="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg bg-white" aria-label="Search tools" placeholder="Search tools..." .value=${this.searchQuery} @input=${(e: Event) => { this.searchQuery = (e.target as HTMLInputElement).value; }} />
                            <svg class="absolute left-3 top-2.5 h-4 w-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                        </div>

                        <!-- Category Tree -->
                        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden flex-1">
                            <div class="p-3 border-b border-gray-100">
                                <button class="w-full text-left px-2 py-1.5 text-xs font-semibold rounded ${this.selectedCategory === '' ? 'bg-brand text-white' : 'text-gray-500 hover:bg-gray-50'}" @click=${() => { this.selectedCategory = ''; }}>
                                    All Tools (${this.tools.length})
                                </button>
                            </div>
                            <div class="overflow-y-auto" style="max-height: calc(100% - 44px);">
                                ${TOOL_CATEGORIES.map(cat => {
                                    const tools = this.categoryTree[cat];
                                    const isActive = this.selectedCategory === cat;
                                    return html`
                                    <div>
                                        <button class="w-full flex items-center justify-between px-3 py-2 text-sm font-medium transition-colors ${isActive ? 'bg-brand/5 text-brand' : 'text-gray-700 hover:bg-gray-50'}" aria-expanded=${isActive} @click=${() => { this.selectedCategory = isActive ? '' : cat; }}>
                                            <span class="flex items-center gap-2">
                                                <span>${CATEGORY_ICONS[cat] || '📦'}</span>
                                                <span>${cat}</span>
                                            </span>
                                            <span class="text-xs text-gray-500">${tools.length}</span>
                                        </button>
                                        ${isActive ? html`
                                        <div class="border-t border-gray-50">
                                            ${tools.map(t => html`
                                            <button class="w-full text-left px-6 py-1.5 text-xs transition-colors ${this.selectedTool?.name === t.name ? 'bg-brand/10 text-brand font-semibold' : 'text-gray-500 hover:bg-gray-50 hover:text-ink'}" @click=${() => this.selectTool(t)}>
                                                <span class="font-mono">${t.name.split('.').pop()}</span>
                                            </button>`)}
                                        </div>` : ''}
                                    </div>`;
                                })}
                            </div>
                        </div>
                    </div>

                    <!-- Right Panel: Tool Detail + Test -->
                    <div class="flex-1 flex flex-col gap-4 min-w-0">
                        ${this.selectedTool ? this.renderToolDetail() : this.renderToolList()}
                    </div>
                </div>
            </div>
        </main>`;
    }

    private renderToolList() {
        return html`
        <div class="flex-1 bg-white rounded-xl border border-gray-100 overflow-hidden">
            <div class="p-4 border-b border-gray-100">
                <h3 class="text-sm font-semibold text-gray-500">
                    ${this.selectedCategory || 'All Tools'} — ${this.filteredTools.length} tools
                </h3>
            </div>
            <div class="overflow-y-auto divide-y divide-gray-50" style="max-height: calc(100% - 52px);">
                ${this.filteredTools.map(t => html`
                <button class="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors" aria-label="MCP tool: ${t.name} - ${t.description}" @click=${() => this.selectTool(t)}>
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-mono font-semibold text-brand">${t.name}</span>
                            <span class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-500">${t.category}</span>
                        </div>
                        <svg class="h-4 w-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                    <p class="text-xs text-gray-500 mt-0.5">${t.description}</p>
                </button>`)}
            </div>
        </div>`;
    }

    private renderToolDetail() {
        const t = this.selectedTool!;
        const props = (t.params as Record<string, Record<string, unknown>>)?.properties || {};
        const required = (t.params as Record<string, string[]>)?.required || [];
        const propEntries = Object.entries(props);

        return html`
        <div class="flex gap-4 flex-1 min-h-0">
            <!-- Tool Detail + Params -->
            <div class="flex-1 flex flex-col gap-4 min-w-0">
                <!-- Header -->
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-3">
                            <span class="text-lg font-mono font-bold">${t.name}</span>
                            <span class="px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-500">${t.category}</span>
                        </div>
                        <button class="px-3 py-1.5 text-xs border border-gray-200 rounded-lg bg-white hover:bg-gray-50" @click=${() => { this.selectedTool = null; }}>← Back to list</button>
                    </div>
                    <p class="text-sm text-gray-600">${t.description}</p>
                </div>

                <!-- Parameters Form -->
                <div class="bg-white rounded-xl border border-gray-100 flex-1 overflow-hidden flex flex-col">
                    <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                        <h3 class="text-xs font-semibold text-gray-500 uppercase">Parameters</h3>
                        <span class="text-[10px] text-gray-500">${propEntries.length} params · ${required.length} required</span>
                    </div>
                    <div class="flex-1 overflow-y-auto p-5 space-y-4">
                        ${propEntries.length === 0 ? html`
                        <div class="text-sm text-gray-500 text-center py-8">This tool takes no parameters</div>` : ''}

                        ${propEntries.map(([key, schema]) => {
                            const isRequired = required.includes(key);
                            const s = schema as Record<string, unknown>;
                            return html`
                            <div>
                                <label class="flex items-center gap-1 mb-1">
                                    <span class="text-xs font-medium text-gray-700 font-mono">${key}</span>
                                    ${isRequired ? html`<span class="text-[10px] text-red-500">*</span>` : ''}
                                    <span class="text-[10px] text-gray-500 ml-1">${s.type as string}${s.default !== undefined ? ` = ${JSON.stringify(s.default)}` : ''}</span>
                                </label>
                                ${s.description ? html`<p class="text-[10px] text-gray-500 mb-1">${s.description as string}</p>` : ''}
                                ${s.type === 'boolean' ? html`
                                <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white" @change=${(e: Event) => this.handleParamInput(key, (e.target as HTMLSelectElement).value)}>
                                    <option value="false">false</option>
                                    <option value="true">true</option>
                                </select>` : s.type === 'string' && s.enum ? html`
                                <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white" @change=${(e: Event) => this.handleParamInput(key, (e.target as HTMLSelectElement).value)}>
                                    ${(s.enum as string[]).map(v => html`<option value="${v}">${v}</option>`)}
                                </select>` : html`
                                <input type=${s.type === 'integer' || s.type === 'number' ? 'number' : 'text'}
                                    class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono"
                                    placeholder=${s.type === 'array' ? '["item1", "item2"]' : s.type === 'object' ? '{"key": "value"}' : String(s.type)}
                                    .value=${String(this.paramValues[key] ?? '')}
                                    @input=${(e: Event) => this.handleParamInput(key, (e.target as HTMLInputElement).value)} />`}
                            </div>`;
                        })}

                        <!-- Raw JSON editor -->
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">Raw JSON</label>
                            <textarea class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono h-32 resize-none" .value=${this.paramJson} @input=${(e: Event) => { this.paramJson = (e.target as HTMLTextAreaElement).value; }}></textarea>
                        </div>
                    </div>

                    <!-- Run Button -->
                    <div class="px-5 py-3 border-t border-gray-100 flex items-center gap-3">
                        <button class="px-5 py-2 text-sm font-bold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.running ? 'opacity-50' : ''}" ?disabled=${this.running} aria-label="${this.running ? 'Running tool, please wait' : 'Run tool'}" @click=${() => this.runTool()}>
                            ${this.running ? html`<span class="animate-spin inline-block mr-1">⏳</span> Running...` : '▶ Run Tool'}
                        </button>
                        ${this.result ? html`
                        <span class="text-xs ${this.result.success ? 'text-green-600' : 'text-red-600'}">
                            ${this.result.success ? '✓ Success' : '✗ Error'} · ${this.result.duration_ms}ms
                        </span>` : ''}
                    </div>
                </div>
            </div>

            <!-- Result Panel -->
            <div class="w-[420px] flex flex-col gap-4 flex-shrink-0">
                <!-- JSON Schema -->
                <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                    <div class="px-4 py-3 border-b border-gray-100">
                        <h3 class="text-xs font-semibold text-gray-500 uppercase">JSON Schema</h3>
                    </div>
                    <div class="p-4 max-h-48 overflow-y-auto">
                        <pre class="text-xs font-mono text-gray-700 whitespace-pre-wrap">${JSON.stringify(t.params, null, 2)}</pre>
                    </div>
                </div>

                <!-- Response -->
                <div class="bg-white rounded-xl border border-gray-100 flex-1 overflow-hidden flex flex-col" aria-live="polite">
                    <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                        <h3 class="text-xs font-semibold text-gray-500 uppercase">Response</h3>
                        ${this.result ? html`
                        <span class="text-[10px] font-mono ${this.result.success ? 'text-green-600' : 'text-red-600'}">${this.result.timestamp}</span>` : ''}
                    </div>
                    <div class="flex-1 overflow-y-auto p-4">
                        ${this.result ? html`
                        <pre class="text-xs font-mono whitespace-pre-wrap ${this.result.success ? 'text-gray-700' : 'text-red-600'}">${JSON.stringify(this.result.data, null, 2)}</pre>` : html`
                        <div class="text-sm text-gray-500 text-center py-8">Run a tool to see results here</div>`}
                    </div>
                </div>

                <!-- History -->
                ${this.resultHistory.length > 0 ? html`
                <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                    <div class="px-4 py-3 border-b border-gray-100">
                        <h3 class="text-xs font-semibold text-gray-500 uppercase">History (${this.resultHistory.length})</h3>
                    </div>
                    <div class="max-h-32 overflow-y-auto divide-y divide-gray-50">
                        ${this.resultHistory.slice(0, 5).map((r, i) => html`
                        <div class="px-4 py-2 flex items-center justify-between text-xs">
                            <span class="${r.success ? 'text-green-600' : 'text-red-600'}">${r.success ? '✓' : '✗'}</span>
                            <span class="font-mono text-gray-500">${r.duration_ms}ms</span>
                            <span class="text-gray-500">${new Date(r.timestamp).toLocaleTimeString()}</span>
                        </div>`)}
                    </div>
                </div>` : ''}
            </div>
        </div>`;
    }
}
