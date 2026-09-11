import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-data-table';
import '../components/voyant-detail-panel';
import '../components/voyant-metric-card';
import '../components/voyant-browser-canvas';

// ── Interfaces ──────────────────────────────────────────────────────────────

interface Template {
    id: string;
    name: string;
    category: string;
    description: string;
    site_pattern: string;
    engine: string;
    language?: string;
    use_count: number;
    success_rate: number;
    selectors?: Record<string, unknown>;
    workflow?: WorkflowStep[];
    parameters?: TemplateParam[];
    output_fields?: string[];
}

interface TemplateParam {
    name: string;
    type: string;
    required?: boolean;
    description?: string;
    default?: string;
}

interface Category { category: string; count: number; }

interface AuditStep {
    step: number;
    action: string;
    status: string;
    duration_ms: number;
    details: Record<string, unknown>;
    error: string;
}

interface ScraperJob {
    job_id: string;
    status: string;
    urls: string[];
    pages_fetched: number;
    bytes_processed: number;
    artifact_count: number;
    error_message: string;
    created_at: string;
    started_at: string;
    finished_at: string;
}

interface WorkflowStep {
    id?: string;
    action: string;
    url?: string;
    selector?: string;
    text?: string;
    times?: number;
    wait_ms?: number;
    amount?: number;
    direction?: string;
    selectors?: Record<string, string>;
    label?: string;
}

interface DetectedElement {
    tag: string;
    selector: string;
    text: string;
    is_clickable: boolean;
    is_input: boolean;
}

// ── Component ───────────────────────────────────────────────────────────────

@customElement('view-scraper')
export class ViewScraper extends LitElement {
    // Tab state
    @state() tab: 'templates' | 'builder' | 'jobs' | 'results' = 'templates';

    // Templates tab
    @state() templates: Template[] = [];
    @state() categories: Category[] = [];
    @state() loading = true;
    @state() selectedTemplate: Template | null = null;
    @state() detailOpen = false;
    @state() activeCategory = 'all';
    @state() searchQuery = '';
    @state() searchLoading = false;

    // Run state
    @state() paramValues: Record<string, string> = {};
    @state() running = false;
    @state() runResult: Record<string, unknown> | null = null;
    @state() runError = '';
    @state() auditSteps: AuditStep[] = [];
    @state() auditFeed: string[] = [];
    @state() jobId = '';
    @state() pollTimer = 0;

    // Builder tab
    @state() builderSteps: WorkflowStep[] = [];
    @state() selectedStepIndex = -1;
    @state() browserUrl = '';
    @state() showBrowser = false;
    @state() builderName = 'My Workflow';
    @state() workflowJson = '';

    // Jobs tab
    @state() jobs: ScraperJob[] = [];
    @state() jobsLoading = false;
    @state() jobsFilter = '';

    // Results tab
    @state() selectedJobResults: Record<string, unknown> | null = null;
    @state() selectedJobId = '';
    @state() resultsLoading = false;

