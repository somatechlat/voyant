import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

interface ElementInfo {
    tag: string;
    text: string;
    selector: string;
    x: number;
    y: number;
    width: number;
    height: number;
    is_clickable: boolean;
    is_input: boolean;
    is_link: boolean;
}

interface DetectedList {
    name: string;
    selector: string;
    item_count: number;
    fields: Array<{ name: string; selector: string; type: string }>;
    sample_data: Array<Record<string, string>>;
}

interface DetectedPagination {
    type: string;
    selector: string;
}

interface DetectedForm {
    selector: string;
    inputs: Array<{ name: string; selector: string; type: string }>;
    submit_selector: string;
}

interface DetectedData {
    lists: DetectedList[];
    tables: Array<{ name: string; headers: string[]; row_count: number; sample_rows: string[][] }>;
    pagination: DetectedPagination[];
    forms: DetectedForm[];
    load_more: { has_load_more: boolean; selector: string; has_infinite_scroll: boolean };
}

@customElement('voyant-browser-canvas')
export class VoyantBrowserCanvas extends LitElement {
    @property({ type: String }) url = '';
    @property({ type: String }) mode: 'browse' | 'select' = 'browse';

    @state() private connected = false;
    @state() private loading = false;
    @state() private screenshot = '';
    @state() private elements: ElementInfo[] = [];
    @state() private hoveredElement: ElementInfo | null = null;
    @state() private detected: DetectedData | null = null;
    @state() private pageUrl = '';
    @state() private pageTitle = '';
    @state() private scrollY = 0;
    @state() private pageHeight = 0;
    @state() private viewportHeight = 800;
    @state() private extractedData: Record<string, unknown> = {};

    private ws: WebSocket | null = null;
    private canvas: HTMLCanvasElement | null = null;
    private ctx: CanvasRenderingContext2D | null = null;
    private img: HTMLImageElement = new Image();

    createRenderRoot() { return this; }

    connectedCallback() {
        super.connectedCallback();
        this._connect();
    }

    disconnectedCallback() {
        this.ws?.close();
        super.disconnectedCallback();
    }

