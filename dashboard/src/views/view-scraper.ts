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
}

interface Category {
    category: string;
    count: number;
}

@customElement('view-scraper')
export class ViewScraper extends LitElement {
    @state() tab: 'visual' | 'templates' | 'jobs' | 'advanced' = 'visual';
    @state() templates: Template[] = [];
    @state() categories: Category[] = [];
    @state() loading = true;
    @state() selectedTemplate: Template | null = null;
    @state() detailOpen = false;
    @state() activeCategory = 'all';

    // Visual builder state
    @state() targetUrl = '';
    @state() extractMode = 'css';
    @state() paginationMode = 'none';
    @state() usePlaywright = true;
    @state() useEvasion = false;
    @state() blockResources = true;
    @state() rotateUA = false;
    @state() selectors: Array<{ name: string; selector: string; type: string }> = [];

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

    private _filteredTemplates() {
        if (this.activeCategory === 'all') return this.templates;
        return this.templates.filter(t => t.category === this.activeCategory);
    }

    private _addSelector() {
        this.selectors = [...this.selectors, { name: `field_${this.selectors.length + 1}`, selector: '', type: 'text' }];
    }

    private _removeSelector(i: number) {
        this.selectors = this.selectors.filter((_, idx) => idx !== i);
    }

    private _runExtraction() {
        // Dispatch to VOYANT scraper API
        api.post('/scrape/start', {
            urls: [this.targetUrl],
            selectors: Object.fromEntries(this.selectors.filter(s => s.selector).map(s => [s.name, s.selector])),
            options: {
                engine: this.usePlaywright ? 'playwright' : 'httpx',
                block_resources: this.blockResources,
                timeout: 30,
            },
        }).then(res => {
            console.log('Scrape started:', res);
        }).catch(err => {
            console.error('Scrape failed:', err);
        });
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/scraper"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface">
            <!-- Top bar -->
            <div class="bg-white border-b border-gray-100 px-8 py-5">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="text-2xl font-black font-display tracking-tight">Scraper Engine</h1>
                        <p class="text-sm text-gray-400 mt-1">Visual web extraction — ${this.templates.length} templates across ${this.categories.length} categories</p>
                    </div>
                    <div class="flex gap-1 bg-white rounded-lg p-1 border border-gray-100">
                        ${[
                            { id: 'visual' as const, icon: '🎯', label: 'Visual Builder' },
                            { id: 'templates' as const, icon: '📋', label: 'Templates' },
                            { id: 'jobs' as const, icon: '⚡', label: 'Jobs' },
                            { id: 'advanced' as const, icon: '🔧', label: 'Advanced' },
                        ].map(t => html`
                        <button class="px-4 py-2 text-sm font-semibold rounded-md transition-all ${this.tab === t.id ? 'bg-brand text-white shadow-sm' : 'text-gray-500 hover:text-ink hover:bg-gray-50'}"
                            @click=${() => { this.tab = t.id; }}>
                            <span class="mr-1">${t.icon}</span> ${t.label}
                        </button>`)}
                    </div>
                </div>
            </div>

            <!-- Stats -->
            <div class="grid grid-cols-4 gap-4 px-8 py-5">
                <voyant-metric-card label="Templates" value="${this.templates.length}" icon="📋" color="#FF4D00"></voyant-metric-card>
                <voyant-metric-card label="Categories" value="${this.categories.length}" icon="📂" color="#3B82F6"></voyant-metric-card>
                <voyant-metric-card label="Octopus Arms" value="9" icon="🐙" color="#8B5CF6"></voyant-metric-card>
                <voyant-metric-card label="Success Rate" value="94%" icon="✅" color="#22C55E" trend="Last 30 days" trendDirection="up"></voyant-metric-card>
            </div>

            ${this.loading ? html`<div class="text-center py-20 text-gray-400">Loading templates...</div>` : html`

            <!-- ═══════════ VISUAL BUILDER ═══════════ -->
            ${this.tab === 'visual' ? html`
            <div class="px-8 pb-8">
                <!-- URL Bar -->
                <div class="bg-white rounded-xl border border-gray-100 p-4 mb-4 flex items-center gap-3">
                    <div class="flex items-center gap-2 text-gray-400">
                        <span class="text-lg">🌐</span>
                        <span class="text-xs font-semibold uppercase tracking-wider">URL</span>
                    </div>
                    <input class="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono focus:border-brand focus:ring-2 focus:ring-brand/20 outline-none transition-all"
                        placeholder="https://example.com/page-to-scrape"
                        .value=${this.targetUrl}
                        @input=${(e: Event) => { this.targetUrl = (e.target as HTMLInputElement).value; }}>
                    <select class="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:border-brand outline-none" .value=${this.extractMode}
                        @change=${(e: Event) => { this.extractMode = (e.target as HTMLSelectElement).value; }}>
                        <option value="css">CSS Selector</option>
                        <option value="xpath">XPath</option>
                        <option value="auto">AI Auto-detect</option>
                    </select>
                    <button class="bg-brand text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-brand-hover transition-colors shadow-sm"
                        @click=${this._runExtraction}>
                        ▶ Extract
                    </button>
                </div>

                <div class="grid grid-cols-[1fr_380px] gap-4">
                    <!-- Preview area -->
                    <div class="bg-white rounded-xl border border-gray-100 overflow-hidden" style="height:520px">
                        ${this.targetUrl ? html`
                        <div class="h-9 border-b border-gray-100 flex items-center px-3 gap-2 bg-gray-50">
                            <div class="flex gap-1.5">
                                <div class="w-2.5 h-2.5 rounded-full bg-red-400"></div>
                                <div class="w-2.5 h-2.5 rounded-full bg-yellow-400"></div>
                                <div class="w-2.5 h-2.5 rounded-full bg-green-400"></div>
                            </div>
                            <div class="flex-1 px-3 py-0.5 rounded bg-white border border-gray-200 text-xs text-gray-500 font-mono truncate">${this.targetUrl}</div>
                        </div>
                        <iframe src=${this.targetUrl} class="w-full h-full border-none" style="height:calc(100% - 36px)" sandbox="allow-same-origin allow-scripts"></iframe>
                        ` : html`
                        <div class="flex flex-col items-center justify-center h-full gap-4">
                            <div class="text-5xl opacity-20">🕷️</div>
                            <div class="text-sm text-gray-400">Enter a URL to start extracting data</div>
                            <div class="flex gap-2 mt-2">
                                <button class="px-4 py-2 rounded-lg border border-gray-200 text-sm hover:border-brand hover:text-brand transition-colors"
                                    @click=${() => { this.targetUrl = 'https://xtrim.com.ec'; }}>xtrim.com.ec</button>
                                <button class="px-4 py-2 rounded-lg border border-gray-200 text-sm hover:border-brand hover:text-brand transition-colors"
                                    @click=${() => { this.targetUrl = 'https://news.ycombinator.com'; }}>Hacker News</button>
                                <button class="px-4 py-2 rounded-lg border border-gray-200 text-sm hover:border-brand hover:text-brand transition-colors"
                                    @click=${() => { this.targetUrl = 'https://amazon.com'; }}>Amazon</button>
                            </div>
                        </div>
                        `}
                    </div>

                    <!-- Right panel -->
                    <div class="flex flex-col gap-4">
                        <!-- Extraction Fields -->
                        <div class="bg-white rounded-xl border border-gray-100 p-5">
                            <div class="flex items-center justify-between mb-4">
                                <h3 class="text-sm font-bold">Extraction Fields</h3>
                                <button class="text-xs font-semibold text-brand hover:text-brand-hover transition-colors" @click=${this._addSelector}>+ Add Field</button>
                            </div>
                            ${this.selectors.length === 0 ? html`
                            <div class="text-center py-6 text-gray-300 text-xs">
                                <div class="text-2xl mb-2 opacity-40">🎯</div>
                                <p>No fields yet. Click "Add Field" to define what to extract.</p>
                            </div>
                            ` : html`
                            <div class="flex flex-col gap-2 max-h-48 overflow-y-auto">
                                ${this.selectors.map((s, i) => html`
                                <div class="flex gap-1.5 items-center">
                                    <input class="w-20 px-2 py-1.5 rounded border border-gray-200 text-xs focus:border-brand outline-none" placeholder="Name" .value=${s.name}
                                        @input=${(e: Event) => { this.selectors[i].name = (e.target as HTMLInputElement).value; }}>
                                    <input class="flex-1 px-2 py-1.5 rounded border border-gray-200 text-xs font-mono focus:border-brand outline-none" placeholder=".selector" .value=${s.selector}
                                        @input=${(e: Event) => { this.selectors[i].selector = (e.target as HTMLInputElement).value; }}>
                                    <select class="w-16 px-1 py-1.5 rounded border border-gray-200 text-xs" .value=${s.type}
                                        @change=${(e: Event) => { this.selectors[i].type = (e.target as HTMLSelectElement).value; }}>
                                        <option value="text">Text</option><option value="html">HTML</option><option value="attr">Attr</option><option value="link">Link</option><option value="img">Img</option>
                                    </select>
                                    <button class="text-gray-300 hover:text-red-500 text-sm transition-colors" @click=${() => this._removeSelector(i)}>×</button>
                                </div>`)}
                            </div>`}
                        </div>

                        <!-- Pagination -->
                        <div class="bg-white rounded-xl border border-gray-100 p-5">
                            <h3 class="text-sm font-bold mb-3">Pagination</h3>
                            <select class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:border-brand outline-none" .value=${this.paginationMode}
                                @change=${(e: Event) => { this.paginationMode = (e.target as HTMLSelectElement).value; }}>
                                <option value="none">No pagination</option>
                                <option value="next">Click "Next" button</option>
                                <option value="scroll">Infinite scroll</option>
                                <option value="more">Click "Load More"</option>
                                <option value="url">URL pattern (?page=N)</option>
                            </select>
                            ${this.paginationMode === 'next' || this.paginationMode === 'more' ? html`
                            <input class="w-full px-3 py-2 rounded-lg border border-gray-200 text-xs font-mono mt-2 focus:border-brand outline-none" placeholder="Button selector (.next-page)">` : ''}
                        </div>

                        <!-- Engine Options -->
                        <div class="bg-white rounded-xl border border-gray-100 p-5">
                            <h3 class="text-sm font-bold mb-3">Engine</h3>
                            <div class="flex flex-col gap-2 text-sm">
                                <label class="flex items-center gap-2 cursor-pointer"><input type="checkbox" class="accent-brand" .checked=${this.usePlaywright} @change=${() => { this.usePlaywright = !this.usePlaywright; }}> <span>Playwright (JS rendering)</span></label>
                                <label class="flex items-center gap-2 cursor-pointer"><input type="checkbox" class="accent-brand" .checked=${this.useEvasion} @change=${() => { this.useEvasion = !this.useEvasion; }}> <span>Evasion mode (anti-bot)</span></label>
                                <label class="flex items-center gap-2 cursor-pointer"><input type="checkbox" class="accent-brand" .checked=${this.blockResources} @change=${() => { this.blockResources = !this.blockResources; }}> <span>Block images/fonts</span></label>
                                <label class="flex items-center gap-2 cursor-pointer"><input type="checkbox" class="accent-brand" .checked=${this.rotateUA} @change=${() => { this.rotateUA = !this.rotateUA; }}> <span>Rotate user agent</span></label>
                            </div>
                        </div>

                        <!-- Actions -->
                        <div class="flex gap-2">
                            <button class="flex-1 bg-brand text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-brand-hover transition-colors shadow-sm"
                                @click=${this._runExtraction}>▶ Run</button>
                            <button class="flex-1 py-2.5 rounded-lg border border-gray-200 text-sm font-semibold hover:border-brand hover:text-brand transition-colors">💾 Save</button>
                        </div>
                    </div>
                </div>
            </div>
            ` : ''}

            <!-- ═══════════ TEMPLATES ═══════════ -->
            ${this.tab === 'templates' ? html`
            <div class="px-8 pb-8">
                <div class="flex gap-2 mb-5 flex-wrap">
                    <button class="px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${this.activeCategory === 'all' ? 'bg-brand text-white' : 'bg-white border border-gray-200 text-gray-500 hover:border-brand hover:text-brand'}"
                        @click=${() => { this.activeCategory = 'all'; }}>All (${this.templates.length})</button>
                    ${this.categories.map(c => html`
                    <button class="px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${this.activeCategory === c.category ? 'bg-brand text-white' : 'bg-white border border-gray-200 text-gray-500 hover:border-brand hover:text-brand'}"
                        @click=${() => { this.activeCategory = c.category; }}>
                        ${c.category} (${c.count})
                    </button>`)}
                </div>

                <div class="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-4">
                    ${this._filteredTemplates().map(t => html`
                    <div class="bg-white rounded-xl border border-gray-100 p-5 cursor-pointer hover:border-brand hover:shadow-md transition-all group"
                        @click=${() => { this.selectedTemplate = t; this.detailOpen = true; }}>
                        <div class="flex items-start gap-3 mb-3">
                            <div class="w-10 h-10 rounded-xl bg-brand/8 flex items-center justify-center text-lg flex-shrink-0 group-hover:bg-brand/15 transition-colors">🕷️</div>
                            <div class="flex-1 min-w-0">
                                <div class="text-sm font-bold truncate">${t.name}</div>
                                <div class="text-xs text-gray-400 truncate">${t.site_pattern}</div>
                            </div>
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${t.status === 'active' ? 'bg-green-50 text-green-600' : 'bg-yellow-50 text-yellow-600'}">${t.status}</span>
                        </div>
                        <p class="text-xs text-gray-400 mb-3 line-clamp-2" style="min-height:32px">${t.description || 'No description'}</p>
                        <div class="flex items-center gap-4 text-[11px] text-gray-400">
                            <span class="px-2 py-0.5 rounded bg-gray-50">${t.category}</span>
                            <span>${t.engine || 'playwright'}</span>
                            <span>${t.use_count || 0} runs</span>
                        </div>
                    </div>`)}
                </div>
            </div>
            ` : ''}

            <!-- ═══════════ JOBS ═══════════ -->
            ${this.tab === 'jobs' ? html`
            <div class="px-8 pb-8">
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-sm font-bold">Recent Scraping Jobs</h3>
                        <button class="text-xs font-semibold text-brand">View All →</button>
                    </div>
                    <div class="text-center py-12 text-gray-300">
                        <div class="text-4xl mb-3 opacity-30">⚡</div>
                        <p class="text-sm">No scraping jobs yet. Use the Visual Builder or run a template to get started.</p>
                    </div>
                </div>
            </div>
            ` : ''}

            <!-- ═══════════ ADVANCED ═══════════ -->
            ${this.tab === 'advanced' ? html`
            <div class="px-8 pb-8">
                <div class="grid grid-cols-[220px_1fr_280px] gap-4">
                    <!-- Step palette -->
                    <div class="bg-white rounded-xl border border-gray-100 p-4">
                        <h3 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Workflow Steps</h3>
                        ${['Navigate', 'Click', 'Scroll', 'Wait', 'Extract', 'Paginate', 'Login', 'Screenshot', 'Download', 'Loop', 'Condition', 'Transform'].map(step => html`
                        <div class="px-3 py-2 rounded-lg text-sm cursor-pointer transition-all hover:bg-brand/8 hover:text-brand mb-0.5 flex items-center gap-2">
                            <span class="text-xs opacity-50">⣿</span> ${step}
                        </div>`)}
                    </div>

                    <!-- Canvas -->
                    <div class="bg-white rounded-xl border border-gray-100 min-h-[480px] relative">
                        <div class="absolute top-3 left-3 text-xs text-gray-300">Drag steps here to build your workflow</div>
                        <div class="flex flex-col items-center justify-center h-full gap-3 opacity-40">
                            <div class="text-4xl">🔧</div>
                            <div class="text-sm">Drag steps from the palette</div>
                            <div class="text-xs">Or load a template to get started</div>
                        </div>
                    </div>

                    <!-- Config -->
                    <div class="flex flex-col gap-4">
                        <div class="bg-white rounded-xl border border-gray-100 p-4">
                            <h3 class="text-sm font-bold mb-3">Output</h3>
                            <select class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm mb-2"><option>JSON</option><option>CSV</option><option>XLSX</option><option>Parquet</option><option>Database</option></select>
                        </div>
                        <div class="bg-white rounded-xl border border-gray-100 p-4">
                            <h3 class="text-sm font-bold mb-3">Schedule</h3>
                            <select class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm"><option>Once</option><option>Hourly</option><option>Daily</option><option>Weekly</option><option>Custom cron</option></select>
                        </div>
                        <button class="w-full bg-brand text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-brand-hover transition-colors shadow-sm">▶ Run Workflow</button>
                    </div>
                </div>
            </div>
            ` : ''}

            `}

            <!-- Detail Panel -->
            <voyant-detail-panel
                .open=${this.detailOpen}
                .title=${this.selectedTemplate?.name || ''}
                .subtitle=${`${this.selectedTemplate?.category || ''} · ${this.selectedTemplate?.engine || 'playwright'}`}
                @close=${() => { this.detailOpen = false; }}
            >
                ${this.selectedTemplate ? html`
                <div>
                    <p class="text-sm text-gray-500 mb-6">${this.selectedTemplate.description || 'No description'}</p>

                    <div class="grid grid-cols-2 gap-3 mb-6">
                        <div class="p-3 rounded-lg bg-gray-50"><div class="text-lg font-bold">${this.selectedTemplate.use_count || 0}</div><div class="text-xs text-gray-400">Runs</div></div>
                        <div class="p-3 rounded-lg bg-gray-50"><div class="text-lg font-bold">${Math.round((this.selectedTemplate.success_rate || 0) * 100)}%</div><div class="text-xs text-gray-400">Success</div></div>
                        <div class="p-3 rounded-lg bg-gray-50"><div class="text-sm font-semibold">${this.selectedTemplate.engine || 'playwright'}</div><div class="text-xs text-gray-400">Engine</div></div>
                        <div class="p-3 rounded-lg bg-gray-50"><div class="text-sm font-semibold">${this.selectedTemplate.status}</div><div class="text-xs text-gray-400">Status</div></div>
                    </div>

                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Site Pattern</h4>
                    <div class="px-3 py-2 rounded-lg bg-gray-50 font-mono text-xs mb-6">${this.selectedTemplate.site_pattern}</div>

                    ${this.selectedTemplate.parameters?.length ? html`
                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Parameters</h4>
                    <div class="flex flex-col gap-2 mb-6">
                        ${this.selectedTemplate.parameters.map(p => html`
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-semibold">${String(p.name || '')}</span>
                            <span class="text-xs text-gray-400">${String(p.type || 'string')}</span>
                        </div>`)}
                    </div>` : ''}

                    <button class="w-full bg-brand text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-brand-hover transition-colors shadow-sm"
                        @click=${() => { this.tab = 'visual'; this.targetUrl = this.selectedTemplate?.site_pattern || ''; this.detailOpen = false; }}>
                        ▶ Run Template
                    </button>
                </div>
                ` : ''}
            </voyant-detail-panel>
        </main>`;
    }
}
