import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-data-table';
import '../components/voyant-detail-panel';
import '../components/voyant-metric-card';

interface Template {
    id: string;
    name: string;
    category: string;
    description: string;
    site_pattern: string;
    status: string;
    engine: string;
    use_count: number;
    success_rate: number;
    selectors?: Record<string, unknown>;
    workflow?: Array<Record<string, unknown>>;
    parameters?: Array<Record<string, unknown>>;
    output_fields?: string[];
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

@customElement('view-scraper')
export class ViewScraper extends LitElement {
    @state() tab: 'templates' | 'builder' | 'jobs' | 'audit' = 'templates';
    @state() templates: Template[] = [];
    @state() categories: Category[] = [];
    @state() loading = true;
    @state() selectedTemplate: Template | null = null;
    @state() detailOpen = false;
    @state() activeCategory = 'all';

    // Run state
    @state() paramValues: Record<string, string> = {};
    @state() running = false;
    @state() runResult: Record<string, unknown> | null = null;
    @state() runError = '';
    @state() auditSteps: AuditStep[] = [];
    @state() auditFeed: string[] = [];
    @state() jobId = '';
    @state() pollTimer = 0;

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

    private _filteredTemplates() {
        if (this.activeCategory === 'all') return this.templates;
        return this.templates.filter(t => t.category === this.activeCategory);
    }

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

            // Poll for audit trail
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