    private _searchDebounce = 0;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try {
            const [tplRes, catRes] = await Promise.all([
                api.get('/scraper/templates').catch(() => []),
                api.get('/scraper/templates/categories').catch(() => []),
            ]);
            this.templates = (tplRes as Template[]) || [];
            this.categories = (catRes as Category[]) || [];
        } catch { /* empty */ }
        finally { this.loading = false; }
    }

    disconnectedCallback() {
        if (this.pollTimer) clearInterval(this.pollTimer);
        super.disconnectedCallback();
    }

    // ── Template Helpers ────────────────────────────────────────────────────

    private _filteredTemplates() {
        let result = this.templates;
        if (this.activeCategory !== 'all') {
            result = result.filter(t => t.category === this.activeCategory);
        }
        if (this.searchQuery.trim()) {
            const q = this.searchQuery.toLowerCase();
            result = result.filter(t =>
                t.name.toLowerCase().includes(q) ||
                t.description.toLowerCase().includes(q) ||
                t.site_pattern.toLowerCase().includes(q)
            );
        }
        return result;
    }

    private _onSearch(e: Event) {
        const val = (e.target as HTMLInputElement).value;
        this.searchQuery = val;
        clearTimeout(this._searchDebounce);
        if (val.trim().length >= 2) {
            this._searchDebounce = window.setTimeout(async () => {
                this.searchLoading = true;
                try {
                    const res = await api.get(`/scraper/templates/search?q=${encodeURIComponent(val)}`);
                    if (Array.isArray(res) && res.length > 0) {
                        this.templates = res as Template[];
                    }
                } catch { /* ignore */ }
                finally { this.searchLoading = false; }
            }, 400);
        } else if (val.trim().length === 0) {
            // Reload all
            this._searchDebounce = window.setTimeout(async () => {
                try {
                    const res = await api.get('/scraper/templates');
                    this.templates = (res as Template[]) || [];
                } catch { /* ignore */ }
            }, 300);
        }
    }

    // ── Run Template ────────────────────────────────────────────────────────

    private async _runTemplate() {
        if (!this.selectedTemplate) return;
        this.running = true;
        this.runResult = null;
        this.runError = '';
        this.auditSteps = [];
        this.auditFeed = [];
        this.jobId = '';

        try {
            const res = await api.post(`/scraper/templates/${this.selectedTemplate.id}/run`, {
                parameters: this.paramValues,
            });
            this.runResult = res as Record<string, unknown>;
            this.jobId = String((res as Record<string, unknown>).job_id || '');
            if (this.jobId) {
                this._startPolling();
            }
        } catch (err: unknown) {
            this.runError = (err as Error).message || 'Run failed';
            this.running = false;
        }
    }

    private _startPolling() {
        let attempts = 0;
        this.pollTimer = window.setInterval(async () => {
            attempts++;
            try {
                const audit = await api.get(`/scraper/jobs/${this.jobId}/audit`).catch(() => null);
                if (audit && (audit as Record<string, unknown>).steps) {
                    this.auditSteps = (audit as Record<string, unknown>).steps as AuditStep[];
                }
                const live = await api.get(`/scraper/jobs/${this.jobId}/audit/live`).catch(() => null);
                if (live && (live as Record<string, unknown>).feed) {
                    this.auditFeed = (live as Record<string, unknown>).feed as string[];
                }
                if (this.runResult?.status === 'succeeded' || this.runResult?.status === 'failed' || attempts > 30) {
                    clearInterval(this.pollTimer);
                    this.running = false;
                    try {
                        const resultData = await api.get(`/scrape/status/${this.jobId}`);
                        this.runResult = { ...this.runResult, ...(resultData as Record<string, unknown>) };
                    } catch { /* ok */ }
                }
            } catch { /* polling ok to fail */ }
        }, 2000);
    }

    private _openTemplate(t: Template) {
        this.selectedTemplate = t;
        this.paramValues = {};
        this.runResult = null;
        this.runError = '';
        this.auditSteps = [];
        this.auditFeed = [];
        this.detailOpen = true;
    }

    // ── Builder Helpers ─────────────────────────────────────────────────────

    private _addStep(action: string) {
        const step: WorkflowStep = {
            id: `step-${Date.now()}`,
            action,
            url: '',
            selector: '',
            text: '',
            times: 3,
            wait_ms: 2000,
            amount: 500,
            direction: 'down',
            label: this._stepLabel(action),
        };
        this.builderSteps = [...this.builderSteps, step];
        this.selectedStepIndex = this.builderSteps.length - 1;
    }

    private _removeStep(index: number) {
        this.builderSteps = this.builderSteps.filter((_, i) => i !== index);
        if (this.selectedStepIndex >= this.builderSteps.length) {
            this.selectedStepIndex = this.builderSteps.length - 1;
        }
    }

    private _moveStep(index: number, direction: -1 | 1) {
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= this.builderSteps.length) return;
        const arr = [...this.builderSteps];
        [arr[index], arr[newIndex]] = [arr[newIndex], arr[index]];
        this.builderSteps = arr;
        this.selectedStepIndex = newIndex;
    }

    private _updateStep(index: number, field: string, value: unknown) {
        const arr = [...this.builderSteps];
        arr[index] = { ...arr[index], [field]: value };
        this.builderSteps = arr;
    }

    private _exportWorkflow() {
        const json = JSON.stringify({
            name: this.builderName,
            workflow: this.builderSteps.map(s => {
                const clean: Record<string, unknown> = { action: s.action };
                if (s.url) clean.url = s.url;
                if (s.selector) clean.selector = s.selector;
                if (s.text) clean.text = s.text;
                if (s.times !== undefined && s.action === 'scroll') clean.times = s.times;
                if (s.wait_ms !== undefined && s.action === 'wait') clean.wait_ms = s.wait_ms;
                if (s.amount !== undefined && s.action === 'scroll') clean.amount = s.amount;
                if (s.direction && s.action === 'scroll') clean.direction = s.direction;
                return clean;
            }),
        }, null, 2);
        this.workflowJson = json;
        // Copy to clipboard
        navigator.clipboard.writeText(json).catch(() => {});
    }

    private _importWorkflow() {
        try {
            const data = JSON.parse(this.workflowJson);
            if (data.name) this.builderName = data.name;
            if (Array.isArray(data.workflow)) {
                this.builderSteps = data.workflow.map((s: Record<string, unknown>, i: number) => ({
                    id: `step-${Date.now()}-${i}`,
                    action: String(s.action || 'navigate'),
                    url: String(s.url || ''),
                    selector: String(s.selector || ''),
                    text: String(s.text || ''),
                    times: Number(s.times || 3),
                    wait_ms: Number(s.wait_ms || 2000),
                    amount: Number(s.amount || 500),
                    direction: String(s.direction || 'down'),
                    label: this._stepLabel(String(s.action || 'navigate')),
                }));
            }
        } catch { /* invalid json */ }
    }

    private _loadFromTemplate(t: Template) {
        this.builderName = `${t.name} (copy)`;
        this.builderSteps = (t.workflow || []).map((s, i) => ({
            id: `step-${Date.now()}-${i}`,
            action: String(s.action || 'navigate'),
            url: String(s.url || ''),
            selector: String(s.selector || ''),
            text: String(s.text || ''),
            times: Number(s.times || 3),
            wait_ms: Number(s.wait_ms || 2000),
            amount: Number(s.amount || 500),
            direction: String(s.direction || 'down'),
            label: this._stepLabel(String(s.action || 'navigate')),
        }));
        this.tab = 'builder';
    }

    private _onBrowserElementClick(e: CustomEvent) {
        const el = e.detail as DetectedElement;
        if (this.selectedStepIndex >= 0 && this.selectedStepIndex < this.builderSteps.length) {
            const step = this.builderSteps[this.selectedStepIndex];
            if (step.action === 'click' || step.action === 'extract' || step.action === 'enter_text' || step.action === 'hover') {
                this._updateStep(this.selectedStepIndex, 'selector', el.selector);
            }
        }
    }

    // ── Jobs Helpers ────────────────────────────────────────────────────────

    private async _loadJobs() {
        this.jobsLoading = true;
        try {
            const url = this.jobsFilter
                ? `/scraper/jobs?status=${this.jobsFilter}`
                : '/scraper/jobs';
            const res = await api.get(url);
            this.jobs = (res as ScraperJob[]) || [];
        } catch { this.jobs = []; }
        finally { this.jobsLoading = false; }
    }

    private async _loadJobResults(jobId: string) {
        this.resultsLoading = true;
        this.selectedJobId = jobId;
        try {
            const res = await api.get(`/scraper/jobs/${jobId}/results`);
            this.selectedJobResults = res as Record<string, unknown>;
        } catch { this.selectedJobResults = null; }
        finally { this.resultsLoading = false; }
    }

    private _exportResults(format: 'json' | 'csv') {
        if (!this.selectedJobResults) return;
        const data = this.selectedJobResults;
        let blob: Blob;
        let filename: string;

        if (format === 'json') {
            blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            filename = `scraper-results-${this.selectedJobId.slice(0, 8)}.json`;
        } else {
            // CSV: flatten results into rows
            const results = (data as Record<string, unknown>).results as Record<string, unknown> || {};
            const rows: string[][] = [['field', 'value']];
            for (const [key, val] of Object.entries(results)) {
                rows.push([key, typeof val === 'object' ? JSON.stringify(val) : String(val ?? '')]);
            }
            const csv = rows.map(r => r.map(c => `"${c.replace(/"/g, '""')}"`).join(',')).join('\n');
            blob = new Blob([csv], { type: 'text/csv' });
            filename = `scraper-results-${this.selectedJobId.slice(0, 8)}.csv`;
        }

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    // ── Render Helpers ──────────────────────────────────────────────────────

    private _statusColor(status: string): string {
        if (status === 'succeeded') return '#22C55E';
        if (status === 'failed') return '#EF4444';
        if (status === 'running') return '#3B82F6';
        if (status === 'queued') return '#F59E0B';
        return '#9CA3AF';
    }

    private _actionIcon(action: string): string {
        const icons: Record<string, string> = {
            navigate: '🌐', fetch: '🌐', scroll: '📜', click: '🖱️',
            wait: '⏳', extract: '📊', enter_text: '⌨️', hover: '👆',
            capture_html: '📄', close_popup: '❌', paginate: '📄',
            login: '🔐', screenshot: '📸', condition: '🔀', loop: '🔄',
        };
        return icons[action] || '⚡';
    }

    private _stepLabel(action: string): string {
        const labels: Record<string, string> = {
            navigate: 'Navigate', click: 'Click', scroll: 'Scroll',
            wait: 'Wait', extract: 'Extract', enter_text: 'Enter Text',
            hover: 'Hover', paginate: 'Paginate', login: 'Login',
            screenshot: 'Screenshot', condition: 'Condition', loop: 'Loop',
        };
        return labels[action] || action;
    }

    private _formatBytes(bytes: number): string {
        if (!bytes) return '0 B';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    private _formatDate(iso: string): string {
        if (!iso) return '—';
        try {
            return new Date(iso).toLocaleString();
        } catch { return iso; }
    }

    // ── Tab switch with data loading ────────────────────────────────────────

    private _switchTab(t: 'templates' | 'builder' | 'jobs' | 'results') {
        this.tab = t;
        if (t === 'jobs' && this.jobs.length === 0) {
            this._loadJobs();
        }
    }

    // ── Render ──────────────────────────────────────────────────────────────

    render() {
        return html`
        <saas-sidebar currentPath="/admin/scraper"></saas-sidebar>
        <main class="ml-60 min-h-screen" style="background:var(--saas-bg-page)">
            <!-- Header -->
            <div style="padding:32px 32px 0;display:flex;align-items:center;justify-content:space-between">
                <div>
                    <h1 style="font-size:28px;font-weight:900;font-family:Geist,Inter,sans-serif;letter-spacing:-0.02em">Scraper Engine</h1>
                    <p style="font-size:13px;color:var(--saas-text-secondary);margin-top:4px">Visual web extraction · ${this.templates.length} templates · ${this.categories.length} categories · Agent-native MCP</p>
                </div>
                <div class="voyant-tabs" role="tablist" aria-label="Scraper sections">
                    <button class="voyant-tab ${this.tab === 'templates' ? 'active' : ''}" role="tab" aria-selected=${this.tab === 'templates'} @click=${() => this._switchTab('templates')}>📋 Templates</button>
                    <button class="voyant-tab ${this.tab === 'builder' ? 'active' : ''}" role="tab" aria-selected=${this.tab === 'builder'} @click=${() => this._switchTab('builder')}>🔧 Builder</button>
                    <button class="voyant-tab ${this.tab === 'jobs' ? 'active' : ''}" role="tab" aria-selected=${this.tab === 'jobs'} @click=${() => this._switchTab('jobs')}>⚡ Jobs</button>
                    <button class="voyant-tab ${this.tab === 'results' ? 'active' : ''}" role="tab" aria-selected=${this.tab === 'results'} @click=${() => this._switchTab('results')}>📊 Results</button>
                </div>
            </div>

            <!-- Stats -->
            <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px;padding:24px 32px">
                <voyant-metric-card label="Templates" value="${this.templates.length}" icon="📋" color="#FF4D00"></voyant-metric-card>
                <voyant-metric-card label="Categories" value="${this.categories.length}" icon="📂" color="#3B82F6"></voyant-metric-card>
                <voyant-metric-card label="Octopus Arms" value="9" icon="🐙" color="#8B5CF6"></voyant-metric-card>
                <voyant-metric-card label="MCP Tools" value="8" icon="🔧" color="#22C55E" trend="Agent-accessible" trendDirection="up"></voyant-metric-card>
                <voyant-metric-card label="Playwright" value="Live" icon="🎭" color="#06B6D4" trend="JS rendering" trendDirection="up"></voyant-metric-card>
            </div>

            ${this.loading ? html`<div style="text-align:center;padding:80px;color:var(--saas-text-muted)" role="status" aria-live="polite">Loading...</div>` : html`

            <!-- ═══════════ TEMPLATES ═══════════ -->
            ${this.tab === 'templates' ? this._renderTemplatesTab() : ''}

            <!-- ═══════════ BUILDER ═══════════ -->
            ${this.tab === 'builder' ? this._renderBuilderTab() : ''}

            <!-- ═══════════ JOBS ═══════════ -->
            ${this.tab === 'jobs' ? this._renderJobsTab() : ''}

            <!-- ═══════════ RESULTS ═══════════ -->
            ${this.tab === 'results' ? this._renderResultsTab() : ''}

            `}

            <!-- ═══════════ DETAIL PANEL ═══════════ -->
            ${this._renderDetailPanel()}
        </main>`;
    }

    // ── Templates Tab ───────────────────────────────────────────────────────

    private _renderTemplatesTab() {
        return html`
        <div style="padding:0 32px 32px">
            <!-- Search + Category pills -->
            <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px">
                <div style="position:relative;flex:1;max-width:400px" role="search" aria-label="Search scraper templates">
                    <input class="voyant-input" style="font-size:13px;padding-left:36px;width:100%"
                        placeholder="Search templates..."
                        aria-label="Search templates"
                        .value=${this.searchQuery}
                        @input=${(e: Event) => this._onSearch(e)}>
                    <span style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--saas-text-muted);font-size:14px">🔍</span>
                    ${this.searchLoading ? html`<span style="position:absolute;right:12px;top:50%;transform:translateY(-50%);font-size:12px;color:var(--saas-text-muted)">...</span>` : ''}
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;flex:1">
                    <button style="padding:6px 16px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid ${this.activeCategory === 'all' ? '#FF4D00' : '#E5E7EB'};background:${this.activeCategory === 'all' ? '#FF4D00' : 'white'};color:${this.activeCategory === 'all' ? 'white' : '#6B7280'};transition:all 120ms"
                        @click=${() => { this.activeCategory = 'all'; }}>All (${this.templates.length})</button>
                    ${this.categories.map(c => html`
                    <button style="padding:6px 16px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid ${this.activeCategory === c.category ? '#FF4D00' : '#E5E7EB'};background:${this.activeCategory === c.category ? '#FF4D00' : 'white'};color:${this.activeCategory === c.category ? 'white' : '#6B7280'};transition:all 120ms"
                        @click=${() => { this.activeCategory = c.category; }}>
                        ${c.category} (${c.count})
                    </button>`)}
                </div>
            </div>

            <!-- Template grid -->
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px">
                ${this._filteredTemplates().map(t => html`
                <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px;cursor:pointer;transition:all 200ms"
                    role="button"
                    tabindex="0"
                    aria-label="Scraper template: ${t.name}"
                    @mouseenter=${(e: Event) => { const el = e.currentTarget as HTMLElement; el.style.borderColor = '#FF4D00'; el.style.boxShadow = '0 4px 12px rgba(255,77,0,0.1)'; el.style.transform = 'translateY(-2px)'; }}
                    @mouseleave=${(e: Event) => { const el = e.currentTarget as HTMLElement; el.style.borderColor = 'var(--saas-border)'; el.style.boxShadow = ''; el.style.transform = ''; }}
                    @click=${() => this._openTemplate(t)}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this._openTemplate(t); } }}>
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
                        <div style="width:40px;height:40px;border-radius:10px;background:rgba(255,77,0,0.08);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">🕷️</div>
                        <div style="flex:1;min-width:0">
                            <div style="font-size:14px;font-weight:700;color:var(--saas-text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${t.name}</div>
                            <div style="font-size:11px;color:var(--saas-text-muted)">${t.site_pattern}</div>
                        </div>
                        <span style="padding:3px 10px;border-radius:12px;font-size:10px;font-weight:600;background:${t.engine === 'playwright' ? 'rgba(59,130,246,0.1)' : 'rgba(34,197,94,0.1)'};color:${t.engine === 'playwright' ? '#3B82F6' : '#22C55E'}">${t.engine || 'playwright'}</span>
                    </div>
                    <p style="font-size:12px;color:var(--saas-text-secondary);margin-bottom:14px;min-height:32px;line-height:1.5">${t.description || 'No description'}</p>
                    <div style="display:flex;align-items:center;gap:12px;font-size:11px;color:var(--saas-text-muted)">
                        <span style="padding:2px 8px;border-radius:6px;background:var(--saas-bg-hover)">${t.category}</span>
                        <span>${t.output_fields?.length || 0} fields</span>
                        <span>${t.use_count || 0} runs</span>
                    </div>
                    <div style="display:flex;gap:6px;margin-top:12px">
                        <button class="voyant-btn" style="flex:1;font-size:11px;padding:6px 0;justify-content:center;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                            @click=${(e: Event) => { e.stopPropagation(); this._openTemplate(t); }}>
                            ▶ Run
                        </button>
                        <button class="voyant-btn" style="font-size:11px;padding:6px 10px;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                            @click=${(e: Event) => { e.stopPropagation(); this._loadFromTemplate(t); }}
                            title="Load into Builder">
                            🔧
                        </button>
                    </div>
                </div>`)}
            </div>

            ${this._filteredTemplates().length === 0 ? html`
            <div style="text-align:center;padding:60px;opacity:0.4">
                <div style="font-size:40px;margin-bottom:12px">🔍</div>
                <div style="font-size:13px">No templates match your search</div>
            </div>` : ''}
        </div>`;
    }

    // ── Builder Tab ─────────────────────────────────────────────────────────

    private _renderBuilderTab() {
        return html`
        <div style="padding:0 32px 32px">
            <!-- Builder Header -->
            <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px">
                <input class="voyant-input" style="font-size:14px;font-weight:700;width:300px"
                    placeholder="Workflow name..."
                    .value=${this.builderName}
                    @input=${(e: Event) => { this.builderName = (e.target as HTMLInputElement).value; }}>
                <div style="flex:1"></div>
                <button class="voyant-btn" style="font-size:12px;padding:8px 16px;border:1px solid var(--saas-border);border-radius:8px;background:white;cursor:pointer"
                    @click=${() => { this.workflowJson = JSON.stringify({ name: this.builderName, workflow: this.builderSteps }, null, 2); }}>📋 Export JSON</button>
                <label class="voyant-btn" style="font-size:12px;padding:8px 16px;border:1px solid var(--saas-border);border-radius:8px;background:white;cursor:pointer">
                    📥 Import JSON
                    <input type="file" accept=".json" style="display:none" @change=${(e: Event) => {
                        const file = (e.target as HTMLInputElement).files?.[0];
                        if (file) {
                            const reader = new FileReader();
                            reader.onload = () => {
                                this.workflowJson = String(reader.result || '');
                                this._importWorkflow();
                            };
                            reader.readAsText(file);
                        }
                    }}>
                </label>
            </div>

            <div style="display:grid;grid-template-columns:220px 1fr 280px;gap:16px">
                <!-- Step Palette -->
                <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:16px">
                    <h3 style="font-size:11px;font-weight:700;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Workflow Steps</h3>
                    ${['navigate', 'click', 'scroll', 'wait', 'extract', 'enter_text', 'hover', 'paginate', 'login', 'screenshot', 'condition', 'loop'].map(action => html`
                    <div style="padding:8px 12px;border-radius:8px;font-size:12px;cursor:grab;margin-bottom:4px;transition:all 120ms;color:var(--saas-text-secondary);display:flex;align-items:center;gap:8px"
                        role="button"
                        tabindex="0"
                        aria-label="Add ${this._stepLabel(action)} step"
                        @click=${() => this._addStep(action)}
                        @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this._addStep(action); } }}
                        @mouseenter=${(e: Event) => { const el = e.currentTarget as HTMLElement; el.style.background = 'rgba(255,77,0,0.08)'; el.style.color = '#FF4D00'; }}
                        @mouseleave=${(e: Event) => { const el = e.currentTarget as HTMLElement; el.style.background = ''; el.style.color = 'var(--saas-text-secondary)'; }}>
                        <span style="font-size:14px">${this._actionIcon(action)}</span> ${this._stepLabel(action)}
                    </div>`)}
                </div>

                <!-- Canvas + Steps -->
                <div style="display:flex;flex-direction:column;gap:16px">
                    <!-- Browser Canvas -->
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;overflow:hidden">
                        <div style="display:flex;align-items:center;gap:8px;padding:8px 12px;border-bottom:1px solid var(--saas-border)">
                            <span style="font-size:12px;font-weight:600;color:var(--saas-text-primary)">Browser Preview</span>
                            <div style="flex:1"></div>
                            <input class="voyant-input" style="font-size:11px;flex:1;max-width:300px"
                                placeholder="Enter URL to preview..."
                                .value=${this.browserUrl}
                                @keydown=${(e: KeyboardEvent) => {
                                    if (e.key === 'Enter') {
                                        this.showBrowser = true;
                                        const canvas = this.renderRoot.querySelector('voyant-browser-canvas') as any;
                                        if (canvas) canvas.navigateTo(this.browserUrl);
                                    }
                                }}
                                @input=${(e: Event) => { this.browserUrl = (e.target as HTMLInputElement).value; }}>
                            <button style="padding:4px 12px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid #FF4D00;background:#FF4D00;color:white"
                                @click=${() => {
                                    this.showBrowser = true;
                                    setTimeout(() => {
                                        const canvas = this.renderRoot.querySelector('voyant-browser-canvas') as any;
                                        if (canvas && this.browserUrl) canvas.navigateTo(this.browserUrl);
                                    }, 100);
                                }}>Load</button>
                        </div>
                        <div style="height:400px;position:relative">
                            ${this.showBrowser ? html`
                            <voyant-browser-canvas
                                mode="select"
                                .url=${this.browserUrl}
                                @element-click=${(e: CustomEvent) => this._onBrowserElementClick(e)}
                                style="height:100%"></voyant-browser-canvas>
                            ` : html`
                            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:12px;opacity:0.3">
                                <div style="font-size:40px">🌐</div>
                                <div style="font-size:13px">Enter a URL above to load the browser preview</div>
                                <div style="display:flex;gap:8px">
                                    <button style="padding:6px 14px;border-radius:8px;border:1px solid #E5E7EB;background:white;font-size:11px;cursor:pointer"
                                        @click=${() => { this.browserUrl = 'https://news.ycombinator.com'; this.showBrowser = true; setTimeout(() => {
                                            const canvas = this.renderRoot.querySelector('voyant-browser-canvas') as any;
                                            if (canvas) canvas.navigateTo(this.browserUrl);
                                        }, 100); }}>Hacker News</button>
                                    <button style="padding:6px 14px;border-radius:8px;border:1px solid #E5E7EB;background:white;font-size:11px;cursor:pointer"
                                        @click=${() => { this.browserUrl = 'https://example.com'; this.showBrowser = true; setTimeout(() => {
                                            const canvas = this.renderRoot.querySelector('voyant-browser-canvas') as any;
                                            if (canvas) canvas.navigateTo(this.browserUrl);
                                        }, 100); }}>Example</button>
                                </div>
                            </div>`}
                        </div>
                    </div>

                    <!-- Step List -->
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:16px">
                        <h3 style="font-size:11px;font-weight:700;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">
                            Steps (${this.builderSteps.length})
                        </h3>
                        ${this.builderSteps.length === 0 ? html`
                        <div style="text-align:center;padding:24px;opacity:0.4;font-size:12px">
                            Click steps from the palette to add them
                        </div>` : html`
                        <div style="display:flex;flex-direction:column;gap:4px">
                            ${this.builderSteps.map((step, i) => html`
                            <div style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;font-size:12px;cursor:pointer;transition:all 120ms;background:${this.selectedStepIndex === i ? 'rgba(255,77,0,0.08)' : 'var(--saas-bg-hover)'};border:1px solid ${this.selectedStepIndex === i ? '#FF4D00' : 'transparent'}"
                                @click=${() => { this.selectedStepIndex = i; }}>
                                <span style="font-size:10px;color:var(--saas-text-muted);width:20px">${i + 1}</span>
                                <span style="font-size:14px">${this._actionIcon(step.action)}</span>
                                <span style="font-weight:600;flex:1">${this._stepLabel(step.action)}</span>
                                ${step.selector ? html`<span style="font-size:10px;color:var(--saas-text-muted);font-family:JetBrains Mono,monospace;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${step.selector}</span>` : ''}
                                <button style="background:none;border:none;cursor:pointer;font-size:10px;opacity:0.5;padding:2px" title="Move up"
                                    aria-label="Move step ${i + 1} up"
                                    @click=${(e: Event) => { e.stopPropagation(); this._moveStep(i, -1); }}>▲</button>
                                <button style="background:none;border:none;cursor:pointer;font-size:10px;opacity:0.5;padding:2px" title="Move down"
                                    aria-label="Move step ${i + 1} down"
                                    @click=${(e: Event) => { e.stopPropagation(); this._moveStep(i, 1); }}>▼</button>
                                <button style="background:none;border:none;cursor:pointer;font-size:12px;color:#EF4444;opacity:0.5;padding:2px" title="Remove"
                                    aria-label="Remove step ${i + 1}"
                                    @click=${(e: Event) => { e.stopPropagation(); this._removeStep(i); }}>✕</button>
                            </div>`)}
                        </div>`}
                    </div>
                </div>

                <!-- Config Panel -->
                <div style="display:flex;flex-direction:column;gap:16px">
                    ${this.selectedStepIndex >= 0 && this.selectedStepIndex < this.builderSteps.length
                        ? this._renderStepConfig()
                        : html`
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:16px">
                        <h3 style="font-size:13px;font-weight:700;margin-bottom:8px">Step Config</h3>
                        <div style="text-align:center;padding:24px;opacity:0.4;font-size:12px">Select a step to configure</div>
                    </div>`}

                    <!-- Output Settings -->
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:16px">
                        <h3 style="font-size:13px;font-weight:700;margin-bottom:8px">Output</h3>
                        <select class="voyant-input" style="font-size:12px"><option>JSON</option><option>CSV</option><option>XLSX</option><option>Parquet</option><option>Database</option></select>
                    </div>
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:16px">
                        <h3 style="font-size:13px;font-weight:700;margin-bottom:8px">Schedule</h3>
                        <select class="voyant-input" style="font-size:12px"><option>Once</option><option>Hourly</option><option>Daily</option><option>Weekly</option><option>Cron</option></select>
                    </div>
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:16px">
                        <h3 style="font-size:13px;font-weight:700;margin-bottom:8px">Anti-Bot</h3>
                        <div style="display:flex;flex-direction:column;gap:6px;font-size:12px">
                            <label style="display:flex;align-items:center;gap:6px;cursor:pointer"><input type="checkbox" checked style="accent-color:#FF4D00"> Playwright (JS)</label>
                            <label style="display:flex;align-items:center;gap:6px;cursor:pointer"><input type="checkbox" style="accent-color:#FF4D00"> Evasion mode</label>
                            <label style="display:flex;align-items:center;gap:6px;cursor:pointer"><input type="checkbox" checked style="accent-color:#FF4D00"> Block resources</label>
                        </div>
                    </div>
                    <button class="voyant-btn-primary voyant-btn" style="width:100%;justify-content:center"
                        ?disabled=${this.builderSteps.length === 0}
                        @click=${() => {
                            this._exportWorkflow();
                            this.tab = 'results';
                        }}>▶ Run Workflow</button>
                </div>
            </div>

            <!-- JSON Modal -->
            ${this.workflowJson && this.tab === 'builder' ? html`
            <div style="margin-top:16px;background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:16px">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                    <h3 style="font-size:13px;font-weight:700">Workflow JSON</h3>
                    <button style="background:none;border:none;cursor:pointer;font-size:14px" @click=${() => { this.workflowJson = ''; }}>✕</button>
                </div>
                <textarea style="width:100%;height:200px;font-family:JetBrains Mono,monospace;font-size:12px;padding:12px;border:1px solid var(--saas-border);border-radius:8px;resize:vertical;background:var(--saas-bg-hover);color:var(--saas-text-primary)"
                    .value=${this.workflowJson}
                    @input=${(e: Event) => { this.workflowJson = (e.target as HTMLTextAreaElement).value; }}></textarea>
                <div style="display:flex;gap:8px;margin-top:8px">
                    <button class="voyant-btn" style="font-size:12px;padding:6px 16px;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                        @click=${() => this._importWorkflow()}>Apply Import</button>
                    <button class="voyant-btn" style="font-size:12px;padding:6px 16px;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                        @click=${() => { navigator.clipboard.writeText(this.workflowJson).catch(() => {}); }}>Copy to Clipboard</button>
                </div>
            </div>` : ''}
        </div>`;
    }

    private _renderStepConfig() {
        const step = this.builderSteps[this.selectedStepIndex];
        if (!step) return html``;

        return html`
        <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:16px">
            <h3 style="font-size:13px;font-weight:700;margin-bottom:12px">
                ${this._actionIcon(step.action)} ${this._stepLabel(step.action)} Config
            </h3>
            <div style="display:flex;flex-direction:column;gap:10px">
                ${step.action === 'navigate' || step.action === 'login' ? html`
                <div>
                    <label style="font-size:11px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:4px">URL</label>
                    <input class="voyant-input" style="font-size:12px;font-family:JetBrains Mono,monospace" placeholder="https://..."
                        .value=${step.url || ''}
                        @input=${(e: Event) => this._updateStep(this.selectedStepIndex, 'url', (e.target as HTMLInputElement).value)}>
                </div>` : ''}

                ${step.action === 'click' || step.action === 'hover' || step.action === 'extract' || step.action === 'enter_text' || step.action === 'paginate' ? html`
                <div>
                    <label style="font-size:11px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:4px">CSS Selector</label>
                    <input class="voyant-input" style="font-size:12px;font-family:JetBrains Mono,monospace" placeholder=".class, #id, [attr]"
                        .value=${step.selector || ''}
                        @input=${(e: Event) => this._updateStep(this.selectedStepIndex, 'selector', (e.target as HTMLInputElement).value)}>
                    <div style="font-size:10px;color:var(--saas-text-muted);margin-top:2px">Click an element in the browser to auto-fill</div>
                </div>` : ''}

                ${step.action === 'enter_text' ? html`
                <div>
                    <label style="font-size:11px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:4px">Text to Enter</label>
                    <input class="voyant-input" style="font-size:12px" placeholder="Text..."
                        .value=${step.text || ''}
                        @input=${(e: Event) => this._updateStep(this.selectedStepIndex, 'text', (e.target as HTMLInputElement).value)}>
                </div>` : ''}

                ${step.action === 'scroll' ? html`
                <div>
                    <label style="font-size:11px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:4px">Scroll Times</label>
                    <input class="voyant-input" style="font-size:12px" type="number" min="1" max="50"
                        .value=${String(step.times || 3)}
                        @input=${(e: Event) => this._updateStep(this.selectedStepIndex, 'times', Number((e.target as HTMLInputElement).value))}>
                </div>
                <div>
                    <label style="font-size:11px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:4px">Direction</label>
                    <select class="voyant-input" style="font-size:12px"
                        .value=${step.direction || 'down'}
                        @change=${(e: Event) => this._updateStep(this.selectedStepIndex, 'direction', (e.target as HTMLSelectElement).value)}>
                        <option value="down">Down</option>
                        <option value="up">Up</option>
                    </select>
                </div>` : ''}

                ${step.action === 'wait' ? html`
                <div>
                    <label style="font-size:11px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:4px">Wait (ms)</label>
                    <input class="voyant-input" style="font-size:12px" type="number" min="100" max="30000" step="100"
                        .value=${String(step.wait_ms || 2000)}
                        @input=${(e: Event) => this._updateStep(this.selectedStepIndex, 'wait_ms', Number((e.target as HTMLInputElement).value))}>
                </div>` : ''}

                ${step.action === 'wait' || step.action === 'click' ? html`
                <div>
                    <label style="font-size:11px;font-weight:600;color:var(--saas-text-muted);display:block;margin-bottom:4px">Wait For Selector (optional)</label>
                    <input class="voyant-input" style="font-size:12px;font-family:JetBrains Mono,monospace" placeholder=".element-loaded"
                        .value=${step.selector || ''}
                        @input=${(e: Event) => this._updateStep(this.selectedStepIndex, 'selector', (e.target as HTMLInputElement).value)}>
                </div>` : ''}
            </div>
        </div>`;
    }

    // ── Jobs Tab ────────────────────────────────────────────────────────────

    private _renderJobsTab() {
        return html`
        <div style="padding:0 32px 32px">
            <!-- Toolbar -->
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
                <select class="voyant-input" style="font-size:12px;width:160px"
                    .value=${this.jobsFilter}
                    @change=${(e: Event) => { this.jobsFilter = (e.target as HTMLSelectElement).value; this._loadJobs(); }}>
                    <option value="">All statuses</option>
                    <option value="queued">Queued</option>
                    <option value="running">Running</option>
                    <option value="succeeded">Succeeded</option>
                    <option value="failed">Failed</option>
                </select>
                <div style="flex:1"></div>
                <button class="voyant-btn" style="font-size:12px;padding:6px 16px;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                    @click=${() => this._loadJobs()}>🔄 Refresh</button>
            </div>

            ${this.jobsLoading ? html`<div style="text-align:center;padding:40px;color:var(--saas-text-muted)" role="status" aria-live="polite">Loading jobs...</div>` : html`
            ${this.jobs.length === 0 ? html`
            <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:24px">
                <div style="text-align:center;padding:60px;opacity:0.4">
                    <div style="font-size:40px;margin-bottom:12px">⚡</div>
                    <div style="font-size:13px">No scraping jobs yet. Run a template to see jobs here.</div>
                </div>
            </div>` : html`
            <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;overflow:hidden" aria-live="polite">
                <table style="width:100%;border-collapse:collapse;font-size:12px" role="table" aria-label="Scraper jobs">
                    <thead>
                        <tr style="border-bottom:1px solid var(--saas-border)">
                            <th style="text-align:left;padding:12px 16px;font-weight:600;color:var(--saas-text-muted);font-size:11px;text-transform:uppercase">Job ID</th>
                            <th style="text-align:left;padding:12px 16px;font-weight:600;color:var(--saas-text-muted);font-size:11px;text-transform:uppercase">Status</th>
                            <th style="text-align:left;padding:12px 16px;font-weight:600;color:var(--saas-text-muted);font-size:11px;text-transform:uppercase">URL</th>
                            <th style="text-align:right;padding:12px 16px;font-weight:600;color:var(--saas-text-muted);font-size:11px;text-transform:uppercase">Pages</th>
                            <th style="text-align:right;padding:12px 16px;font-weight:600;color:var(--saas-text-muted);font-size:11px;text-transform:uppercase">Size</th>
                            <th style="text-align:left;padding:12px 16px;font-weight:600;color:var(--saas-text-muted);font-size:11px;text-transform:uppercase">Created</th>
                            <th style="text-align:center;padding:12px 16px;font-weight:600;color:var(--saas-text-muted);font-size:11px;text-transform:uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.jobs.map(j => html`
                        <tr style="border-bottom:1px solid var(--saas-border);cursor:pointer;transition:background 120ms"
                            @mouseenter=${(e: Event) => { (e.currentTarget as HTMLElement).style.background = 'var(--saas-bg-hover)'; }}
                            @mouseleave=${(e: Event) => { (e.currentTarget as HTMLElement).style.background = ''; }}>
                            <td style="padding:12px 16px">
                                <span style="font-family:JetBrains Mono,monospace;font-size:11px">${j.job_id.slice(0, 8)}</span>
                            </td>
                            <td style="padding:12px 16px">
                                <span style="display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:12px;font-size:10px;font-weight:600;background:${this._statusColor(j.status)}20;color:${this._statusColor(j.status)}">
                                    <span style="width:6px;height:6px;border-radius:50%;background:${this._statusColor(j.status)}"></span>
                                    ${j.status}
                                </span>
                            </td>
                            <td style="padding:12px 16px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--saas-text-secondary)">
                                ${j.urls?.[0] || '—'}
                            </td>
                            <td style="padding:12px 16px;text-align:right;font-weight:600">${j.pages_fetched || 0}</td>
                            <td style="padding:12px 16px;text-align:right">${this._formatBytes(j.bytes_processed || 0)}</td>
                            <td style="padding:12px 16px;color:var(--saas-text-muted)">${this._formatDate(j.created_at)}</td>
                            <td style="padding:12px 16px;text-align:center">
                                <button style="font-size:11px;padding:4px 10px;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                                    @click=${(e: Event) => { e.stopPropagation(); this._loadJobResults(j.job_id); this.tab = 'results'; }}>
                                    📊 Results
                                </button>
                            </td>
                        </tr>`)}
                    </tbody>
                </table>
            </div>`}`}
        </div>`;
    }

    // ── Results Tab ─────────────────────────────────────────────────────────

    private _renderResultsTab() {
        return html`
        <div style="padding:0 32px 32px">
            ${!this.selectedJobResults ? html`
            <!-- No results selected -->
            <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:24px">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
                    <h3 style="font-size:14px;font-weight:700">Select a Job</h3>
                    <select class="voyant-input" style="font-size:12px;flex:1"
                        @change=${(e: Event) => {
                            const jobId = (e.target as HTMLSelectElement).value;
                            if (jobId) this._loadJobResults(jobId);
                        }}>
                        <option value="">Choose a job to view results...</option>
                        ${this.jobs.map(j => html`
                        <option value="${j.job_id}">${j.job_id.slice(0, 8)} — ${j.status} — ${j.urls?.[0] || 'no url'}</option>`)}
                    </select>
                    <button class="voyant-btn" style="font-size:12px;padding:6px 16px;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                        @click=${() => this._loadJobs()}>🔄 Load Jobs</button>
                </div>
                <div style="text-align:center;padding:40px;opacity:0.4">
                    <div style="font-size:40px;margin-bottom:12px">📊</div>
                    <div style="font-size:13px">Select a job above or run a template to see extracted data here</div>
                </div>
            </div>` : html`
            <!-- Results display -->
            <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:24px">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
                    <h3 style="font-size:14px;font-weight:700">Extracted Data</h3>
                    <span style="font-family:JetBrains Mono,monospace;font-size:11px;color:var(--saas-text-muted)">Job: ${this.selectedJobId.slice(0, 8)}</span>
                    <div style="flex:1"></div>
                    <select class="voyant-input" style="font-size:12px"
                        @change=${(e: Event) => {
                            const jobId = (e.target as HTMLSelectElement).value;
                            if (jobId) this._loadJobResults(jobId);
                        }}>
                        <option value="">Switch job...</option>
                        ${this.jobs.map(j => html`
                        <option value="${j.job_id}" .selected=${j.job_id === this.selectedJobId}>${j.job_id.slice(0, 8)} — ${j.status}</option>`)}
                    </select>
                </div>

                <!-- Summary -->
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:20px">
                    <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover);text-align:center">
                        <div style="font-size:16px;font-weight:800">${String((this.selectedJobResults as Record<string, unknown>).status || '—')}</div>
                        <div style="font-size:10px;color:var(--saas-text-muted)">Status</div>
                    </div>
                    <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover);text-align:center">
                        <div style="font-size:16px;font-weight:800">${String((this.selectedJobResults as Record<string, unknown>).pages_fetched || 0)}</div>
                        <div style="font-size:10px;color:var(--saas-text-muted)">Pages</div>
                    </div>
                    <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover);text-align:center">
                        <div style="font-size:16px;font-weight:800">${this._formatBytes(Number((this.selectedJobResults as Record<string, unknown>).bytes_processed || 0))}</div>
                        <div style="font-size:10px;color:var(--saas-text-muted)">Size</div>
                    </div>
                    <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover);text-align:center">
                        <div style="font-size:16px;font-weight:800">${((this.selectedJobResults as Record<string, unknown>).artifacts as unknown[])?.length || 0}</div>
                        <div style="font-size:10px;color:var(--saas-text-muted)">Artifacts</div>
                    </div>
                </div>

                <!-- Export buttons -->
                <div style="display:flex;gap:8px;margin-bottom:16px">
                    <button class="voyant-btn" style="font-size:11px;padding:6px 14px;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                        @click=${() => this._exportResults('json')}>📄 Export JSON</button>
                    <button class="voyant-btn" style="font-size:11px;padding:6px 14px;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                        @click=${() => this._exportResults('csv')}>📊 Export CSV</button>
                    <button class="voyant-btn" style="font-size:11px;padding:6px 14px;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                        @click=${() => {
                            // XLSX export via CSV (basic)
                            this._exportResults('csv');
                        }}>📗 Export XLSX</button>
                </div>

                <!-- Results Data Table -->
                ${this._renderResultsData()}

                <!-- Artifacts -->
                ${((this.selectedJobResults as Record<string, unknown>).artifacts as unknown[])?.length ? html`
                <div style="margin-top:16px">
                    <h4 style="font-size:11px;font-weight:700;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Artifacts</h4>
                    <div style="display:flex;flex-direction:column;gap:4px">
                        ${((this.selectedJobResults as Record<string, unknown>).artifacts as Array<Record<string, unknown>>).map(a => html`
                        <div style="display:flex;align-items:center;gap:12px;padding:8px 12px;border-radius:8px;background:var(--saas-bg-hover);font-size:12px">
                            <span style="font-size:14px">${a.type === 'json' ? '📄' : a.type === 'csv' ? '📊' : a.type === 'html' ? '🌐' : '📁'}</span>
                            <span style="font-weight:600;flex:1">${String(a.type)}</span>
                            <span style="color:var(--saas-text-muted)">${String(a.format)}</span>
                            <span style="color:var(--saas-text-muted)">${this._formatBytes(Number(a.size_bytes || 0))}</span>
                        </div>`)}
                    </div>
                </div>` : ''}
            </div>`}
        </div>`;
    }

    private _renderResultsData() {
        const results = (this.selectedJobResults as Record<string, unknown>)?.results as Record<string, unknown>;
        if (!results || Object.keys(results).length === 0) {
            return html`
            <div style="text-align:center;padding:24px;opacity:0.4;font-size:12px">
                No extracted data available
            </div>`;
        }

        return html`
        <div style="border:1px solid var(--saas-border);border-radius:8px;overflow:hidden">
            <table style="width:100%;border-collapse:collapse;font-size:12px">
                <thead>
                    <tr style="background:var(--saas-bg-hover)">
                        <th style="text-align:left;padding:10px 16px;font-weight:600;color:var(--saas-text-muted);font-size:11px;border-bottom:1px solid var(--saas-border)">Field</th>
                        <th style="text-align:left;padding:10px 16px;font-weight:600;color:var(--saas-text-muted);font-size:11px;border-bottom:1px solid var(--saas-border)">Value</th>
                    </tr>
                </thead>
                <tbody>
                    ${Object.entries(results).map(([key, val]) => html`
                    <tr style="border-bottom:1px solid var(--saas-border)">
                        <td style="padding:10px 16px;font-weight:600;font-family:JetBrains Mono,monospace;font-size:11px;white-space:nowrap">${key}</td>
                        <td style="padding:10px 16px;color:var(--saas-text-secondary);max-width:400px;overflow:hidden;text-overflow:ellipsis">
                            ${typeof val === 'object' ? html`
                            <details>
                                <summary style="cursor:pointer;font-size:11px;color:var(--saas-text-muted)">Object (${Object.keys(val as Record<string, unknown>).length} keys)</summary>
                                <pre style="font-size:11px;margin-top:4px;padding:8px;background:var(--saas-bg-hover);border-radius:6px;overflow:auto;max-height:200px">${JSON.stringify(val, null, 2)}</pre>
                            </details>` : html`${String(val ?? '—')}`}
                        </td>
                    </tr>`)}
                </tbody>
            </table>
        </div>`;
    }

    // ── Detail Panel ────────────────────────────────────────────────────────

    private _renderDetailPanel() {
        return html`
        <voyant-detail-panel
            .open=${this.detailOpen}
            .title=${this.selectedTemplate?.name || ''}
            .subtitle=${`${this.selectedTemplate?.category || ''} · ${this.selectedTemplate?.engine || 'playwright'}`}
            .width=${500}
            @close=${() => { this.detailOpen = false; this.runResult = null; this.runError = ''; if (this.pollTimer) clearInterval(this.pollTimer); }}
        >
            ${this.selectedTemplate ? html`
            <div>
                <p style="font-size:13px;color:var(--saas-text-secondary);margin-bottom:16px;line-height:1.5">${this.selectedTemplate.description || 'No description'}</p>

                <!-- Stats -->
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:16px">
                    <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover);text-align:center">
                        <div style="font-size:18px;font-weight:800">${this.selectedTemplate.use_count || 0}</div>
                        <div style="font-size:10px;color:var(--saas-text-muted)">Runs</div>
                    </div>
                    <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover);text-align:center">
                        <div style="font-size:18px;font-weight:800">${Math.round((this.selectedTemplate.success_rate || 0) * 100)}%</div>
                        <div style="font-size:10px;color:var(--saas-text-muted)">Success</div>
                    </div>
                    <div style="padding:10px;border-radius:8px;background:var(--saas-bg-hover);text-align:center">
                        <div style="font-size:18px;font-weight:800">${this.selectedTemplate.output_fields?.length || 0}</div>
                        <div style="font-size:10px;color:var(--saas-text-muted)">Fields</div>
                    </div>
                </div>

                <!-- Workflow preview -->
                ${this.selectedTemplate.workflow?.length ? html`
                <h4 style="font-size:11px;font-weight:700;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Workflow</h4>
                <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:16px">
                    ${this.selectedTemplate.workflow.map((step, i) => html`
                    <div style="display:flex;align-items:center;gap:4px">
                        ${i > 0 ? html`<span style="color:var(--saas-text-muted);font-size:10px">→</span>` : ''}
                        <span style="padding:3px 8px;border-radius:6px;font-size:10px;font-weight:600;background:var(--saas-bg-hover);color:var(--saas-text-primary)">${this._actionIcon(String(step.action || ''))} ${String(step.action || '')}</span>
                    </div>`)}
                </div>` : ''}

                <!-- Parameter inputs -->
                ${this.selectedTemplate.parameters?.length ? html`
                <h4 style="font-size:11px;font-weight:700;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Parameters</h4>
                <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:16px">
                    ${this.selectedTemplate.parameters.map(p => html`
                    <div>
                        <label style="font-size:12px;font-weight:600;color:var(--saas-text-primary);display:block;margin-bottom:4px">
                            ${String(p.name || '')} ${p.required ? html`<span style="color:#EF4444">*</span>` : ''}
                            <span style="font-weight:400;color:var(--saas-text-muted);margin-left:4px">${String(p.type || 'string')}</span>
                        </label>
                        <input class="voyant-input" style="font-size:12px;font-family:JetBrains Mono,monospace"
                            placeholder=${String(p.description || p.name || 'Enter value...')}
                            .value=${this.paramValues[String(p.name || '')] || ''}
                            @input=${(e: Event) => { this.paramValues = { ...this.paramValues, [String(p.name)]: (e.target as HTMLInputElement).value }; }}>
                    </div>`)}
                </div>` : ''}

                <!-- Run button -->
                <button class="voyant-btn-primary voyant-btn" style="width:100%;justify-content:center;padding:12px;margin-bottom:12px;${this.running ? 'opacity:0.6;cursor:wait;' : ''}"
                    ?disabled=${this.running}
                    @click=${() => this._runTemplate()}>
                    ${this.running ? html`<span class="animate-spin" style="display:inline-block;margin-right:8px">⏳</span> Scraping...` : html`▶ Run Template`}
                </button>

                <!-- Error -->
                ${this.runError ? html`
                <div style="padding:10px 14px;border-radius:8px;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);font-size:12px;color:#EF4444;margin-bottom:12px">${this.runError}</div>
                ` : ''}

                <!-- Live Audit Trail -->
                ${this.running && this.auditFeed.length > 0 ? html`
                <h4 style="font-size:11px;font-weight:700;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Live Progress</h4>
                <div style="font-family:JetBrains Mono,monospace;font-size:11px;line-height:1.8;background:var(--saas-bg-hover);border-radius:8px;padding:12px;margin-bottom:12px;max-height:200px;overflow-y:auto">
                    ${this.auditFeed.map(line => html`<div>${line}</div>`)}
                </div>
                ` : ''}

                <!-- Results -->
                ${this.runResult && !this.running ? html`
                <div style="border-top:1px solid var(--saas-border);padding-top:16px">
                    <h4 style="font-size:11px;font-weight:700;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Results</h4>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
                        <div style="padding:8px 12px;border-radius:8px;background:var(--saas-bg-hover);font-size:12px">
                            <span style="color:var(--saas-text-muted)">Status:</span>
                            <span style="font-weight:700;color:${this._statusColor(String(this.runResult.status || ''))};margin-left:4px">${String(this.runResult.status || 'unknown')}</span>
                        </div>
                        <div style="padding:8px 12px;border-radius:8px;background:var(--saas-bg-hover);font-size:12px">
                            <span style="color:var(--saas-text-muted)">Pages:</span>
                            <span style="font-weight:700;margin-left:4px">${String(this.runResult.pages_fetched || 0)}</span>
                        </div>
                        <div style="padding:8px 12px;border-radius:8px;background:var(--saas-bg-hover);font-size:12px">
                            <span style="color:var(--saas-text-muted)">Size:</span>
                            <span style="font-weight:700;margin-left:4px">${this.runResult.bytes_processed ? `${(Number(this.runResult.bytes_processed) / 1024).toFixed(1)} KB` : '—'}</span>
                        </div>
                        <div style="padding:8px 12px;border-radius:8px;background:var(--saas-bg-hover);font-size:12px">
                            <span style="color:var(--saas-text-muted)">Job:</span>
                            <span style="font-weight:500;font-family:JetBrains Mono,monospace;font-size:11px;margin-left:4px">${this.jobId.slice(0, 8)}</span>
                        </div>
                    </div>

                    ${this.auditSteps.length > 0 ? html`
                    <h4 style="font-size:11px;font-weight:700;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Execution Steps</h4>
                    <div style="display:flex;flex-direction:column;gap:4px;margin-bottom:12px">
                        ${this.auditSteps.map(s => html`
                        <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;border-radius:6px;font-size:11px;background:var(--saas-bg-hover)">
                            <span style="font-size:14px">${this._actionIcon(s.action)}</span>
                            <span style="font-weight:600;flex:1">${s.action}</span>
                            <span style="color:var(--saas-text-muted)">${s.duration_ms ? `${s.duration_ms.toFixed(0)}ms` : ''}</span>
                            <span style="width:8px;height:8px;border-radius:50%;background:${this._statusColor(s.status)}"></span>
                        </div>`)}
                    </div>` : ''}

                    <!-- View in Results tab -->
                    <button class="voyant-btn" style="width:100%;justify-content:center;font-size:12px;padding:8px;border:1px solid var(--saas-border);border-radius:6px;background:white;cursor:pointer"
                        @click=${() => {
                            if (this.jobId) {
                                this._loadJobResults(this.jobId);
                                this.detailOpen = false;
                                this.tab = 'results';
                            }
                        }}>📊 View Full Results</button>
                </div>
                ` : ''}
            </div>
            ` : ''}
        </voyant-detail-panel>`;
    }
}
