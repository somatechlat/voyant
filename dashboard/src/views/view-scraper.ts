import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

interface ScrapeResult {
    job_id: string;
    status: string;
    pages_fetched: number;
    bytes_processed: number;
    artifact_count: number;
    error_count: number;
    created_at: string;
}

interface SelectorDef {
    name: string;
    selector: string;
    type: 'css' | 'xpath';
}

@customElement('view-scraper')
export class ViewScraper extends LitElement {
    // Tab state
    @state() tab: 'jobs' | 'new' | 'extract' | 'ocr' | 'pdf' | 'fetch' = 'jobs';

    // Jobs list
    @state() jobs: ScrapeResult[] = [];
    @state() loading = true;

    // New scrape job
    @state() urls = '';
    @state() engine = 'playwright';
    @state() scroll = false;
    @state() timeout = 30;
    @state() waitSelector = '';
    @state() captureJson = false;
    @state() blockResources = true;
    @state() submitting = false;
    @state() submitResult = '';

    // Extract
    @state() extractHtml = '';
    @state() extractSelectors: SelectorDef[] = [{ name: 'title', selector: 'h1', type: 'css' }];
    @state() extractResult: Record<string, unknown> | null = null;

    // Fetch preview
    @state() fetchUrl = '';
    @state() fetchResult: Record<string, unknown> | null = null;

    // OCR
    @state() ocrUrl = '';
    @state() ocrResult: Record<string, unknown> | null = null;