    private _connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/scraper/`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.connected = true;
            this._send({ action: 'start' });
            if (this.url) {
                this._send({ action: 'navigate', url: this.url });
            }
        };

        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            this._handleMessage(msg);
        };

        this.ws.onclose = () => {
            this.connected = false;
        };

        this.ws.onerror = () => {
            this.connected = false;
        };
    }

    private _send(data: Record<string, unknown>) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    private _handleMessage(msg: Record<string, unknown>) {
        switch (msg.type) {
            case 'page_state':
                this._updatePageState(msg.data as Record<string, unknown>);
                break;
            case 'detected':
                this.detected = msg.data as DetectedData;
                break;
            case 'hover':
                break;
            case 'extracted':
                this.extractedData = msg.data as Record<string, unknown>;
                break;
            case 'error':
                console.error('Scraper error:', msg.message);
                this.loading = false;
                break;
            case 'connected':
                this.connected = true;
                break;
        }
    }

    private _updatePageState(data: Record<string, unknown>) {
        this.screenshot = data.screenshot as string;
        this.elements = (data.elements as ElementInfo[]) || [];
        this.pageUrl = data.url as string;
        this.pageTitle = data.title as string;
        this.scrollY = data.scroll_y as number;
        this.pageHeight = data.page_height as number;
        this.viewportHeight = data.viewport_height as number;
        this.loading = false;

        this.img.onload = () => {
            this._drawCanvas();
        };
        this.img.src = `data:image/png;base64,${this.screenshot}`;
    }

    private _drawCanvas() {
        if (!this.canvas || !this.ctx) return;

        const dpr = window.devicePixelRatio || 1;
        const displayWidth = this.canvas.clientWidth;
        const displayHeight = this.canvas.clientHeight;
        this.canvas.width = displayWidth * dpr;
        this.canvas.height = displayHeight * dpr;
        this.ctx.scale(dpr, dpr);

        // Draw screenshot
        this.ctx.drawImage(this.img, 0, 0, displayWidth, displayHeight);

        // Draw element overlays in select mode
        if (this.mode === 'select') {
            const scaleX = displayWidth / (this.img.naturalWidth || 1280);
            const scaleY = displayHeight / (this.img.naturalHeight || 800);

            for (const el of this.elements) {
                const x = el.x * scaleX;
                const y = (el.y - this.scrollY) * scaleY;
                const w = el.width * scaleX;
                const h = el.height * scaleY;

                if (y + h < 0 || y > displayHeight) continue;
                if (w < 2 || h < 2) continue;

                // Highlight interactive elements
                this.ctx.strokeStyle = el.is_clickable ? 'rgba(255,77,0,0.4)' : 'rgba(59,130,246,0.2)';
                this.ctx.lineWidth = 1;
                this.ctx.strokeRect(x, y, w, h);

                if (el === this.hoveredElement) {
                    this.ctx.fillStyle = 'rgba(255,77,0,0.15)';
                    this.ctx.fillRect(x, y, w, h);
                }
            }
        }
    }

    private _onCanvasClick(e: MouseEvent) {
        if (!this.canvas) return;
        const rect = this.canvas.getBoundingClientRect();
        const displayX = e.clientX - rect.left;
        const displayY = e.clientY - rect.top;

        const scaleX = (this.img.naturalWidth || 1280) / this.canvas.clientWidth;
        const scaleY = (this.img.naturalHeight || 800) / this.canvas.clientHeight;

        const pageX = Math.round(displayX * scaleX);
        const pageY = Math.round(displayY * scaleY + this.scrollY);

        if (this.mode === 'select') {
            // Find element under cursor
            const el = this._findElementAt(pageX, pageY);
            if (el) {
                this.dispatchEvent(new CustomEvent('element-click', { detail: el }));
            }
        } else {
            this.loading = true;
            this._send({ action: 'click', x: pageX, y: pageY });
        }
    }

    private _onCanvasMouseMove(e: MouseEvent) {
        if (!this.canvas || this.mode !== 'select') return;
        const rect = this.canvas.getBoundingClientRect();
        const displayX = e.clientX - rect.left;
        const displayY = e.clientY - rect.top;

        const scaleX = (this.img.naturalWidth || 1280) / this.canvas.clientWidth;
        const scaleY = (this.img.naturalHeight || 800) / this.canvas.clientHeight;

        const pageX = Math.round(displayX * scaleX);
        const pageY = Math.round(displayY * scaleY + this.scrollY);

        const el = this._findElementAt(pageX, pageY);
        if (el !== this.hoveredElement) {
            this.hoveredElement = el;
            this._drawCanvas();
            this.canvas.style.cursor = el ? 'pointer' : 'default';
        }
    }

    private _findElementAt(x: number, y: number): ElementInfo | null {
        for (const el of this.elements) {
            if (x >= el.x && x <= el.x + el.width && y >= el.y && y <= el.y + el.height) {
                return el;
            }
        }
        return null;
    }

    navigateTo(url: string) {
        this.loading = true;
        this.url = url;
        this._send({ action: 'navigate', url });
    }

    scroll(direction: 'up' | 'down' = 'down') {
        this._send({ action: 'scroll', direction, amount: 500 });
    }

    goBack() {
        this.loading = true;
        this._send({ action: 'back' });
    }

    extract(selectors: Record<string, string>) {
        this._send({ action: 'extract', selectors });
    }

    firstUpdated() {
        this.canvas = this.renderRoot.querySelector('canvas');
        if (this.canvas) {
            this.ctx = this.canvas.getContext('2d');
        }
    }

    render() {
        return html`
            <div style="display:flex;flex-direction:column;height:100%;font-family:Inter,system-ui,sans-serif">
                <!-- URL Bar -->
                <div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#FAFAFA;border-bottom:1px solid #E5E7EB">
                    <div style="display:flex;gap:4px">
                        <button class="nav-btn" @click=${this.goBack} title="Back" style="width:28px;height:28px;border-radius:6px;border:1px solid #E5E7EB;background:white;cursor:pointer;font-size:12px">←</button>
                        <button class="nav-btn" @click=${() => this.scroll('up')} title="Scroll up" style="width:28px;height:28px;border-radius:6px;border:1px solid #E5E7EB;background:white;cursor:pointer;font-size:12px">↑</button>
                        <button class="nav-btn" @click=${() => this.scroll('down')} title="Scroll down" style="width:28px;height:28px;border-radius:6px;border:1px solid #E5E7EB;background:white;cursor:pointer;font-size:12px">↓</button>
                    </div>
                    <div style="flex:1;display:flex;align-items:center;gap:8px;padding:4px 12px;border-radius:8px;border:1px solid #E5E7EB;background:white">
                        <span style="color:#9CA3AF;font-size:12px">🔒</span>
                        <input style="flex:1;border:none;outline:none;font-size:12px;font-family:JetBrains Mono,monospace;color:#050505"
                            placeholder="Enter URL..." .value=${this.pageUrl || this.url}
                            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter') this.navigateTo((e.target as HTMLInputElement).value); }}>
                    </div>
                    <div style="display:flex;gap:4px">
                        <button style="padding:4px 12px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;transition:all 120ms;border:1px solid ${this.mode === 'browse' ? '#FF4D00' : '#E5E7EB'};background:${this.mode === 'browse' ? '#FF4D00' : 'white'};color:${this.mode === 'browse' ? 'white' : '#6B7280'}"
                            @click=${() => { this.mode = 'browse'; this._drawCanvas(); }}>Browse</button>
                        <button style="padding:4px 12px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;transition:all 120ms;border:1px solid ${this.mode === 'select' ? '#FF4D00' : '#E5E7EB'};background:${this.mode === 'select' ? '#FF4D00' : 'white'};color:${this.mode === 'select' ? 'white' : '#6B7280'}"
                            @click=${() => { this.mode = 'select'; this._drawCanvas(); }}>🎯 Select</button>
                    </div>
                    <span style="font-size:10px;color:${this.connected ? '#22C55E' : '#EF4444'}">${this.connected ? '● Connected' : '○ Disconnected'}</span>
                </div>

