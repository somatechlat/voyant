import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import { getToken } from '../lib/api';
import '../components/saas-sidebar';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface AgentDef {
    id: string;
    name: string;
    description?: string;
    status: string;
    model_provider: string;
    model_name: string;
    temperature: number;
    max_tokens: number;
    system_prompt: string;
    tools: string[];
    guardrails: Record<string, unknown>;
    tools_count?: number;
    created_at: string;
    evaluations?: AgentEvalSummary[];
}

interface AgentEvalSummary {
    id: string;
    name: string;
    status: string;
    overall_score: number;
    run_count: number;
    passed_count?: number;
}

interface AgentEvalDetail extends AgentEvalSummary {
    test_cases: Array<Record<string, unknown>>;
    results: Array<Record<string, unknown>>;
    judge_model: string;
}

interface LiveSession {
    id: string;
    agent_id: string;
    agent_name: string;
    user: string;
    started_at: string;
    messages: number;
    status: string;
}

/* ── Known MCP tools for the picker ─────────────────────────────────────────── */

const MCP_TOOLS: Array<{ name: string; category: string; description: string; params: Record<string, unknown> }> = [
    // Data Ops
    { name: 'voyant.sql', category: 'Data Ops', description: 'Execute read-only SQL via Trino', params: { type: 'object', properties: { sql: { type: 'string' }, limit: { type: 'integer', default: 1000 } }, required: ['sql'] } },
    { name: 'voyant.search', category: 'Data Ops', description: 'Semantic vector search across indexed data', params: { type: 'object', properties: { query: { type: 'string' }, limit: { type: 'integer', default: 5 } }, required: ['query'] } },
    { name: 'voyant.kpi', category: 'Data Ops', description: 'Run KPI queries and return aggregated results', params: { type: 'object', properties: { kpis: { type: 'array' }, limit: { type: 'integer', default: 1000 } }, required: ['kpis'] } },
    { name: 'voyant.tables.list', category: 'Data Ops', description: 'List available tables in the data warehouse', params: { type: 'object', properties: { schema: { type: 'string' } } } },
    { name: 'voyant.tables.columns', category: 'Data Ops', description: 'List columns for a given table', params: { type: 'object', properties: { table: { type: 'string' }, schema: { type: 'string' } }, required: ['table'] } },
    // Catalog
    { name: 'voyant.sources.list', category: 'Catalog', description: 'List all data sources for a tenant', params: { type: 'object', properties: {} } },
    { name: 'voyant.sources.get', category: 'Catalog', description: 'Get a data source with connection config', params: { type: 'object', properties: { source_id: { type: 'string' } }, required: ['source_id'] } },
    { name: 'voyant.sources.delete', category: 'Catalog', description: 'Delete a data source', params: { type: 'object', properties: { source_id: { type: 'string' } }, required: ['source_id'] } },
    { name: 'voyant.discover', category: 'Catalog', description: 'Auto-detect source type from a URL/DSN hint', params: { type: 'object', properties: { hint: { type: 'string' } }, required: ['hint'] } },
    { name: 'voyant.connect', category: 'Catalog', description: 'Register a new data source', params: { type: 'object', properties: { name: { type: 'string' }, source_type: { type: 'string' }, connection_config: { type: 'object' } }, required: ['name', 'source_type', 'connection_config'] } },
    { name: 'voyant.discovery.services.list', category: 'Catalog', description: 'List registered microservice definitions', params: { type: 'object', properties: { tag: { type: 'string' } } } },
    { name: 'voyant.discovery.services.get', category: 'Catalog', description: 'Get a microservice definition by name', params: { type: 'object', properties: { name: { type: 'string' } }, required: ['name'] } },
    { name: 'voyant.discovery.services.register', category: 'Catalog', description: 'Register a new microservice', params: { type: 'object', properties: { name: { type: 'string' }, base_url: { type: 'string' }, spec_url: { type: 'string' } }, required: ['name', 'base_url'] } },
    { name: 'voyant.discovery.scan', category: 'Catalog', description: 'Scan an OpenAPI spec URL', params: { type: 'object', properties: { url: { type: 'string' } }, required: ['url'] } },
    { name: 'voyant.lineage', category: 'Catalog', description: 'Fetch upstream/downstream lineage from DataHub', params: { type: 'object', properties: { urn: { type: 'string' }, direction: { type: 'string', default: 'both' }, depth: { type: 'integer', default: 3 } }, required: ['urn'] } },
    // Scraper
    { name: 'scrape.fetch', category: 'Scraper', description: 'Fetch a web page with JS rendering support', params: { type: 'object', properties: { url: { type: 'string' }, engine: { type: 'string', default: 'playwright' } }, required: ['url'] } },
    { name: 'scrape.deep_archive', category: 'Scraper', description: 'Deep archival scrape with tab navigation', params: { type: 'object', properties: { url: { type: 'string' } }, required: ['url'] } },
    { name: 'scrape.extract', category: 'Scraper', description: 'Extract structured data from HTML via selectors', params: { type: 'object', properties: { html: { type: 'string' }, selectors: { type: 'object' } }, required: ['html', 'selectors'] } },
    { name: 'scrape.ocr', category: 'Scraper', description: 'OCR on images via Tesseract', params: { type: 'object', properties: { images: { type: 'array' } }, required: ['images'] } },
    { name: 'scrape.parse_pdf', category: 'Scraper', description: 'Parse PDF for text and tables', params: { type: 'object', properties: { pdf_url: { type: 'string' }, extract_tables: { type: 'boolean' } }, required: ['pdf_url'] } },
    { name: 'scrape.transcribe', category: 'Scraper', description: 'Transcribe audio/video via Whisper', params: { type: 'object', properties: { media_urls: { type: 'array' }, language: { type: 'string', default: 'es' } }, required: ['media_urls'] } },
    { name: 'voyant.scraper.templates.list', category: 'Scraper', description: 'List scraper templates', params: { type: 'object', properties: { category: { type: 'string' } } } },
    { name: 'voyant.scraper.templates.get', category: 'Scraper', description: 'Get template detail', params: { type: 'object', properties: { template_id: { type: 'string' } }, required: ['template_id'] } },
    { name: 'voyant.scraper.templates.search', category: 'Scraper', description: 'Search templates', params: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] } },
    { name: 'voyant.scraper.templates.create', category: 'Scraper', description: 'Create a new scraper template', params: { type: 'object', properties: { name: { type: 'string' }, category: { type: 'string' }, site_pattern: { type: 'string' }, workflow: { type: 'array' } }, required: ['name', 'category', 'site_pattern', 'workflow'] } },
    { name: 'voyant.scraper.templates.validate', category: 'Scraper', description: 'Validate a template definition', params: { type: 'object', properties: { template: { type: 'object' } }, required: ['template'] } },
    { name: 'voyant.scraper.templates.run', category: 'Scraper', description: 'Run a scraper template', params: { type: 'object', properties: { template_id: { type: 'string' }, parameters: { type: 'object' } }, required: ['template_id'] } },
    { name: 'voyant.scraper.templates.generate', category: 'Scraper', description: 'Auto-generate template from URL', params: { type: 'object', properties: { url: { type: 'string' }, name: { type: 'string' } }, required: ['url'] } },
    { name: 'voyant.scraper.templates.export', category: 'Scraper', description: 'Export template as JSON or Python', params: { type: 'object', properties: { template_id: { type: 'string' }, format: { type: 'string', default: 'json' } }, required: ['template_id'] } },
    { name: 'voyant.templates.execute', category: 'Scraper', description: 'Execute a UPTP template', params: { type: 'object', properties: { template_id: { type: 'string' }, category: { type: 'string' }, tenant_id: { type: 'string' }, params: { type: 'object' } }, required: ['template_id', 'category', 'tenant_id', 'params'] } },
    // Ontology
    { name: 'voyant.ontology.types.list', category: 'Ontology', description: 'List all object types', params: { type: 'object', properties: {} } },
    { name: 'voyant.ontology.types.get', category: 'Ontology', description: 'Get object type with properties', params: { type: 'object', properties: { type_id: { type: 'string' } }, required: ['type_id'] } },
    { name: 'voyant.ontology.types.create', category: 'Ontology', description: 'Create a new object type', params: { type: 'object', properties: { name: { type: 'string' }, description: { type: 'string' }, properties: { type: 'array' } }, required: ['name'] } },
    { name: 'voyant.ontology.objects.list', category: 'Ontology', description: 'List object instances', params: { type: 'object', properties: { type_id: { type: 'string' }, limit: { type: 'integer', default: 100 } } } },
    { name: 'voyant.ontology.objects.create', category: 'Ontology', description: 'Create an object instance', params: { type: 'object', properties: { type_id: { type: 'string' }, properties: { type: 'object' } }, required: ['type_id', 'properties'] } },
    { name: 'voyant.ontology.objects.get', category: 'Ontology', description: 'Get object with links', params: { type: 'object', properties: { object_id: { type: 'string' } }, required: ['object_id'] } },
    { name: 'voyant.ontology.objects.update', category: 'Ontology', description: 'Update an object instance', params: { type: 'object', properties: { object_id: { type: 'string' }, properties: { type: 'object' } }, required: ['object_id', 'properties'] } },
    { name: 'voyant.ontology.objects.batch_create', category: 'Ontology', description: 'Batch create objects', params: { type: 'object', properties: { type_id: { type: 'string' }, items: { type: 'array' } }, required: ['type_id', 'items'] } },
    { name: 'voyant.ontology.links.create', category: 'Ontology', description: 'Create a link between objects', params: { type: 'object', properties: { link_type_id: { type: 'string' }, source_object_id: { type: 'string' }, target_object_id: { type: 'string' } }, required: ['link_type_id', 'source_object_id', 'target_object_id'] } },
    { name: 'voyant.ontology.links.delete', category: 'Ontology', description: 'Delete a link', params: { type: 'object', properties: { link_id: { type: 'string' } }, required: ['link_id'] } },
    { name: 'voyant.ontology.traverse', category: 'Ontology', description: 'Traverse object graph', params: { type: 'object', properties: { object_id: { type: 'string' }, direction: { type: 'string', default: 'outgoing' }, max_depth: { type: 'integer', default: 1 } }, required: ['object_id'] } },
    { name: 'voyant.ontology.interfaces.list', category: 'Ontology', description: 'List polymorphic interfaces', params: { type: 'object', properties: {} } },
    { name: 'voyant.ontology.actions.execute', category: 'Ontology', description: 'Execute an action on an object', params: { type: 'object', properties: { action_type_id: { type: 'string' }, object_id: { type: 'string' }, params: { type: 'object' } }, required: ['action_type_id', 'object_id'] } },
    { name: 'voyant.ontology.functions.run', category: 'Ontology', description: 'Run an ontology function', params: { type: 'object', properties: { function_id: { type: 'string' }, input_data: { type: 'object' } }, required: ['function_id'] } },
    // Governance
    { name: 'voyant.governance.schema', category: 'Governance', description: 'Fetch governance schema from DataHub', params: { type: 'object', properties: { urn: { type: 'string' } }, required: ['urn'] } },
    { name: 'voyant.quotas.tiers', category: 'Governance', description: 'List quota tiers', params: { type: 'object', properties: {} } },
    { name: 'voyant.quotas.usage', category: 'Governance', description: 'Get current quota usage', params: { type: 'object', properties: {} } },
    { name: 'voyant.quotas.limits', category: 'Governance', description: 'Get quota limits', params: { type: 'object', properties: {} } },
    { name: 'voyant.quotas.set_tier', category: 'Governance', description: 'Set tenant quota tier', params: { type: 'object', properties: { tier: { type: 'string' } }, required: ['tier'] } },
    { name: 'voyant.presets.list', category: 'Governance', description: 'List preset jobs', params: { type: 'object', properties: {} } },
    { name: 'voyant.presets.get', category: 'Governance', description: 'Get a preset job', params: { type: 'object', properties: { job_id: { type: 'string' } }, required: ['job_id'] } },
    { name: 'voyant.preset', category: 'Governance', description: 'Create a preset job', params: { type: 'object', properties: { preset_name: { type: 'string' }, payload: { type: 'object' } }, required: ['preset_name', 'payload'] } },
    // ML
    { name: 'voyant.ingest', category: 'ML', description: 'Start data ingestion workflow', params: { type: 'object', properties: { source_id: { type: 'string' }, mode: { type: 'string', default: 'full' } }, required: ['source_id'] } },
    { name: 'voyant.profile', category: 'ML', description: 'Run data profiling', params: { type: 'object', properties: { source_id: { type: 'string' }, table: { type: 'string' }, sample_size: { type: 'integer', default: 10000 } }, required: ['source_id'] } },
    { name: 'voyant.quality', category: 'ML', description: 'Run quality checks', params: { type: 'object', properties: { source_id: { type: 'string' }, table: { type: 'string' } }, required: ['source_id'] } },
    { name: 'voyant.analyze', category: 'ML', description: 'Run full analysis pipeline', params: { type: 'object', properties: { source_id: { type: 'string' }, table: { type: 'string' }, sample_size: { type: 'integer', default: 10000 } }, required: ['source_id'] } },
    { name: 'voyant.status', category: 'ML', description: 'Check job status', params: { type: 'object', properties: { job_id: { type: 'string' } }, required: ['job_id'] } },
    { name: 'voyant.artifact', category: 'ML', description: 'Get artifact metadata', params: { type: 'object', properties: { artifact_id: { type: 'string' } }, required: ['artifact_id'] } },
    { name: 'voyant.artifacts.list', category: 'ML', description: 'List artifacts for a job', params: { type: 'object', properties: { job_id: { type: 'string' } }, required: ['job_id'] } },
    { name: 'voyant.vector.search', category: 'ML', description: 'Hybrid vector search (dense + sparse)', params: { type: 'object', properties: { query: { type: 'string' }, limit: { type: 'integer', default: 5 } }, required: ['query'] } },
    { name: 'voyant.vector.index', category: 'ML', description: 'Index text into vector store', params: { type: 'object', properties: { text: { type: 'string' }, metadata: { type: 'object' } }, required: ['text'] } },
    // Streaming
    { name: 'voyant.jobs.list', category: 'Streaming', description: 'List jobs with optional filters', params: { type: 'object', properties: { status: { type: 'string' }, job_type: { type: 'string' }, limit: { type: 'integer', default: 50 } } } },
    { name: 'voyant.jobs.cancel', category: 'Streaming', description: 'Cancel a running job', params: { type: 'object', properties: { job_id: { type: 'string' } }, required: ['job_id'] } },
    { name: 'voyant.kpi_templates.list', category: 'Streaming', description: 'List KPI templates', params: { type: 'object', properties: { category: { type: 'string' } } } },
    { name: 'voyant.kpi_templates.categories', category: 'Streaming', description: 'List KPI template categories', params: { type: 'object', properties: {} } },
    { name: 'voyant.kpi_templates.get', category: 'Streaming', description: 'Get a KPI template by name', params: { type: 'object', properties: { name: { type: 'string' } }, required: ['name'] } },
    { name: 'voyant.kpi_templates.render', category: 'Streaming', description: 'Render a KPI template to SQL', params: { type: 'object', properties: { name: { type: 'string' }, params: { type: 'object' } }, required: ['name', 'params'] } },
];

