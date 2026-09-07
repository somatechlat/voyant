import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';
import '../components/voyant-data-table';
import '../components/voyant-detail-panel';
import '../components/voyant-metric-card';

interface ScrapeTemplate {
    id: string;
    name: string;
    category: string;
    description: string;
    site_pattern: string;
    status: string;
    engine: string;
    use_count: number;
    success_rate: number;
}

interface ScrapeJob {
    id: string;
    status: string;
    urls: string[];
    pages_fetched: number;
    bytes_processed: number;
    created_at: string;
}

@customElement('view-scraper')
export class ViewScraper extends LitElement {
    @state() tab: 'builder' | 'templates' | 'jobs' | 'visual' = 'visual';
    @state() templates: ScrapeTemplate[] = [];
    @state() jobs: ScrapeJob[] = [];
    @state() loading = true;
    @state() selectedTemplate: ScrapeTemplate | null = null;
    @state() detailOpen = false;

    // Visual builder state
    @state() targetUrl = '';
    @state() pageLoaded = false;
    @state() selectedSelectors: Array<{ name: string; selector: string; type: string }> = [];
    @state() extractMode = 'css';

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this._loadData();
    }

    async _loadData() {
        this.loading = true;
        try {
            const [tplRes, jobRes] = await Promise.all([
                api.get('/scraper/templates').catch(() => []),
                api.get('/admin/scraper/jobs').catch(() => []),
            ]);
            this.templates = (tplRes as ScrapeTemplate[]) || [];
            this.jobs = (jobRes as ScrapeJob[]) || [];
        } catch { /* empty */ }
        finally { this.loading = false; }
    }

    private _loadUrl() {
        if (!this.targetUrl) return;
        this.pageLoaded = true;
    }

    private _addSelector() {
        this.selectedSelectors = [...this.selectedSelectors, { name: '', selector: '', type: 'text' }];
    }

    private _removeSelector(i: number) {
        this.selectedSelectors = this.selectedSelectors.filter((_, idx) => idx !== i);
    }

    private _categories() {
        const cats = new Map<string, number>();
        this.templates.forEach(t => cats.set(t.category, (cats.get(t.category) || 0) + 1));
        return [...cats.entries()];
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/scraper"></saas-sidebar>
        <main class="ml-60 min-h-screen" style="background:var(--saas-bg-page)">
            <!-- Header -->
            <div style="padding:32px 32px 0;display:flex;align-items:center;justify-content:space-between">
                <div>
                    <h1 style="font-size:28px;font-weight:900;font-family:Geist,Inter,system-ui,sans-serif;letter-spacing:-0.02em">Scraper Engine</h1>
                    <p style="font-size:13px;color:var(--saas-text-secondary);margin-top:4px">Visual web scraping — Octoparse-grade, AI-native, ${this.templates.length} templates</p>
                </div>
                <div class="voyant-tabs">
                    <button class="voyant-tab ${this.tab === 'visual' ? 'active' : ''}" @click=${() => { this.tab = 'visual'; }}>🎯 Visual Builder</button>
                    <button class="voyant-tab ${this.tab === 'templates' ? 'active' : ''}" @click=${() => { this.tab = 'templates'; }}>📋 Templates</button>
                    <button class="voyant-tab ${this.tab === 'jobs' ? 'active' : ''}" @click=${() => { this.tab = 'jobs'; }}>⚡ Jobs</button>
                    <button class="voyant-tab ${this.tab === 'builder' ? 'active' : ''}" @click=${() => { this.tab = 'builder'; }}>🔧 Advanced</button>
                </div>
            </div>

            <!-- Metrics -->
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;padding:24px 32px">
                <voyant-metric-card label="Templates" value="${this.templates.length}" icon="📋" color="#FF4D00"></voyant-metric-card>
                <voyant-metric-card label="Categories" value="${this._categories().length}" icon="📂" color="#3B82F6"></voyant-metric-card>
                <voyant-metric-card label="Total Jobs" value="${this.jobs.length}" icon="⚡" color="#22C55E"></voyant-metric-card>
                <voyant-metric-card label="Octopus Arms" value="9" icon="🐙" color="#8B5CF6"></voyant-metric-card>
            </div>

            ${this.loading ? html`<div style="text-align:center;padding:80px;color:var(--saas-text-muted)">Loading...</div>` : html`

            <!-- ====== VISUAL BUILDER (Octoparse clone) ====== -->
            ${this.tab === 'visual' ? html`
            <div style="padding:0 32px 32px">
                <!-- URL Bar -->
                <div class="voyant-card" style="padding:16px 20px;display:flex;gap:12px;align-items:center;margin-bottom:16px">
                    <span style="font-size:14px">🌐</span>
                    <input class="voyant-input" style="flex:1" placeholder="Enter URL to scrape (e.g. https://example.com)" .value=${this.targetUrl} @input=${(e: Event) => { this.targetUrl = (e.target as HTMLInputElement).value; }}>
                    <button class="voyant-btn-primary voyant-btn" @click=${this._loadUrl}>Load Page</button>
                    <select class="voyant-input" style="width:140px" .value=${this.extractMode} @change=${(e: Event) => { this.extractMode = (e.target as HTMLSelectElement).value; }}>
                        <option value="css">CSS Selector</option>
                        <option value="xpath">XPath</option>
                        <option value="auto">AI Auto-detect</option>
                    </select>
                </div>

                <div style="display:grid;grid-template-columns:1fr 360px;gap:16px">
                    <!-- Browser Preview -->
                    <div class="voyant-card" style="height:520px;overflow:hidden;position:relative">
                        ${this.pageLoaded ? html`
                        <div style="position:absolute;top:0;left:0;right:0;height:36px;background:var(--saas-bg-hover);border-bottom:1px solid var(--saas-border);display:flex;align-items:center;padding:0 12px;gap:8px;z-index:1">
                            <div style="display:flex;gap:4px">
                                <div style="width:8px;height:8px;border-radius:50%;background:#EF4444"></div>
                                <div style="width:8px;height:8px;border-radius:50%;background:#F59E0B"></div>
                                <div style="width:8px;height:8px;border-radius:50%;background:#22C55E"></div>
                            </div>
                            <div style="flex:1;padding:4px 12px;border-radius:6px;background:var(--saas-bg-card);font-size:12px;color:var(--saas-text-secondary);font-family:JetBrains Mono,monospace">${this.targetUrl}</div>
                            <span style="font-size:11px;color:var(--saas-text-muted)">🔍 Click elements to select</span>
                        </div>
                        <iframe src=${this.targetUrl} style="width:100%;height:100%;border:none;padding-top:36px" sandbox="allow-same-origin allow-scripts"></iframe>
                        ` : html`
                        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:16px">
                            <div style="font-size:48px;opacity:0.3">🌐</div>
                            <div style="font-size:14px;color:var(--saas-text-muted)">Enter a URL above to load the page</div>
                            <div style="font-size:12px;color:var(--saas-text-muted)">Point and click to select elements for extraction</div>
                            <div style="display:flex;gap:8px;margin-top:16px">
                                <button class="voyant-btn" @click=${() => { this.targetUrl = 'https://xtrim.com.ec'; this._loadUrl(); }}>Try: xtrim.com.ec</button>
                                <button class="voyant-btn" @click=${() => { this.targetUrl = 'https://news.ycombinator.com'; this._loadUrl(); }}>Try: Hacker News</button>
                            </div>
                        </div>
                        `}
                    </div>

                    <!-- Selector Panel -->
                    <div style="display:flex;flex-direction:column;gap:16px">
                        <div class="voyant-card" style="padding:20px">
                            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
                                <h3 style="font-size:14px;font-weight:600">Extraction Rules</h3>
                                <button class="voyant-btn" style="font-size:11px" @click=${this._addSelector}>+ Add Field</button>
                            </div>
                            ${this.selectedSelectors.length === 0 ? html`
                            <div style="text-align:center;padding:24px;color:var(--saas-text-muted);font-size:12px">
                                <p>No fields defined yet.</p>
                                <p style="margin-top:4px">Click "Add Field" or click elements in the preview.</p>
                            </div>
                            ` : html`
                            <div style="display:flex;flex-direction:column;gap:8px">
                                ${this.selectedSelectors.map((s, i) => html`
                                <div style="display:flex;gap:6px;align-items:center">
                                    <input class="voyant-input" style="flex:1;font-size:11px" placeholder="Field name" .value=${s.name} @input=${(e: Event) => { this.selectedSelectors[i].name = (e.target as HTMLInputElement).value; }}>
                                    <input class="voyant-input" style="flex:2;font-size:11px;font-family:JetBrains Mono,monospace" placeholder=".css-selector or //xpath" .value=${s.selector} @input=${(e: Event) => { this.selectedSelectors[i].selector = (e.target as HTMLInputElement).value; }}>
                                    <select class="voyant-input" style="width:80px;font-size:11px" .value=${s.type} @change=${(e: Event) => { this.selectedSelectors[i].type = (e.target as HTMLSelectElement).value; }}>
                                        <option value="text">Text</option>
                                        <option value="html">HTML</option>
                                        <option value="attr">Attribute</option>
                                        <option value="image">Image</option>
                                        <option value="link">Link</option>
                                    </select>
                                    <button class="voyant-btn-ghost voyant-btn" style="padding:4px 8px;color:var(--saas-danger)" @click=${() => this._removeSelector(i)}>×</button>
                                </div>`)}
                            </div>`}
                        </div>

                        <div class="voyant-card" style="padding:20px">
                            <h3 style="font-size:14px;font-weight:600;margin-bottom:12px">Pagination</h3>
                            <select class="voyant-input" style="margin-bottom:8px">
                                <option value="none">No pagination</option>
                                <option value="next_button">Click "Next" button</option>
                                <option value="infinite_scroll">Infinite scroll</option>
                                <option value="load_more">Click "Load More"</option>
                                <option value="url_pattern">URL pattern (?page=1,2,3...)</option>
                            </select>
                            <input class="voyant-input" placeholder="Next button selector (optional)" style="font-size:11px">
                        </div>

                        <div class="voyant-card" style="padding:20px">
                            <h3 style="font-size:14px;font-weight:600;margin-bottom:12px">Anti-Bot</h3>
                            <div style="display:flex;flex-direction:column;gap:8px;font-size:12px">
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                                    <input type="checkbox" checked> Use Playwright (JS rendering)
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                                    <input type="checkbox"> Evasion mode (curl-cffi + camoufox)
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                                    <input type="checkbox"> Rotate user agent
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                                    <input type="checkbox"> Block resources (images/fonts)
                                </label>
                            </div>
                        </div>

                        <div style="display:flex;gap:8px">
                            <button class="voyant-btn-primary voyant-btn" style="flex:1;justify-content:center">▶ Run Extraction</button>
                            <button class="voyant-btn" style="flex:1;justify-content:center">💾 Save Template</button>
                        </div>
                    </div>
                </div>
            </div>
            ` : ''}

            <!-- ====== TEMPLATES ====== -->
            ${this.tab === 'templates' ? html`
            <div style="padding:0 32px 32px">
                <!-- Category filters -->
                <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
                    <button class="voyant-btn voyant-btn-ghost" style="background:var(--saas-brand-light)">All (${this.templates.length})</button>
                    ${this._categories().map(([cat, count]) => html`
                    <button class="voyant-btn voyant-btn-ghost">${cat} (${count})</button>
                    `)}
                </div>

                <!-- Template grid -->
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px">
                    ${this.templates.map(t => html`
                    <div class="voyant-card" style="padding:20px;cursor:pointer" @click=${() => { this.selectedTemplate = t; this.detailOpen = true; }}>
                        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
                            <div style="width:36px;height:36px;border-radius:10px;background:var(--saas-brand-light);display:flex;align-items:center;justify-content:center;font-size:16px">🕷️</div>
                            <div style="flex:1">
                                <div style="font-size:13px;font-weight:700">${t.name}</div>
                                <div style="font-size:11px;color:var(--saas-text-muted)">${t.site_pattern}</div>
                            </div>
                            <span class="voyant-badge ${t.status === 'active' ? 'voyant-badge-success' : 'voyant-badge-warning'}">${t.status}</span>
                        </div>
                        <p style="font-size:12px;color:var(--saas-text-secondary);margin-bottom:12px;min-height:32px">${t.description || 'No description'}</p>
                        <div style="display:flex;gap:16px;font-size:11px;color:var(--saas-text-muted)">
                            <span>Engine: ${t.engine}</span>
                            <span>Used: ${t.use_count}x</span>
                            <span>Success: ${Math.round((t.success_rate || 0) * 100)}%</span>
                        </div>
                    </div>`)}
                </div>
            </div>
            ` : ''}

            <!-- ====== JOBS ====== -->
            ${this.tab === 'jobs' ? html`
            <div style="padding:0 32px 32px">
                <div class="voyant-card" style="padding:20px">
                    <voyant-data-table
                        .columns=${[
                            { key: 'id', label: 'Job ID', sortable: true },
                            { key: 'status', label: 'Status', sortable: true, format: 'badge' as const, badgeColors: { succeeded: '#22C55E', running: '#3B82F6', failed: '#EF4444', queued: '#F59E0B' } },
                            { key: 'pages', label: 'Pages', sortable: true, format: 'number' as const },
                            { key: 'size', label: 'Size', sortable: true },
                            { key: 'created', label: 'Created', sortable: true },
                        ]}
                        .rows=${this.jobs.map(j => ({
                            id: j.id?.slice(0, 8) || '—',
                            status: j.status,
                            pages: j.pages_fetched || 0,
                            size: j.bytes_processed ? `${(j.bytes_processed / 1024).toFixed(1)} KB` : '—',
                            created: j.created_at ? new Date(j.created_at).toLocaleString() : '—',
                        }))}
                        .exportable=${true}
                    ></voyant-data-table>
                </div>
            </div>
            ` : ''}

            <!-- ====== ADVANCED BUILDER ====== -->
            ${this.tab === 'builder' ? html`
            <div style="padding:0 32px 32px">
                <div style="display:grid;grid-template-columns:240px 1fr 300px;gap:16px">
                    <!-- Step Palette -->
                    <div class="voyant-card" style="padding:20px">
                        <h3 style="font-size:13px;font-weight:600;margin-bottom:16px;color:var(--saas-text-muted);text-transform:uppercase;letter-spacing:0.05em">Steps</h3>
                        ${['Navigate', 'Click', 'Scroll', 'Wait', 'Extract', 'Paginate', 'Login', 'Screenshot', 'Download', 'Loop', 'Condition', 'Transform'].map(step => html`
                        <div style="padding:8px 12px;border-radius:8px;font-size:12px;cursor:pointer;margin-bottom:4px;transition:all 120ms"
                            @mouseenter=${(e: Event) => { const el = e.currentTarget as HTMLElement; el.style.background = 'var(--saas-brand-light)'; el.style.color = 'var(--saas-brand)'; }}
                            @mouseleave=${(e: Event) => { const el = e.currentTarget as HTMLElement; el.style.background = ''; el.style.color = ''; }}>
                            ${step}
                        </div>`)}
                    </div>

                    <!-- Canvas -->
                    <div class="voyant-card" style="min-height:480px;padding:20px;position:relative">
                        <div style="position:absolute;top:12px;left:12px;font-size:11px;color:var(--saas-text-muted)">Drag steps from the palette to build your workflow</div>
                        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:16px">
                            <div style="font-size:32px;opacity:0.2">🔧</div>
                            <div style="font-size:13px;color:var(--saas-text-muted)">Drag steps here to build your extraction workflow</div>
                            <div style="font-size:12px;color:var(--saas-text-muted)">Or use a template to get started</div>
                            <button class="voyant-btn">Load from Template</button>
                        </div>
                    </div>

                    <!-- Config Panel -->
                    <div style="display:flex;flex-direction:column;gap:16px">
                        <div class="voyant-card" style="padding:20px">
                            <h3 style="font-size:13px;font-weight:600;margin-bottom:12px">Step Configuration</h3>
                            <div style="text-align:center;padding:24px;color:var(--saas-text-muted);font-size:12px">Select a step to configure</div>
                        </div>
                        <div class="voyant-card" style="padding:20px">
                            <h3 style="font-size:13px;font-weight:600;margin-bottom:12px">Output Format</h3>
                            <select class="voyant-input" style="margin-bottom:8px">
                                <option value="json">JSON</option>
                                <option value="csv">CSV</option>
                                <option value="xlsx">Excel (XLSX)</option>
                                <option value="parquet">Parquet</option>
                                <option value="database">Database (PostgreSQL)</option>
                            </select>
                        </div>
                        <div class="voyant-card" style="padding:20px">
                            <h3 style="font-size:13px;font-weight:600;margin-bottom:12px">Schedule</h3>
                            <select class="voyant-input">
                                <option value="once">Run once</option>
                                <option value="hourly">Every hour</option>
                                <option value="daily">Daily</option>
                                <option value="weekly">Weekly</option>
                                <option value="custom">Custom cron</option>
                            </select>
                        </div>
                        <button class="voyant-btn-primary voyant-btn" style="width:100%;justify-content:center">▶ Run Workflow</button>
                    </div>
                </div>
            </div>
            ` : ''}

            `}

            <!-- Detail Panel -->
            <voyant-detail-panel
                .open=${this.detailOpen}
                .title=${this.selectedTemplate?.name || ''}
                .subtitle=${`Template · ${this.selectedTemplate?.category || ''}`}
                @close=${() => { this.detailOpen = false; }}
            >
                ${this.selectedTemplate ? html`
                <div style="font-family:Inter,system-ui,sans-serif">
                    <p style="font-size:13px;color:var(--saas-text-secondary);margin-bottom:24px">${this.selectedTemplate.description || 'No description'}</p>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:24px">
                        <div style="padding:12px;border-radius:8px;background:var(--saas-bg-hover)">
                            <div style="font-size:11px;color:var(--saas-text-muted)">Engine</div>
                            <div style="font-size:13px;font-weight:600">${this.selectedTemplate.engine}</div>
                        </div>
                        <div style="padding:12px;border-radius:8px;background:var(--saas-bg-hover)">
                            <div style="font-size:11px;color:var(--saas-text-muted)">Success Rate</div>
                            <div style="font-size:13px;font-weight:600">${Math.round((this.selectedTemplate.success_rate || 0) * 100)}%</div>
                        </div>
                        <div style="padding:12px;border-radius:8px;background:var(--saas-bg-hover)">
                            <div style="font-size:11px;color:var(--saas-text-muted)">Used</div>
                            <div style="font-size:13px;font-weight:600">${this.selectedTemplate.use_count} times</div>
                        </div>
                        <div style="padding:12px;border-radius:8px;background:var(--saas-bg-hover)">
                            <div style="font-size:11px;color:var(--saas-text-muted)">Status</div>
                            <div style="font-size:13px;font-weight:600">${this.selectedTemplate.status}</div>
                        </div>
                    </div>
                    <h4 style="font-size:12px;font-weight:600;color:var(--saas-text-muted);text-transform:uppercase;margin-bottom:12px">Site Pattern</h4>
                    <div style="padding:8px 12px;border-radius:6px;background:var(--saas-bg-hover);font-family:JetBrains Mono,monospace;font-size:12px;color:var(--saas-text-primary);margin-bottom:24px">${this.selectedTemplate.site_pattern}</div>
                    <button class="voyant-btn-primary voyant-btn" style="width:100%;justify-content:center">▶ Run Template</button>
                </div>
                ` : ''}
            </voyant-detail-panel>
        </main>`;
    }
}