                <!-- Browser Viewport -->
                <div style="flex:1;position:relative;overflow:hidden;background:#F5F5F5">
                    ${this.loading ? html`
                    <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.8);z-index:10">
                        <div style="font-size:13px;color:#6B7280">Loading...</div>
                    </div>` : ''}

                    ${this.screenshot ? html`
                    <canvas style="width:100%;height:100%;cursor:${this.mode === 'select' ? 'crosshair' : 'default'}"
                        @click=${this._onCanvasClick}
                        @mousemove=${this._onCanvasMouseMove}></canvas>
                    ` : html`
                    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:16px">
                        <div style="font-size:48px;opacity:0.15">🌐</div>
                        <div style="font-size:14px;color:#9CA3AF">Enter a URL above to load the page</div>
                        <div style="display:flex;gap:8px">
                            <button style="padding:6px 16px;border-radius:8px;border:1px solid #E5E7EB;background:white;font-size:12px;cursor:pointer"
                                @click=${() => this.navigateTo('https://xtrim.com.ec')}>xtrim.com.ec</button>
                            <button style="padding:6px 16px;border-radius:8px;border:1px solid #E5E7EB;background:white;font-size:12px;cursor:pointer"
                                @click=${() => this.navigateTo('https://news.ycombinator.com')}>Hacker News</button>
                        </div>
                    </div>
                    `}

                    <!-- Hover tooltip -->
                    ${this.hoveredElement && this.mode === 'select' ? html`
                    <div style="position:absolute;top:8px;left:8px;padding:6px 10px;border-radius:6px;background:#141414;color:#FAFAFA;font-size:11px;z-index:20;pointer-events:none;max-width:300px">
                        <div style="font-weight:600">${this.hoveredElement.tag} ${this.hoveredElement.selector}</div>
                        ${this.hoveredElement.text ? html`<div style="color:#9CA3AF;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:280px">${this.hoveredElement.text.slice(0, 80)}</div>` : ''}
                    </div>` : ''}
                </div>
            </div>
        `;
    }
}