                // Check if done
                if (this.runResult?.status === 'succeeded' || this.runResult?.status === 'failed' || attempts > 30) {
                    clearInterval(this.pollTimer);
                    this.running = false;

                    // Fetch final result
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

    private _statusColor(status: string): string {
        if (status === 'succeeded') return '#22C55E';
        if (status === 'failed') return '#EF4444';
        if (status === 'running') return '#3B82F6';
        return '#9CA3AF';
    }

    private _actionIcon(action: string): string {
        const icons: Record<string, string> = {
            navigate: '🌐', fetch: '🌐', scroll: '📜', click: '🖱️',
            wait: '⏳', extract: '📊', enter_text: '⌨️', hover: '👆',
            capture_html: '📄', close_popup: '❌',
        };
        return icons[action] || '⚡';
    }

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
                <div class="voyant-tabs">
                    <button class="voyant-tab ${this.tab === 'templates' ? 'active' : ''}" @click=${() => { this.tab = 'templates'; }}>📋 Templates</button>
                    <button class="voyant-tab ${this.tab === 'builder' ? 'active' : ''}" @click=${() => { this.tab = 'builder'; }}>🔧 Builder</button>
                    <button class="voyant-tab ${this.tab === 'jobs' ? 'active' : ''}" @click=${() => { this.tab = 'jobs'; }}>⚡ Jobs</button>
                    <button class="voyant-tab ${this.tab === 'audit' ? 'active' : ''}" @click=${() => { this.tab = 'audit'; }}>📡 Audit</button>
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

            ${this.loading ? html`<div style="text-align:center;padding:80px;color:var(--saas-text-muted)">Loading...</div>` : html`

            <!-- ═══════════ TEMPLATES ═══════════ -->
            ${this.tab === 'templates' ? html`
            <div style="padding:0 32px 32px">
                <!-- Category pills -->
                <div style="display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap">
                    <button style="padding:6px 16px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid ${this.activeCategory === 'all' ? '#FF4D00' : '#E5E7EB'};background:${this.activeCategory === 'all' ? '#FF4D00' : 'white'};color:${this.activeCategory === 'all' ? 'white' : '#6B7280'};transition:all 120ms"
                        @click=${() => { this.activeCategory = 'all'; }}>All (${this.templates.length})</button>
                    ${this.categories.map(c => html`
                    <button style="padding:6px 16px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid ${this.activeCategory === c.category ? '#FF4D00' : '#E5E7EB'};background:${this.activeCategory === c.category ? '#FF4D00' : 'white'};color:${this.activeCategory === c.category ? 'white' : '#6B7280'};transition:all 120ms"
                        @click=${() => { this.activeCategory = c.category; }}>
                        ${c.category} (${c.count})
                    </button>`)}
                </div>

                <!-- Template grid -->
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px">
                    ${this._filteredTemplates().map(t => html`
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:20px;cursor:pointer;transition:all 200ms"
                        @mouseenter=${(e: Event) => { const el = e.currentTarget as HTMLElement; el.style.borderColor = '#FF4D00'; el.style.boxShadow = '0 4px 12px rgba(255,77,0,0.1)'; el.style.transform = 'translateY(-2px)'; }}
                        @mouseleave=${(e: Event) => { const el = e.currentTarget as HTMLElement; el.style.borderColor = 'var(--saas-border)'; el.style.boxShadow = ''; el.style.transform = ''; }}
                        @click=${() => this._openTemplate(t)}>
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
                    </div>`)}
                </div>
            </div>
            ` : ''}

            <!-- ═══════════ BUILDER ═══════════ -->
            ${this.tab === 'builder' ? html`
            <div style="padding:0 32px 32px">
                <div style="display:grid;grid-template-columns:220px 1fr 280px;gap:16px">
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:16px">
                        <h3 style="font-size:11px;font-weight:700;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px">Workflow Steps</h3>
                        ${['Navigate', 'Click', 'Scroll', 'Wait', 'Extract', 'Enter Text', 'Hover', 'Loop', 'Condition', 'Paginate', 'Login', 'Screenshot'].map(step => html`
                        <div style="padding:8px 12px;border-radius:8px;font-size:12px;cursor:grab;margin-bottom:4px;transition:all 120ms;color:var(--saas-text-secondary);display:flex;align-items:center;gap:8px"
                            @mouseenter=${(e: Event) => { const el = e.currentTarget as HTMLElement; el.style.background = 'rgba(255,77,0,0.08)'; el.style.color = '#FF4D00'; }}
                            @mouseleave=${(e: Event) => { const el = e.currentTarget as HTMLElement; el.style.background = ''; el.style.color = 'var(--saas-text-secondary)'; }}>
                            <span style="font-size:14px">${this._actionIcon(step.toLowerCase().replace(' ', '_'))}</span> ${step}
                        </div>`)}
                    </div>
                    <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;min-height:480px;position:relative">
                        <div style="position:absolute;top:12px;left:12px;font-size:11px;color:var(--saas-text-muted)">Drag steps from the palette to build your workflow</div>
                        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:12px;opacity:0.3">
                            <div style="font-size:40px">🔧</div>
                            <div style="font-size:13px">Drag steps here to build your workflow</div>
                        </div>
                    </div>
                    <div style="display:flex;flex-direction:column;gap:16px">
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
                        <button class="voyant-btn-primary voyant-btn" style="width:100%;justify-content:center">▶ Run Workflow</button>
                    </div>
                </div>
            </div>
            ` : ''}

            <!-- ═══════════ JOBS ═══════════ -->
            ${this.tab === 'jobs' ? html`
            <div style="padding:0 32px 32px">
                <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:24px">
                    <div style="text-align:center;padding:60px;opacity:0.4">
                        <div style="font-size:40px;margin-bottom:12px">⚡</div>
                        <div style="font-size:13px">No scraping jobs yet. Run a template to see jobs here.</div>
                    </div>
                </div>
            </div>
            ` : ''}

            <!-- ═══════════ AUDIT ═══════════ -->
            ${this.tab === 'audit' ? html`
            <div style="padding:0 32px 32px">
                <div style="background:var(--saas-bg-card);border:1px solid var(--saas-border);border-radius:12px;padding:24px">
                    <h3 style="font-size:14px;font-weight:700;margin-bottom:16px">Live Audit Feed</h3>
                    ${this.auditFeed.length > 0 ? html`
                    <div style="font-family:JetBrains Mono,monospace;font-size:12px;line-height:2;background:var(--saas-bg-hover);border-radius:8px;padding:16px;max-height:400px;overflow-y:auto">
                        ${this.auditFeed.map(line => html`<div style="color:var(--saas-text-primary)">${line}</div>`)}
                    </div>
                    ` : html`
                    <div style="text-align:center;padding:40px;opacity:0.4">
                        <div style="font-size:32px;margin-bottom:8px">📡</div>
                        <div style="font-size:12px">Run a template to see the live audit trail here</div>
                    </div>
                    `}
                </div>
            </div>
            ` : ''}

            `}

            <!-- ═══════════ DETAIL PANEL ═══════════ -->
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
                    </div>
                    ` : ''}
                </div>
                ` : ''}
            </voyant-detail-panel>
        </main>`;
    }
}