    // PDF
    @state() pdfUrl = '';
    @state() pdfResult: Record<string, unknown> | null = null;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadJobs();
    }

    async loadJobs() {
        this.loading = true;
        try { this.jobs = await api.get<ScrapeResult[]>('/admin/scraper/jobs?limit=100'); }
        catch { this.jobs = []; }
        finally { this.loading = false; }
    }

    async startScrape() {
        const urlList = this.urls.split('\n').map(u => u.trim()).filter(Boolean);
        if (urlList.length === 0) return;
        this.submitting = true;
        this.submitResult = '';
        try {
            const res = await api.post<{ job_id: string; status: string }>('/v1/scrape/start', {
                urls: urlList,
                options: {
                    engine: this.engine,
                    scroll: this.scroll,
                    timeout: this.timeout,
                    wait_for: this.waitSelector || undefined,
                    capture_json: this.captureJson,
                    block_resources: this.blockResources,
                },
            });
            this.submitResult = `Job started: ${res.job_id}`;
            this.tab = 'jobs';
            await this.loadJobs();
        } catch (e: unknown) {
            this.submitResult = `Error: ${e instanceof Error ? e.message : 'Failed'}`;
        } finally { this.submitting = false; }
    }

    async extractData() {
        if (!this.extractHtml.trim()) return;
        const selectors: Record<string, string> = {};
        for (const s of this.extractSelectors) {
            if (s.name && s.selector) selectors[s.name] = s.selector;
        }
        try {
            this.extractResult = await api.post('/v1/scrape/extract', { html: this.extractHtml, selectors });
        } catch (e: unknown) {
            this.extractResult = { error: e instanceof Error ? e.message : 'Failed' };
        }
    }

    async fetchPage() {
        if (!this.fetchUrl.trim()) return;
        this.fetchResult = null;
        try {
            this.fetchResult = await api.post('/v1/scrape/fetch', {
                url: this.fetchUrl,
                engine: this.engine,
                timeout: this.timeout,
                block_resources: this.blockResources,
                capture_json: this.captureJson,
            });
        } catch (e: unknown) {
            this.fetchResult = { error: e instanceof Error ? e.message : 'Failed' };
        }
    }

    async processOcr() {
        if (!this.ocrUrl.trim()) return;
        try { this.ocrResult = await api.post('/v1/scrape/ocr', { image_url: this.ocrUrl, language: 'spa+eng' }); }
        catch (e: unknown) { this.ocrResult = { error: e instanceof Error ? e.message : 'Failed' }; }
    }

    async parsePdf() {
        if (!this.pdfUrl.trim()) return;
        try { this.pdfResult = await api.post('/v1/scrape/parse_pdf', { pdf_url: this.pdfUrl, extract_tables: true }); }
        catch (e: unknown) { this.pdfResult = { error: e instanceof Error ? e.message : 'Failed' }; }
    }

    addSelector() {
        this.extractSelectors = [...this.extractSelectors, { name: '', selector: '', type: 'css' }];
    }

    removeSelector(i: number) {
        this.extractSelectors = this.extractSelectors.filter((_, idx) => idx !== i);
    }

    private statusColor(s: string) {
        const m: Record<string, string> = { completed: 'bg-green-50 text-green-700', running: 'bg-blue-50 text-blue-700', failed: 'bg-red-50 text-red-700', cancelled: 'bg-gray-50 text-gray-500' };
        return m[s] || 'bg-amber-50 text-amber-700';
    }

    render() {
        const tabs = [
            { id: 'jobs', label: 'Jobs' },
            { id: 'new', label: 'New Scrape' },
            { id: 'fetch', label: 'Fetch Page' },
            { id: 'extract', label: 'Extract Data' },
            { id: 'ocr', label: 'OCR' },
            { id: 'pdf', label: 'Parse PDF' },
        ];

        return html`
        <saas-sidebar currentPath="/admin/scraper"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8">
            <h1 class="text-2xl font-black font-display tracking-tight mb-6">Scraper</h1>

            <!-- Tab bar -->
            <div class="flex gap-1 mb-6 bg-white rounded-lg p-1 border border-gray-100 w-fit">
                ${tabs.map(t => html`
                <button class="px-4 py-2 text-sm font-semibold rounded-md transition-colors ${this.tab === t.id ? 'bg-brand text-white' : 'text-gray-500 hover:text-ink'}" @click=${() => { this.tab = t.id as typeof this.tab; }}>${t.label}</button>`)}
            </div>

            <!-- Jobs Tab -->
            ${this.tab === 'jobs' ? html`
            <div class="flex items-center justify-between mb-4">
                <span class="text-sm text-gray-400">${this.jobs.length} jobs</span>
                <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50" @click=${() => this.loadJobs()}>Refresh</button>
            </div>
            ${this.loading ? html`<div class="text-center text-gray-400 py-16">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <table class="w-full text-sm">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-400 uppercase tracking-wider">
                        <th class="px-5 py-3">Job ID</th><th class="px-5 py-3">Status</th><th class="px-5 py-3">Pages</th><th class="px-5 py-3">Bytes</th><th class="px-5 py-3">Artifacts</th><th class="px-5 py-3">Errors</th><th class="px-5 py-3">Created</th>
                    </tr></thead>
                    <tbody>
                    ${this.jobs.map(j => html`
                        <tr class="border-b border-gray-50 hover:bg-gray-50">
                            <td class="px-5 py-3 font-mono text-xs">${j.job_id.slice(0, 8)}</td>
                            <td class="px-5 py-3"><span class="px-2 py-0.5 text-xs rounded ${this.statusColor(j.status)}">${j.status}</span></td>
                            <td class="px-5 py-3">${j.pages_fetched}</td>
                            <td class="px-5 py-3">${((j.bytes_processed || 0) / 1024).toFixed(1)}KB</td>
                            <td class="px-5 py-3">${j.artifact_count}</td>
                            <td class="px-5 py-3 ${j.error_count ? 'text-red-600' : ''}">${j.error_count}</td>
                            <td class="px-5 py-3 text-gray-400 text-xs">${new Date(j.created_at).toLocaleString()}</td>
                        </tr>`)}
                    </tbody>
                </table>
                ${this.jobs.length === 0 ? html`<div class="text-center text-gray-400 py-12">No scraper jobs</div>` : ''}
            </div>`}` : ''}

            <!-- New Scrape Tab -->
            ${this.tab === 'new' ? html`
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="bg-white rounded-xl border border-gray-100 p-6">
                    <h3 class="text-sm font-semibold text-gray-500 mb-4">URLs (one per line)</h3>
                    <textarea class="w-full h-40 p-4 border border-gray-200 rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand" placeholder="https://example.com&#10;https://example.com/page2" .value=${this.urls} @input=${(e: Event) => { this.urls = (e.target as HTMLTextAreaElement).value; }}></textarea>

                    <div class="grid grid-cols-2 gap-4 mt-4">
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">Engine</label>
                            <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white" .value=${this.engine} @change=${(e: Event) => { this.engine = (e.target as HTMLSelectElement).value; }}>
                                <option value="playwright">Playwright (JS)</option>
                                <option value="httpx">HTTPX (Fast)</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">Timeout (s)</label>
                            <input type="number" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" .value=${String(this.timeout)} @input=${(e: Event) => { this.timeout = parseInt((e.target as HTMLInputElement).value) || 30; }} />
                        </div>
                    </div>

                    <div class="mt-4">
                        <label class="block text-xs font-medium text-gray-500 mb-1">Wait for selector</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono" placeholder=".content-loaded" .value=${this.waitSelector} @input=${(e: Event) => { this.waitSelector = (e.target as HTMLInputElement).value; }} />
                    </div>

                    <div class="flex gap-4 mt-4">
                        <label class="flex items-center gap-2 text-sm text-gray-600">
                            <input type="checkbox" .checked=${this.scroll} @change=${(e: Event) => { this.scroll = (e.target as HTMLInputElement).checked; }} /> Scroll
                        </label>
                        <label class="flex items-center gap-2 text-sm text-gray-600">
                            <input type="checkbox" .checked=${this.captureJson} @change=${(e: Event) => { this.captureJson = (e.target as HTMLInputElement).checked; }} /> Capture JSON/XHR
                        </label>
                        <label class="flex items-center gap-2 text-sm text-gray-600">
                            <input type="checkbox" .checked=${this.blockResources} @change=${(e: Event) => { this.blockResources = (e.target as HTMLInputElement).checked; }} /> Block images/fonts
                        </label>
                    </div>

                    <button class="mt-6 w-full py-3 text-sm font-bold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.submitting ? 'opacity-50' : ''}" ?disabled=${this.submitting} @click=${() => this.startScrape()}>
                        ${this.submitting ? 'Starting...' : 'Start Scrape Job'}
                    </button>
                    ${this.submitResult ? html`<div class="mt-3 text-sm ${this.submitResult.startsWith('Error') ? 'text-red-600' : 'text-green-600'}">${this.submitResult}</div>` : ''}
                </div>
                <div class="bg-white rounded-xl border border-gray-100 p-6">
                    <h3 class="text-sm font-semibold text-gray-500 mb-4">Quick Options</h3>
                    <div class="space-y-3">
                        <div class="p-4 border border-gray-100 rounded-lg hover:border-brand transition-colors cursor-pointer" @click=${() => { this.engine = 'playwright'; this.scroll = true; this.blockResources = true; this.captureJson = true; }}>
                            <div class="font-semibold text-sm">Full Page Capture</div>
                            <div class="text-xs text-gray-400">Playwright + scroll + XHR capture + block resources</div>
                        </div>
                        <div class="p-4 border border-gray-100 rounded-lg hover:border-brand transition-colors cursor-pointer" @click=${() => { this.engine = 'httpx'; this.scroll = false; this.blockResources = false; this.captureJson = false; }}>
                            <div class="font-semibold text-sm">Fast Fetch</div>
                            <div class="text-xs text-gray-400">HTTPX — no JS rendering, fastest</div>
                        </div>
                        <div class="p-4 border border-gray-100 rounded-lg hover:border-brand transition-colors cursor-pointer" @click=${() => { this.engine = 'playwright'; this.scroll = true; this.blockResources = false; this.captureJson = false; }}>
                            <div class="font-semibold text-sm">Visual Capture</div>
                            <div class="text-xs text-gray-400">Playwright + scroll, keep images</div>
                        </div>
                    </div>
                </div>
            </div>` : ''}

            <!-- Fetch Page Tab -->
            ${this.tab === 'fetch' ? html`
            <div class="bg-white rounded-xl border border-gray-100 p-6 mb-6">
                <h3 class="text-sm font-semibold text-gray-500 mb-4">Fetch & Preview</h3>
                <div class="flex gap-2">
                    <input type="text" class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono focus:ring-2 focus:ring-brand focus:outline-none" placeholder="https://example.com" .value=${this.fetchUrl} @input=${(e: Event) => { this.fetchUrl = (e.target as HTMLInputElement).value; }} @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter') this.fetchPage(); }} />
                    <button class="px-5 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors" @click=${() => this.fetchPage()}>Fetch</button>
                </div>
            </div>
            ${this.fetchResult ? html`
            <div class="bg-white rounded-xl border border-gray-100 p-6">
                <h3 class="text-sm font-semibold text-gray-500 mb-3">Result</h3>
                <pre class="p-4 bg-gray-50 rounded-lg text-xs font-mono overflow-auto max-h-96">${JSON.stringify(this.fetchResult, null, 2)}</pre>
            </div>` : ''}` : ''}

            <!-- Extract Data Tab -->
            ${this.tab === 'extract' ? html`
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="bg-white rounded-xl border border-gray-100 p-6">
                    <h3 class="text-sm font-semibold text-gray-500 mb-4">HTML Input</h3>
                    <textarea class="w-full h-48 p-4 border border-gray-200 rounded-lg font-mono text-xs resize-none focus:ring-2 focus:ring-brand focus:outline-none" placeholder="Paste HTML here..." .value=${this.extractHtml} @input=${(e: Event) => { this.extractHtml = (e.target as HTMLTextAreaElement).value; }}></textarea>

                    <h4 class="text-sm font-semibold text-gray-500 mt-4 mb-2">Selectors</h4>
                    ${this.extractSelectors.map((s, i) => html`
                    <div class="flex gap-2 mb-2">
                        <input type="text" class="w-24 px-2 py-1.5 text-xs border border-gray-200 rounded-lg" placeholder="name" .value=${s.name} @input=${(e: Event) => { this.extractSelectors[i].name = (e.target as HTMLInputElement).value; }} />
                        <select class="w-20 px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white" .value=${s.type} @change=${(e: Event) => { this.extractSelectors[i].type = (e.target as HTMLSelectElement).value as 'css' | 'xpath'; }}>
                            <option value="css">CSS</option><option value="xpath">XPath</option>
                        </select>
                        <input type="text" class="flex-1 px-2 py-1.5 text-xs border border-gray-200 rounded-lg font-mono" placeholder="selector" .value=${s.selector} @input=${(e: Event) => { this.extractSelectors[i].selector = (e.target as HTMLInputElement).value; }} />
                        <button class="px-2 text-red-400 hover:text-red-600" @click=${() => this.removeSelector(i)}>✕</button>
                    </div>`)}
                    <button class="text-xs text-brand font-semibold hover:underline mt-1" @click=${() => this.addSelector()}>+ Add selector</button>

                    <button class="mt-4 w-full py-2.5 text-sm font-bold bg-brand text-white rounded-lg hover:bg-black transition-colors" @click=${() => this.extractData()}>Extract</button>
                </div>
                <div class="bg-white rounded-xl border border-gray-100 p-6">
                    <h3 class="text-sm font-semibold text-gray-500 mb-3">Extracted Data</h3>
                    ${this.extractResult ? html`
                    <pre class="p-4 bg-gray-50 rounded-lg text-xs font-mono overflow-auto max-h-96">${JSON.stringify(this.extractResult, null, 2)}</pre>` : html`
                    <div class="text-center text-gray-400 py-16">Paste HTML and configure selectors to extract data</div>`}
                </div>
            </div>` : ''}

            <!-- OCR Tab -->
            ${this.tab === 'ocr' ? html`
            <div class="bg-white rounded-xl border border-gray-100 p-6 mb-6">
                <h3 class="text-sm font-semibold text-gray-500 mb-4">OCR — Extract Text from Image</h3>
                <div class="flex gap-2">
                    <input type="text" class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono focus:ring-2 focus:ring-brand focus:outline-none" placeholder="https://example.com/image.png" .value=${this.ocrUrl} @input=${(e: Event) => { this.ocrUrl = (e.target as HTMLInputElement).value; }} />
                    <button class="px-5 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors" @click=${() => this.processOcr()}>Process OCR</button>
                </div>
            </div>
            ${this.ocrResult ? html`
            <div class="bg-white rounded-xl border border-gray-100 p-6">
                <pre class="p-4 bg-gray-50 rounded-lg text-xs font-mono overflow-auto max-h-96">${JSON.stringify(this.ocrResult, null, 2)}</pre>
            </div>` : ''}` : ''}

            <!-- PDF Tab -->
            ${this.tab === 'pdf' ? html`
            <div class="bg-white rounded-xl border border-gray-100 p-6 mb-6">
                <h3 class="text-sm font-semibold text-gray-500 mb-4">Parse PDF</h3>
                <div class="flex gap-2">
                    <input type="text" class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono focus:ring-2 focus:ring-brand focus:outline-none" placeholder="https://example.com/document.pdf" .value=${this.pdfUrl} @input=${(e: Event) => { this.pdfUrl = (e.target as HTMLInputElement).value; }} />
                    <button class="px-5 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors" @click=${() => this.parsePdf()}>Parse PDF</button>
                </div>
            </div>
            ${this.pdfResult ? html`
            <div class="bg-white rounded-xl border border-gray-100 p-6">
                <pre class="p-4 bg-gray-50 rounded-lg text-xs font-mono overflow-auto max-h-96">${JSON.stringify(this.pdfResult, null, 2)}</pre>
            </div>` : ''}` : ''}

        </main>`;
    }
}