const TOOL_CATEGORIES = ['Data Ops', 'Catalog', 'Scraper', 'Ontology', 'Governance', 'ML', 'Streaming'];

const MODEL_OPTIONS = [
    { provider: 'groq', name: 'openai/gpt-oss-120b', label: 'GPT-OSS 120B (Groq)' },
    { provider: 'groq', name: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B (Groq)' },
    { provider: 'openai', name: 'gpt-4o', label: 'GPT-4o (OpenAI)' },
    { provider: 'openai', name: 'gpt-4o-mini', label: 'GPT-4o Mini (OpenAI)' },
    { provider: 'anthropic', name: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4 (Anthropic)' },
    { provider: 'anthropic', name: 'claude-haiku-4-20250414', label: 'Claude Haiku 4 (Anthropic)' },
    { provider: 'ollama', name: 'llama3:70b', label: 'Llama 3 70B (Ollama)' },
];

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-agents')
export class ViewAgents extends LitElement {
    @state() tab: 'definitions' | 'sessions' | 'evaluations' | 'deployments' = 'definitions';
    @state() agents: AgentDef[] = [];
    @state() evaluations: AgentEvalSummary[] = [];
    @state() sessions: LiveSession[] = [];
    @state() loading = true;

    // Deployment monitoring
    @state() deployments: Array<{
        id: string; name: string; status: string; endpoint_path: string;
        invocation_count: number; avg_latency_ms: number;
        model_name?: string; model_version?: string;
    }> = [];
    @state() deploymentMetrics: Record<string, Array<{
        timestamp: string; latency_p50: number; latency_p95: number;
        latency_p99: number; throughput_rps: number; error_rate: number;
    }>> = {};
    @state() deploymentsLoading = false;

    // Agent detail/edit
    @state() selectedAgent: AgentDef | null = null;
    @state() showEditModal = false;
    @state() editAgent: Partial<AgentDef> = {};
    @state() saving = false;
    @state() saveResult = '';

    // Tool picker
    @state() toolSearch = '';
    @state() toolCategoryFilter = '';

    // Evaluation
    @state() showEvalModal = false;
    @state() evalAgentId = '';
    @state() evalName = '';
    @state() evalTestCases = '';
    @state() creatingEval = false;

    // WebSocket state
    @state() wsConnected: boolean = false;
    @state() wsReconnecting: boolean = false;
    private _ws: WebSocket | null = null;
    private _wsReconnectTimer: ReturnType<typeof setTimeout> | null = null;
    private _wsReconnectAttempts: number = 0;
    private readonly _wsMaxReconnectAttempts: number = 10;
    private readonly _wsBaseDelay: number = 1000;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadAgents();
        this._connectWebSocket();
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        this._disconnectWebSocket();
    }

    /* ── WebSocket ──────────────────────────────────────────────────────────── */

    private _connectWebSocket() {
        if (this._ws) return;

        const token = getToken();
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const url = `${protocol}//${host}/ws/agents/${token ? `?token=${encodeURIComponent(token)}` : ''}`;

        try {
            this._ws = new WebSocket(url);
        } catch {
            this.wsConnected = false;
            this.wsReconnecting = false;
            return;
        }

        this._ws.onopen = () => {
            this.wsConnected = true;
            this.wsReconnecting = false;
            this._wsReconnectAttempts = 0;
            // Subscribe to agent events channel
            this._ws?.send(JSON.stringify({
                action: 'subscribe',
                channels: ['agent_events'],
            }));
        };

        this._ws.onmessage = (event: MessageEvent) => {
            try {
                const msg = JSON.parse(event.data);
                this._handleWsMessage(msg);
            } catch { /* ignore parse errors */ }
        };

        this._ws.onclose = () => {
            this.wsConnected = false;
            this._ws = null;
            this._scheduleReconnect();
        };

        this._ws.onerror = () => {
            this.wsConnected = false;
        };
    }

    private _disconnectWebSocket() {
        if (this._wsReconnectTimer) {
            clearTimeout(this._wsReconnectTimer);
            this._wsReconnectTimer = null;
        }
        if (this._ws) {
            this._ws.onclose = null; // prevent reconnect on intentional close
            this._ws.close();
            this._ws = null;
        }
        this.wsConnected = false;
        this.wsReconnecting = false;
    }

    private _scheduleReconnect() {
        if (this._wsReconnectAttempts >= this._wsMaxReconnectAttempts) return;
        this.wsReconnecting = true;
        const delay = Math.min(
            this._wsBaseDelay * Math.pow(2, this._wsReconnectAttempts),
            30000,
        );
        this._wsReconnectTimer = setTimeout(() => {
            this._wsReconnectAttempts++;
            this._connectWebSocket();
        }, delay);
    }

    private _handleWsMessage(msg: Record<string, unknown>) {
        const msgType = msg.type as string;

        // Handle subscription confirmation
        if (msgType === 'subscription.confirmed' || msgType === 'authenticated' || msgType === 'connected') {
            return;
        }

        // Handle agent events on the agent_events channel
        if (msgType === 'event' && msg.channel === 'agent_events') {
            const data = msg.data as Record<string, unknown>;
            const eventType = data.event_type as string;

            // Agent definition lifecycle
            if (eventType === 'agent_definition.created' || eventType === 'agent_definition.updated' || eventType === 'agent_definition.deleted') {
                this.loadAgents();
            }

            // Agent session events
            if (eventType === 'agent_session.started' || eventType === 'agent_session.updated' || eventType === 'agent_session.ended') {
                this._upsertSession(data);
            }

            // Evaluation completed
            if (eventType === 'agent_evaluation.completed') {
                this._updateEvaluationScore(data);
            }
        }
    }

    private _upsertSession(data: Record<string, unknown>) {
        const sessionId = data.session_id as string;
        if (!sessionId) return;

        const existing = this.sessions.find(s => s.id === sessionId);
        const session: LiveSession = {
            id: sessionId,
            agent_id: (data.agent_id as string) || '',
            agent_name: (data.agent_name as string) || 'Unknown',
            user: (data.user as string) || 'Unknown',
            started_at: (data.started_at as string) || new Date().toISOString(),
            messages: (data.messages as number) || 0,
            status: (data.status as string) || 'online',
        };

        if (data.event_type === 'agent_session.ended') {
            session.status = 'ended';
        }

        if (existing) {
            const idx = this.sessions.indexOf(existing);
            this.sessions = [...this.sessions.slice(0, idx), session, ...this.sessions.slice(idx + 1)];
        } else {
            this.sessions = [session, ...this.sessions];
        }
    }

    private _updateEvaluationScore(data: Record<string, unknown>) {
        const evalId = data.evaluation_id as string;
        if (!evalId) return;

        const existing = this.evaluations.find(e => e.id === evalId);
        if (existing) {
            const score = data.overall_score as number;
            const passed = data.passed_count as number;
            this.evaluations = this.evaluations.map(e =>
                e.id === evalId
                    ? { ...e, overall_score: score ?? e.overall_score, passed_count: passed ?? e.passed_count, status: 'completed' }
                    : e,
            );
        } else {
            // Reload evaluations to pick up the new one
            this.loadEvaluations();
        }
    }

    async loadAgents() {
        this.loading = true;
        try {
            this.agents = await api.get<AgentDef[]>('/ml/agents');
        } catch { this.agents = []; }
        finally { this.loading = false; }
    }

    async loadEvaluations() {
        if (this.agents.length === 0) return;
        try {
            const allEvals: AgentEvalSummary[] = [];
            for (const agent of this.agents) {
                try {
                    const evals = await api.get<AgentEvalSummary[]>(`/ml/agents/${agent.id}/evaluations`);
                    allEvals.push(...evals.map(e => ({ ...e, agent_name: agent.name } as AgentEvalSummary & { agent_name: string })));
                } catch { /* skip */ }
            }
            this.evaluations = allEvals;
        } catch { this.evaluations = []; }
    }

    async loadDeployments() {
        this.deploymentsLoading = true;
        try {
            this.deployments = await api.get<Array<{
                id: string; name: string; status: string; endpoint_path: string;
                invocation_count: number; avg_latency_ms: number;
                model_name?: string; model_version?: string;
            }>>('/ml/endpoints');
        } catch { this.deployments = []; }
        finally { this.deploymentsLoading = false; }
    }

    async loadDeploymentMetrics(endpointId: string) {
        try {
            const metrics = await api.get<Array<{
                timestamp: string; latency_p50: number; latency_p95: number;
                latency_p99: number; throughput_rps: number; error_rate: number;
            }>>(`/ml/endpoints/${endpointId}/metrics`);
            this.deploymentMetrics = { ...this.deploymentMetrics, [endpointId]: metrics };
        } catch { /* empty */ }
    }

    async loadAgentDetail(id: string) {
        try {
            const detail = await api.get<AgentDef>(`/ml/agents/${id}`);
            this.selectedAgent = detail;
        } catch { /* empty */ }
    }

    async saveAgent() {
        this.saving = true;
        this.saveResult = '';
        try {
            if (this.editAgent.id) {
                await api.put(`/ml/agents/${this.editAgent.id}`, this.editAgent);
                this.saveResult = 'Agent updated successfully';
            } else {
                const res = await api.post<{ id: string }>('/ml/agents', this.editAgent);
                this.saveResult = `Agent created: ${res.id}`;
            }
            this.showEditModal = false;
            await this.loadAgents();
        } catch (e: unknown) {
            this.saveResult = `Error: ${e instanceof Error ? e.message : 'Failed'}`;
        } finally { this.saving = false; }
    }

    async deleteAgent(id: string) {
        if (!confirm('Delete this agent definition?')) return;
        try {
            await api.del(`/ml/agents/${id}`);
            this.selectedAgent = null;
            await this.loadAgents();
        } catch { /* empty */ }
    }

    async createEvaluation() {
        if (!this.evalAgentId || !this.evalTestCases.trim()) return;
        this.creatingEval = true;
        try {
            let testCases: Array<Record<string, unknown>>;
            try {
                testCases = JSON.parse(this.evalTestCases);
            } catch {
                // Build a simple test case from lines
                testCases = this.evalTestCases.split('\n').filter(l => l.trim()).map(line => ({
                    input: line.trim(),
                    expected: 'Should provide a useful answer',
                }));
            }
            await api.post(`/ml/agents/${this.evalAgentId}/evaluations`, {
                name: this.evalName || `eval-${Date.now()}`,
                test_cases: testCases,
            });
            this.showEvalModal = false;
            this.evalTestCases = '';
            this.evalName = '';
            await this.loadEvaluations();
        } catch { /* empty */ }
        finally { this.creatingEval = false; }
    }

    async runEvaluation(evalId: string) {
        try {
            await api.post(`/ml/evaluations/${evalId}/run`);
            // Refresh
            await this.loadEvaluations();
        } catch { /* empty */ }
    }

    openCreateModal() {
        this.editAgent = {
            name: '',
            description: '',
            system_prompt: 'You are a helpful data analyst agent.',
            model_provider: 'groq',
            model_name: 'openai/gpt-oss-120b',
            temperature: 0.1,
            max_tokens: 4096,
            tools: [],
            guardrails: { max_queries_per_session: 50, max_sql_rows: 10000 },
        };
        this.showEditModal = true;
    }

    openEditModal(agent: AgentDef) {
        this.editAgent = { ...agent };
        this.showEditModal = true;
    }

    private toggleTool(toolName: string) {
        const tools = [...(this.editAgent.tools || [])];
        const idx = tools.indexOf(toolName);
        if (idx >= 0) tools.splice(idx, 1);
        else tools.push(toolName);
        this.editAgent = { ...this.editAgent, tools };
    }

    private get filteredTools() {
        let tools = MCP_TOOLS;
        if (this.toolCategoryFilter) {
            tools = tools.filter(t => t.category === this.toolCategoryFilter);
        }
        if (this.toolSearch) {
            const q = this.toolSearch.toLowerCase();
            tools = tools.filter(t => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q));
        }
        return tools;
    }

    private statusBadge(s: string) {
        const colors: Record<string, string> = {
            active: 'bg-green-50 text-green-700 border-green-200',
            draft: 'bg-amber-50 text-amber-700 border-amber-200',
            archived: 'bg-gray-50 text-gray-500 border-gray-200',
            completed: 'bg-green-50 text-green-700 border-green-200',
            running: 'bg-blue-50 text-blue-700 border-blue-200',
            pending: 'bg-amber-50 text-amber-700 border-amber-200',
            online: 'bg-green-50 text-green-700 border-green-200',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[s] || colors.draft}">${s}</span>`;
    }

    private scoreBar(score: number) {
        const pct = Math.round(score * 100);
        const color = pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500';
        return html`
            <div class="flex items-center gap-2">
                <div class="w-24 bg-gray-100 rounded-full h-1.5">
                    <div class="${color} h-1.5 rounded-full" style="width:${pct}%"></div>
                </div>
                <span class="text-xs font-mono">${pct}%</span>
            </div>`;
    }

    /* ── Render ─────────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/agents"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Agent Control Center">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Agent Control Center</h1>
                    <p class="text-sm text-gray-400 mt-1">Define, test, and evaluate AI agents with MCP tool access</p>
                </div>
                <div class="flex gap-2">
                    <!-- Connection status indicator -->
                    <div class="flex items-center gap-2 px-3 py-1.5 text-xs border border-gray-200 rounded-lg bg-white" role="status" aria-label="WebSocket ${this.wsConnected ? 'connected' : this.wsReconnecting ? 'reconnecting' : 'disconnected'}">
                        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${this.wsConnected ? '#22c55e' : this.wsReconnecting ? '#eab308' : '#ef4444'}"></span>
                        <span class="text-gray-500">${this.wsConnected ? 'Live' : this.wsReconnecting ? 'Reconnecting...' : 'Offline'}</span>
                    </div>
                    <button class="px-4 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                        aria-label="Create new agent definition" @click=${() => this.openCreateModal()}>+ New Agent</button>
                </div>
            </div>

            <!-- Tab Bar -->
            <div class="flex gap-1 mb-6 bg-white rounded-lg p-1 border border-gray-100 w-fit" role="tablist" aria-label="Agent sections">
                ${(['definitions', 'sessions', 'evaluations', 'deployments'] as const).map(t => html`
                <button class="px-4 py-2 text-sm font-semibold rounded-md transition-colors ${this.tab === t ? 'bg-brand text-white' : 'text-gray-500 hover:text-ink'}"
                    role="tab" aria-selected=${this.tab === t}
                    @click=${() => {
                        this.tab = t;
                        if (t === 'evaluations') this.loadEvaluations();
                        if (t === 'deployments') this.loadDeployments();
                    }}>
                    ${t === 'definitions' ? 'Definitions' : t === 'sessions' ? 'Live Sessions' : t === 'evaluations' ? 'Evaluations' : 'Deployments'}
                </button>`)}
            </div>

            ${this.loading ? html`<div class="text-center text-gray-400 py-16" role="status" aria-live="polite">Loading...</div>` : ''}

            <!-- Definitions Tab -->
            ${this.tab === 'definitions' && !this.loading ? this.renderDefinitions() : ''}

            <!-- Live Sessions Tab -->
            ${this.tab === 'sessions' && !this.loading ? this.renderSessions() : ''}

            <!-- Evaluations Tab -->
            ${this.tab === 'evaluations' && !this.loading ? this.renderEvaluations() : ''}

            <!-- Deployments Tab -->
            ${this.tab === 'deployments' && !this.loading ? this.renderDeployments() : ''}

            ${this.saveResult ? html`
            <div class="fixed bottom-6 right-6 px-4 py-3 rounded-xl shadow-lg text-sm font-semibold z-50 ${this.saveResult.startsWith('Error') ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}">
                ${this.saveResult}
            </div>` : ''}
        </main>

        ${this.showEditModal ? this.renderEditModal() : ''}
        ${this.showEvalModal ? this.renderEvalModal() : ''}
        ${this.selectedAgent ? this.renderDetailDrawer() : ''}
        `;
    }

    private renderDefinitions() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
            <table class="w-full text-sm" role="table" aria-label="Agent definitions">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">Name</th>
                    <th class="px-5 py-3">Model</th>
                    <th class="px-5 py-3">Tools</th>
                    <th class="px-5 py-3">Status</th>
                    <th class="px-5 py-3">Created</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.agents.length === 0 ? html`
                <tr><td colspan="6" class="px-5 py-12 text-center text-gray-400">
                    No agents defined. Click "+ New Agent" to create one.
                </td></tr>` : ''}
                ${this.agents.map(a => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer" role="button" tabindex="0" aria-label="Agent: ${a.name}" @click=${() => this.loadAgentDetail(a.id)} @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.loadAgentDetail(a.id); } }}>
                    <td class="px-5 py-3">
                        <div class="font-semibold">${a.name}</div>
                        <div class="text-xs text-gray-400 truncate max-w-xs">${a.description || 'No description'}</div>
                    </td>
                    <td class="px-5 py-3">
                        <span class="px-2 py-0.5 text-xs bg-gray-100 rounded font-mono">${a.model_name}</span>
                    </td>
                    <td class="px-5 py-3">
                        <span class="text-sm font-semibold">${a.tools_count ?? a.tools?.length ?? 0}</span>
                        <span class="text-xs text-gray-400 ml-1">tools</span>
                    </td>
                    <td class="px-5 py-3">${this.statusBadge(a.status)}</td>
                    <td class="px-5 py-3 text-xs text-gray-500">${new Date(a.created_at).toLocaleDateString()}</td>
                    <td class="px-5 py-3" @click=${(e: Event) => e.stopPropagation()}>
                        <div class="flex gap-2">
                            <button class="text-xs text-blue-600 hover:underline" aria-label="Edit agent ${a.name}" @click=${() => this.openEditModal(a)}>Edit</button>
                            <button class="text-xs text-red-600 hover:underline" aria-label="Delete agent ${a.name}" @click=${() => this.deleteAgent(a.id)}>Delete</button>
                        </div>
                    </td>
                </tr>`)}
                </tbody>
            </table>
        </div>`;
    }

    private renderSessions() {
        return html`
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
            <table class="w-full text-sm" role="table" aria-label="Live agent sessions">
                    <th class="px-5 py-3">Session ID</th>
                    <th class="px-5 py-3">Agent</th>
                    <th class="px-5 py-3">User</th>
                    <th class="px-5 py-3">Messages</th>
                    <th class="px-5 py-3">Status</th>
                    <th class="px-5 py-3">Started</th>
                </tr></thead>
                <tbody>
                ${this.sessions.length === 0 ? html`
                <tr><td colspan="6" class="px-5 py-16 text-center text-gray-400">
                    <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
                        <svg class="w-7 h-7 text-gray-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    </div>
                    <div class="text-sm font-semibold text-gray-600">No active sessions</div>
                    <div class="text-xs mt-2 max-w-sm mx-auto text-gray-400">Agent sessions will appear here in real-time once WebSocket integration is complete. Check back soon for live session tracking.</div>
                </td></tr>` : ''}
                ${this.sessions.map(s => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50">
                    <td class="px-5 py-3 font-mono text-xs">${s.id.slice(0, 8)}</td>
                    <td class="px-5 py-3 font-semibold">${s.agent_name}</td>
                    <td class="px-5 py-3 text-gray-500">${s.user}</td>
                    <td class="px-5 py-3">${s.messages}</td>
                    <td class="px-5 py-3">${this.statusBadge(s.status)}</td>
                    <td class="px-5 py-3 text-xs text-gray-500">${new Date(s.started_at).toLocaleString()}</td>
                </tr>`)}
                </tbody>
            </table>
        </div>`;
    }

    private renderEvaluations() {
        return html`
        <div class="flex items-center gap-2 mb-4">
            <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50" aria-label="Refresh evaluations" @click=${() => this.loadEvaluations()}>Refresh</button>
            <button class="px-4 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors" aria-label="Create new evaluation" @click=${() => { this.evalAgentId = this.agents[0]?.id || ''; this.showEvalModal = true; }}>+ New Evaluation</button>
        </div>
        <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" aria-live="polite">
            <table class="w-full text-sm" role="table" aria-label="Agent evaluations">
                <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                    <th class="px-5 py-3">Evaluation</th>
                    <th class="px-5 py-3">Agent</th>
                    <th class="px-5 py-3">Status</th>
                    <th class="px-5 py-3">Score</th>
                    <th class="px-5 py-3">Runs</th>
                    <th class="px-5 py-3">Passed</th>
                    <th class="px-5 py-3">Actions</th>
                </tr></thead>
                <tbody>
                ${this.evaluations.length === 0 ? html`
                <tr><td colspan="7" class="px-5 py-12 text-center text-gray-400">
                    No evaluations yet. Create one to test your agents.
                </td></tr>` : ''}
                ${this.evaluations.map(e => html`
                <tr class="border-b border-gray-50 hover:bg-gray-50">
                    <td class="px-5 py-3 font-semibold">${e.name}</td>
                    <td class="px-5 py-3 text-gray-500">${(e as unknown as Record<string, string>).agent_name || '—'}</td>
                    <td class="px-5 py-3">${this.statusBadge(e.status)}</td>
                    <td class="px-5 py-3">${this.scoreBar(e.overall_score)}</td>
                    <td class="px-5 py-3">${e.run_count}</td>
                    <td class="px-5 py-3">${e.passed_count ?? '—'}</td>
                    <td class="px-5 py-3">
                        <button class="text-xs text-blue-600 hover:underline" aria-label="Run evaluation ${e.name}" @click=${() => this.runEvaluation(e.id)}>Run</button>
                    </td>
                </tr>`)}
                </tbody>
            </table>
        </div>`;
    }

    private renderDeployments() {
        return html`
        <div class="flex items-center gap-2 mb-4">
            <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50" aria-label="Refresh deployments" @click=${() => this.loadDeployments()}>Refresh</button>
        </div>

        ${this.deploymentsLoading ? html`<div class="text-center text-gray-400 py-8" role="status">Loading deployments...</div>` : ''}

        ${!this.deploymentsLoading && this.deployments.length === 0 ? html`
        <div class="bg-white rounded-xl border border-gray-100 p-12 text-center" aria-live="polite">
            <div class="text-4xl opacity-20 mb-3">🚀</div>
            <div class="text-gray-500">No model deployments yet. Deploy a model from the Model Registry to create an endpoint.</div>
        </div>` : ''}

        ${this.deployments.length > 0 ? html`
        <!-- Deployment Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            ${this.deployments.map(d => html`
            <div class="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow cursor-pointer"
                 @click=${() => this.loadDeploymentMetrics(d.id)}
                 role="button" tabindex="0" aria-label="Deployment: ${d.name}">
                <div class="flex items-center justify-between mb-3">
                    <div class="font-bold text-sm">${d.name}</div>
                    ${this.statusBadge(d.status)}
                </div>
                <div class="text-xs text-gray-400 mb-3 font-mono">${d.endpoint_path || '—'}</div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <div class="text-xs text-gray-400">Invocations</div>
                        <div class="text-lg font-bold">${this.formatNumber(d.invocation_count)}</div>
                    </div>
                    <div>
                        <div class="text-xs text-gray-400">Avg Latency</div>
                        <div class="text-lg font-bold ${d.avg_latency_ms > 500 ? 'text-red-500' : d.avg_latency_ms > 200 ? 'text-yellow-500' : 'text-green-500'}">${d.avg_latency_ms?.toFixed(0) || '—'}ms</div>
                    </div>
                </div>
                ${d.model_name ? html`<div class="mt-3 text-xs text-gray-400">Model: <span class="text-gray-600">${d.model_name}</span>${d.model_version ? html` <span class="text-gray-400">v${d.model_version}</span>` : ''}</div>` : ''}
            </div>`)}
        </div>

        <!-- Metrics Detail for Selected Endpoint -->
        ${Object.entries(this.deploymentMetrics).map(([endpointId, metrics]) => {
            const endpoint = this.deployments.find(d => d.id === endpointId);
            if (!endpoint || metrics.length === 0) return '';
            const latest = metrics[metrics.length - 1];
            return html`
            <div class="bg-white rounded-xl border border-gray-100 p-5 mb-4">
                <div class="flex items-center justify-between mb-4">
                    <div class="font-bold">${endpoint.name} — Recent Metrics</div>
                    <div class="text-xs text-gray-400">${metrics.length} data points</div>
                </div>
                <div class="grid grid-cols-5 gap-4">
                    <div class="text-center">
                        <div class="text-xs text-gray-400">P50 Latency</div>
                        <div class="text-lg font-bold">${latest.latency_p50?.toFixed(0) || '—'}ms</div>
                    </div>
                    <div class="text-center">
                        <div class="text-xs text-gray-400">P95 Latency</div>
                        <div class="text-lg font-bold ${latest.latency_p95 > 500 ? 'text-red-500' : ''}">${latest.latency_p95?.toFixed(0) || '—'}ms</div>
                    </div>
                    <div class="text-center">
                        <div class="text-xs text-gray-400">P99 Latency</div>
                        <div class="text-lg font-bold">${latest.latency_p99?.toFixed(0) || '—'}ms</div>
                    </div>
                    <div class="text-center">
                        <div class="text-xs text-gray-400">Throughput</div>
                        <div class="text-lg font-bold">${latest.throughput_rps?.toFixed(1) || '—'} rps</div>
                    </div>
                    <div class="text-center">
                        <div class="text-xs text-gray-400">Error Rate</div>
                        <div class="text-lg font-bold ${(latest.error_rate || 0) > 0.05 ? 'text-red-500' : 'text-green-500'}">${((latest.error_rate || 0) * 100).toFixed(2)}%</div>
                    </div>
                </div>
            </div>`;
        })}` : ''}
        `;
    }

    private formatNumber(n: number): string {
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
        return String(n);
    }

    /* ── Edit/Create Modal ──────────────────────────────────────────────────── */

    private renderEditModal() {
        const a = this.editAgent;
        return html`
        <div class="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="${a.id ? 'Edit Agent' : 'Create Agent'}"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') { this.showEditModal = false; } }}>
            <div class="absolute inset-0 bg-black/30" @click=${() => { this.showEditModal = false; }}></div>
            <div class="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col" tabindex="-1">
                <!-- Header -->
                <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <h2 class="text-lg font-bold">${a.id ? 'Edit Agent' : 'Create Agent'}</h2>
                    <button class="text-gray-400 hover:text-ink text-xl" aria-label="Close dialog" @click=${() => { this.showEditModal = false; }}>✕</button>
                </div>

                <!-- Body -->
                <div class="flex-1 overflow-y-auto p-6 space-y-6">
                    <div class="grid grid-cols-2 gap-6">
                        <!-- Left column: basic info -->
                        <div class="space-y-4">
                            <div>
                                <label class="block text-xs font-medium text-gray-500 mb-1">Name *</label>
                                <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" placeholder="Sales Analyst" .value=${a.name || ''} @input=${(e: Event) => { this.editAgent = { ...this.editAgent, name: (e.target as HTMLInputElement).value }; }} />
                            </div>
                            <div>
                                <label class="block text-xs font-medium text-gray-500 mb-1">Description</label>
                                <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" placeholder="Analyzes sales data and generates reports" .value=${a.description || ''} @input=${(e: Event) => { this.editAgent = { ...this.editAgent, description: (e.target as HTMLInputElement).value }; }} />
                            </div>
                            <div>
                                <label class="block text-xs font-medium text-gray-500 mb-1">Model</label>
                                <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white" @change=${(e: Event) => {
                                    const idx = (e.target as HTMLSelectElement).selectedIndex;
                                    const opt = MODEL_OPTIONS[idx];
                                    if (opt) this.editAgent = { ...this.editAgent, model_provider: opt.provider, model_name: opt.name };
                                }}>
                                    ${MODEL_OPTIONS.map((m, i) => html`
                                    <option value="${m.name}" ?selected=${m.name === a.model_name}>${m.label}</option>`)}
                                </select>
                            </div>
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-xs font-medium text-gray-500 mb-1">Temperature</label>
                                    <input type="number" step="0.05" min="0" max="2" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" .value=${String(a.temperature ?? 0.1)} @input=${(e: Event) => { this.editAgent = { ...this.editAgent, temperature: parseFloat((e.target as HTMLInputElement).value) || 0.1 }; }} />
                                </div>
                                <div>
                                    <label class="block text-xs font-medium text-gray-500 mb-1">Max Tokens</label>
                                    <input type="number" step="256" min="256" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" .value=${String(a.max_tokens ?? 4096)} @input=${(e: Event) => { this.editAgent = { ...this.editAgent, max_tokens: parseInt((e.target as HTMLInputElement).value) || 4096 }; }} />
                                </div>
                            </div>
                            <div>
                                <label class="block text-xs font-medium text-gray-500 mb-1">Status</label>
                                <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white" .value=${a.status || 'draft'} @change=${(e: Event) => { this.editAgent = { ...this.editAgent, status: (e.target as HTMLSelectElement).value }; }}>
                                    <option value="draft">Draft</option>
                                    <option value="active">Active</option>
                                    <option value="archived">Archived</option>
                                </select>
                            </div>
                        </div>

                        <!-- Right column: system prompt -->
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">System Prompt</label>
                            <textarea class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono h-[calc(100%-24px)] resize-none" placeholder="You are a helpful data analyst agent..." .value=${a.system_prompt || ''} @input=${(e: Event) => { this.editAgent = { ...this.editAgent, system_prompt: (e.target as HTMLTextAreaElement).value }; }}></textarea>
                        </div>
                    </div>

                    <!-- Tool Picker -->
                    <div>
                        <div class="flex items-center justify-between mb-3">
                            <label class="text-xs font-medium text-gray-500">MCP Tools (${(a.tools || []).length} selected / ${MCP_TOOLS.length} total)</label>
                            <div class="flex gap-2">
                                <input type="text" class="px-2 py-1 text-xs border border-gray-200 rounded-md w-48" aria-label="Search MCP tools" placeholder="Search tools..." .value=${this.toolSearch} @input=${(e: Event) => { this.toolSearch = (e.target as HTMLInputElement).value; }} />
                                <select class="px-2 py-1 text-xs border border-gray-200 rounded-md bg-white" @change=${(e: Event) => { this.toolCategoryFilter = (e.target as HTMLSelectElement).value; }}>
                                    <option value="">All Categories</option>
                                    ${TOOL_CATEGORIES.map(c => html`<option value="${c}">${c}</option>`)}
                                </select>
                            </div>
                        </div>
                        <div class="border border-gray-200 rounded-lg max-h-56 overflow-y-auto divide-y divide-gray-50">
                            ${this.filteredTools.map(t => {
                                const checked = (a.tools || []).includes(t.name);
                                return html`
                                <label class="flex items-center gap-3 px-4 py-2 hover:bg-gray-50 cursor-pointer">
                                    <input type="checkbox" class="rounded border-gray-300" .checked=${checked} @change=${() => this.toggleTool(t.name)} />
                                    <div class="flex-1 min-w-0">
                                        <div class="flex items-center gap-2">
                                            <span class="text-xs font-mono font-semibold">${t.name}</span>
                                            <span class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-500">${t.category}</span>
                                        </div>
                                        <div class="text-xs text-gray-400 truncate">${t.description}</div>
                                    </div>
                                </label>`;
                            })}
                        </div>
                    </div>

                    <!-- Guardrails -->
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-2">Guardrails (JSON)</label>
                        <textarea class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono h-28 resize-none" .value=${JSON.stringify(a.guardrails || {}, null, 2)} @input=${(e: Event) => {
                            try {
                                const val = JSON.parse((e.target as HTMLTextAreaElement).value);
                                this.editAgent = { ...this.editAgent, guardrails: val };
                            } catch { /* ignore parse errors while typing */ }
                        }}></textarea>
                        <p class="text-[10px] text-gray-400 mt-1">max_queries_per_session, blocked_tables, max_sql_rows, blocked_tools, require_approval, cost_limit_usd</p>
                    </div>
                </div>

                <!-- Footer -->
                <div class="flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50">
                    <span class="text-xs text-gray-400">${this.saveResult}</span>
                    <div class="flex gap-2">
                        <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50" @click=${() => { this.showEditModal = false; }}>Cancel</button>
                        <button class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.saving ? 'opacity-50' : ''}" ?disabled=${this.saving} @click=${() => this.saveAgent()}>
                            ${this.saving ? 'Saving...' : a.id ? 'Update Agent' : 'Create Agent'}
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    /* ── Evaluation Modal ───────────────────────────────────────────────────── */

    private renderEvalModal() {
        return html`
        <div class="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Create evaluation"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') { this.showEvalModal = false; } }}>
            <div class="absolute inset-0 bg-black/30" @click=${() => { this.showEvalModal = false; }}></div>
            <div class="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl overflow-hidden" tabindex="-1">
                <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <h2 class="text-lg font-bold">Create Evaluation</h2>
                    <button class="text-gray-400 hover:text-ink text-xl" aria-label="Close dialog" @click=${() => { this.showEvalModal = false; }}>✕</button>
                </div>
                <div class="p-6 space-y-4">
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Agent</label>
                        <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white" .value=${this.evalAgentId} @change=${(e: Event) => { this.evalAgentId = (e.target as HTMLSelectElement).value; }}>
                            ${this.agents.map(a => html`<option value="${a.id}">${a.name}</option>`)}
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Evaluation Name</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" placeholder="smoke-test-v1" .value=${this.evalName} @input=${(e: Event) => { this.evalName = (e.target as HTMLInputElement).value; }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Test Cases (JSON array or one query per line)</label>
                        <textarea class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono h-40 resize-none" placeholder=${`[\n  {"input": "How many customers signed up last month?", "expected": "Should query customers table"},\n  {"input": "Show top 10 products by revenue", "expected": "Should query products with ORDER BY"}\n]`} .value=${this.evalTestCases} @input=${(e: Event) => { this.evalTestCases = (e.target as HTMLTextAreaElement).value; }}></textarea>
                    </div>
                </div>
                <div class="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 bg-gray-50">
                    <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50" @click=${() => { this.showEvalModal = false; }}>Cancel</button>
                    <button class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.creatingEval ? 'opacity-50' : ''}" ?disabled=${this.creatingEval} @click=${() => this.createEvaluation()}>
                        ${this.creatingEval ? 'Creating...' : 'Create Evaluation'}
                    </button>
                </div>
            </div>
        </div>`;
    }

    /* ── Detail Drawer ──────────────────────────────────────────────────────── */

    private renderDetailDrawer() {
        const a = this.selectedAgent!;
        return html`
        <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Agent detail: ${a.name}"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') { this.selectedAgent = null; } }}>
            <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedAgent = null; }}></div>
            <div class="relative w-[520px] bg-white h-full overflow-y-auto shadow-2xl border-l border-gray-200" tabindex="-1">
                <div class="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between z-10">
                    <div>
                        <h2 class="font-bold text-lg">${a.name}</h2>
                        <div class="flex items-center gap-2 mt-1">
                            ${this.statusBadge(a.status)}
                            <span class="text-xs text-gray-400 font-mono">${a.model_name}</span>
                        </div>
                    </div>
                    <button class="text-gray-400 hover:text-ink" aria-label="Close agent detail" @click=${() => { this.selectedAgent = null; }}>✕</button>
                </div>
                <div class="p-6 space-y-6">
                    ${a.description ? html`
                    <div>
                        <h4 class="text-xs font-semibold text-gray-500 uppercase mb-1">Description</h4>
                        <p class="text-sm text-gray-700">${a.description}</p>
                    </div>` : ''}

                    <div class="grid grid-cols-2 gap-4">
                        <div><span class="text-xs text-gray-400">Provider</span><div class="font-semibold text-sm">${a.model_provider}</div></div>
                        <div><span class="text-xs text-gray-400">Temperature</span><div class="font-semibold text-sm">${a.temperature}</div></div>
                        <div><span class="text-xs text-gray-400">Max Tokens</span><div class="font-semibold text-sm">${a.max_tokens?.toLocaleString()}</div></div>
                        <div><span class="text-xs text-gray-400">Created</span><div class="text-sm">${new Date(a.created_at).toLocaleString()}</div></div>
                    </div>

                    <div>
                        <h4 class="text-xs font-semibold text-gray-500 uppercase mb-2">System Prompt</h4>
                        <pre class="p-3 bg-gray-50 rounded-lg text-xs font-mono overflow-auto max-h-40 whitespace-pre-wrap">${a.system_prompt}</pre>
                    </div>

                    <div>
                        <h4 class="text-xs font-semibold text-gray-500 uppercase mb-2">Tools (${(a.tools || []).length})</h4>
                        <div class="flex flex-wrap gap-1.5">
                            ${(a.tools || []).map(t => html`
                            <span class="px-2 py-0.5 text-xs bg-blue-50 text-blue-700 rounded border border-blue-200 font-mono">${t}</span>`)}
                        </div>
                    </div>

                    ${a.guardrails && Object.keys(a.guardrails).length > 0 ? html`
                    <div>
                        <h4 class="text-xs font-semibold text-gray-500 uppercase mb-2">Guardrails</h4>
                        <pre class="p-3 bg-gray-50 rounded-lg text-xs font-mono overflow-auto max-h-32">${JSON.stringify(a.guardrails, null, 2)}</pre>
                    </div>` : ''}

                    ${a.evaluations && a.evaluations.length > 0 ? html`
                    <div>
                        <h4 class="text-xs font-semibold text-gray-500 uppercase mb-2">Evaluations (${a.evaluations.length})</h4>
                        <div class="space-y-2">
                            ${a.evaluations.map(e => html`
                            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                <div>
                                    <div class="text-sm font-semibold">${e.name}</div>
                                    <div class="text-xs text-gray-400">${e.run_count} runs</div>
                                </div>
                                <div class="flex items-center gap-3">
                                    ${this.scoreBar(e.overall_score)}
                                    ${this.statusBadge(e.status)}
                                </div>
                            </div>`)}
                        </div>
                    </div>` : ''}

                    <div class="flex gap-2 pt-4 border-t border-gray-100">
                        <button class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors" aria-label="Edit agent ${a.name}" @click=${() => { this.openEditModal(a); }}>Edit Agent</button>
                        <button class="px-4 py-2 text-sm font-semibold text-red-600 border border-red-200 rounded-lg hover:bg-red-50" aria-label="Delete agent ${a.name}" @click=${() => { this.deleteAgent(a.id); }}>Delete</button>
                    </div>
                </div>
            </div>
        </div>`;
    }
}
