import { LitElement, html, nothing, css } from 'lit';
import { customElement, state, property } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

/* ──────────────────────────────────────────────────────────────────────
   Interfaces
   ────────────────────────────────────────────────────────────────────── */

type WidgetType = 'chart' | 'table' | 'kpi' | 'text' | 'iframe';

interface Widget {
    id: string;
    type: WidgetType;
    title: string;
    config: Record<string, unknown>;
    position: { x: number; y: number; w: number; h: number };
}

interface Dashboard {
    id: string;
    name: string;
    description: string;
    widget_count: number;
    widgets: Widget[];
    created_at: string;
    updated_at: string;
}

interface WidgetPaletteItem {
    type: WidgetType;
    label: string;
    icon: string;
    defaultW: number;
    defaultH: number;
}

/* ──────────────────────────────────────────────────────────────────────
   Constants
   ────────────────────────────────────────────────────────────────────── */

const GRID_COLUMNS = 12;
const CELL_HEIGHT = 80; // px per grid row
const WIDGET_PALETTE: WidgetPaletteItem[] = [
    { type: 'chart',  label: 'Chart',  icon: 'M3 3v18h18M7 16l4-4 4 4 5-6', defaultW: 6, defaultH: 3 },
    { type: 'table',  label: 'Table',  icon: 'M3 3h18v18H3V3zm0 6h18M3 12h18M3 17h18M9 3v18M15 3v18', defaultW: 6, defaultH: 4 },
    { type: 'kpi',    label: 'KPI',    icon: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5', defaultW: 3, defaultH: 2 },
    { type: 'text',   label: 'Text',   icon: 'M4 7V4h16v3M9 20h6M12 4v16', defaultW: 4, defaultH: 2 },
    { type: 'iframe', label: 'Iframe', icon: 'M2 3h20v18H2V3zm5 3v12M17 6v12M7 9h10M7 15h10', defaultW: 6, defaultH: 4 },
];

/* ──────────────────────────────────────────────────────────────────────
   View Component
   ────────────────────────────────────────────────────────────────────── */

@customElement('view-dashboards')
export class ViewDashboards extends LitElement {
    @state() dashboards: Dashboard[] = [];
    @state() loading = true;

    // Create modal
    @state() showCreate = false;
    @state() createName = '';
    @state() createDescription = '';
    @state() creating = false;

    // Detail / Editor view
    @state() selectedDashboard: Dashboard | null = null;
    @state() detailLoading = false;
    @state() editMode = false;

    // Widget editor state
    @state() showWidgetPalette = false;
    @state() editingWidget: Widget | null = null;
    @state() widgetFormTitle = '';
    @state() widgetFormConfig = '{}';
    @state() dragSource: { type: WidgetType; w: number; h: number } | null = null;

    // WebSocket auto-refresh
    @state() wsConnected = false;
    @state() lastRefresh = '';
    private ws: WebSocket | null = null;
    private wsRetryTimer: ReturnType<typeof setTimeout> | null = null;

    // Export state
    @state() exporting = false;

    createRenderRoot() { return this; }

    // ── Lifecycle ────────────────────────────────────────────────────────

    async connectedCallback() {
        super.connectedCallback();
        await this.load();
        this.connectWebSocket();
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        this.disconnectWebSocket();
    }

    // ── Data Loading ─────────────────────────────────────────────────────

    async load() {
        this.loading = true;
        try {
            this.dashboards = await api.get<Dashboard[]>('/v1/dashboards');
        } catch {
            this.dashboards = [];
        } finally {
            this.loading = false;
        }
    }

    async createDashboard() {
        if (!this.createName.trim()) return;
        this.creating = true;
        try {
            await api.post('/v1/dashboards', {
                name: this.createName,
                description: this.createDescription,
            });
            this.showCreate = false;
            this.createName = '';
            this.createDescription = '';
            await this.load();
        } catch (e: unknown) {
            console.error('Failed to create dashboard:', e);
        } finally {
            this.creating = false;
        }
    }

    async viewDetail(dashboard: Dashboard) {
        this.detailLoading = true;
        this.editMode = false;
        this.selectedDashboard = dashboard;
        try {
            const detail = await api.get<Dashboard>(`/v1/dashboards/${dashboard.id}`);
            this.selectedDashboard = detail;
        } catch {
            // Use the list item data as fallback
        } finally {
            this.detailLoading = false;
        }
    }

    async deleteDashboard(id: string) {
        if (!confirm('Delete this dashboard? This cannot be undone.')) return;
        try {
            await api.del(`/v1/dashboards/${id}`);
            this.selectedDashboard = null;
            await this.load();
        } catch (e: unknown) {
            console.error('Failed to delete dashboard:', e);
        }
    }

    // ── WebSocket Auto-Refresh ───────────────────────────────────────────

    private connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/dashboards`;
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.wsConnected = true;
            };

            this.ws.onmessage = (event: MessageEvent) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'dashboard_update' || data.type === 'widget_update') {
                        this.lastRefresh = new Date().toLocaleTimeString();
                        this.load();
                        if (this.selectedDashboard && data.dashboard_id === this.selectedDashboard.id) {
                            this.viewDetail(this.selectedDashboard);
                        }
                    }
                } catch { /* ignore parse errors */ }
            };

            this.ws.onclose = () => {
                this.wsConnected = false;
                // Auto-reconnect after 5s
                this.wsRetryTimer = setTimeout(() => this.connectWebSocket(), 5000);
            };

            this.ws.onerror = () => {
                this.wsConnected = false;
            };
        } catch {
            // WebSocket not available — degrade gracefully
            this.wsConnected = false;
        }
    }

    private disconnectWebSocket() {
        if (this.wsRetryTimer) {
            clearTimeout(this.wsRetryTimer);
            this.wsRetryTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.wsConnected = false;
    }

    // ── Widget Grid: Drag & Drop ─────────────────────────────────────────

    private handlePaletteDragStart(e: DragEvent, item: WidgetPaletteItem) {
        if (!e.dataTransfer) return;
        this.dragSource = { type: item.type, w: item.defaultW, h: item.defaultH };
        e.dataTransfer.effectAllowed = 'copy';
        e.dataTransfer.setData('text/plain', item.type);
    }

    private handleGridDragOver(e: DragEvent) {
        e.preventDefault();
        if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
    }

    private handleGridDrop(e: DragEvent) {
        e.preventDefault();
        if (!this.dragSource || !this.selectedDashboard) return;

        const target = e.currentTarget as HTMLElement;
        const rect = target.getBoundingClientRect();
        const x = Math.floor(((e.clientX - rect.left) / rect.width) * GRID_COLUMNS);
        const clampedX = Math.max(0, Math.min(x, GRID_COLUMNS - this.dragSource.w));

        const newWidget: Widget = {
            id: `w_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
            type: this.dragSource.type,
            title: WIDGET_PALETTE.find(p => p.type === this.dragSource!.type)?.label || 'Widget',
            config: {},
            position: { x: clampedX, y: 0, w: this.dragSource.w, h: this.dragSource.h },
        };

        this.selectedDashboard.widgets = [...(this.selectedDashboard.widgets || []), newWidget];
        this.selectedDashboard.widget_count = this.selectedDashboard.widgets.length;
        this.saveWidgetLayout();
        this.dragSource = null;
    }

    private handleWidgetDragStart(e: DragEvent, widget: Widget, index: number) {
        if (!e.dataTransfer) return;
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('application/widget-index', String(index));
    }

    private handleWidgetDragOver(e: DragEvent) {
        e.preventDefault();
        if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
    }

    private handleWidgetDrop(e: DragEvent, targetIndex: number) {
        e.preventDefault();
        e.stopPropagation();
        if (!this.selectedDashboard) return;

        const srcIndexStr = e.dataTransfer?.getData('application/widget-index');
        if (srcIndexStr === undefined || srcIndexStr === null) return;
        const srcIndex = parseInt(srcIndexStr, 10);
        if (isNaN(srcIndex) || srcIndex === targetIndex) return;

        const widgets = [...(this.selectedDashboard.widgets || [])];
        const [moved] = widgets.splice(srcIndex, 1);
        widgets.splice(targetIndex, 0, moved);
        this.selectedDashboard.widgets = widgets;
        this.saveWidgetLayout();
    }

    private removeWidget(widgetId: string) {
        if (!this.selectedDashboard) return;
        this.selectedDashboard.widgets = (this.selectedDashboard.widgets || []).filter(w => w.id !== widgetId);
        this.selectedDashboard.widget_count = this.selectedDashboard.widgets.length;
        this.saveWidgetLayout();
    }

    private resizeWidget(widgetId: string, dw: number, dh: number) {
        if (!this.selectedDashboard) return;
        const widgets = this.selectedDashboard.widgets || [];
        const widget = widgets.find(w => w.id === widgetId);
        if (!widget) return;
        widget.position.w = Math.max(1, Math.min(GRID_COLUMNS, widget.position.w + dw));
        widget.position.h = Math.max(1, widget.position.h + dh);
        this.selectedDashboard.widgets = [...widgets];
        this.saveWidgetLayout();
    }

    private async saveWidgetLayout() {
        if (!this.selectedDashboard) return;
        try {
            await api.put(`/v1/dashboards/${this.selectedDashboard.id}`, {
                widgets: this.selectedDashboard.widgets,
            });
        } catch (e) {
            console.error('Failed to save widget layout:', e);
        }
    }

    // ── Widget Configuration ─────────────────────────────────────────────

    private openWidgetConfig(widget: Widget) {
        this.editingWidget = widget;
        this.widgetFormTitle = widget.title;
        this.widgetFormConfig = JSON.stringify(widget.config, null, 2);
    }

    private closeWidgetConfig() {
        this.editingWidget = null;
        this.widgetFormTitle = '';
        this.widgetFormConfig = '{}';
    }

    private saveWidgetConfig() {
        if (!this.editingWidget || !this.selectedDashboard) return;
        let parsedConfig: Record<string, unknown> = {};
        try {
            parsedConfig = JSON.parse(this.widgetFormConfig);
        } catch {
            alert('Invalid JSON in config');
            return;
        }

        const widgets = this.selectedDashboard.widgets || [];
        const idx = widgets.findIndex(w => w.id === this.editingWidget!.id);
        if (idx >= 0) {
            widgets[idx] = { ...widgets[idx], title: this.widgetFormTitle, config: parsedConfig };
            this.selectedDashboard.widgets = [...widgets];
            this.saveWidgetLayout();
        }
        this.closeWidgetConfig();
    }

    // ── Export ───────────────────────────────────────────────────────────

    private async exportDashboard(format: 'pdf' | 'png') {
        if (!this.selectedDashboard) return;
        this.exporting = true;
        try {
            const result = await api.post<{ download_url: string }>(
                `/v1/dashboards/${this.selectedDashboard.id}/export`,
                { format },
            );
            if (result.download_url) {
                window.open(result.download_url, '_blank');
            }
        } catch (e) {
            console.error(`Export to ${format.toUpperCase()} failed:`, e);
            alert(`Export to ${format.toUpperCase()} failed. Please try again.`);
        } finally {
            this.exporting = false;
        }
    }

    // ── Icons ────────────────────────────────────────────────────────────

    private widgetIcon(type: string): string {
        const item = WIDGET_PALETTE.find(p => p.type === type);
        return item?.icon || WIDGET_PALETTE[0].icon;
    }

    // ── Render ───────────────────────────────────────────────────────────

    render() {
        return html`
        <saas-sidebar currentPath="/admin/dashboards"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Dashboards management">
            ${this.selectedDashboard && this.editMode
                ? this.renderEditor()
                : this.renderList()}
        </main>`;
    }

    // ── List View ────────────────────────────────────────────────────────

    private renderList() {
        return html`
            <div class="flex items-center justify-between mb-6">
                <div class="flex items-center gap-3">
                    <h1 class="text-2xl font-black font-display tracking-tight">Dashboards</h1>
                    ${this.wsConnected
                        ? html`<span class="inline-flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                            <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>Live${this.lastRefresh ? ` · ${this.lastRefresh}` : ''}</span>`
                        : html`<span class="inline-flex items-center gap-1 text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                            <span class="w-1.5 h-1.5 rounded-full bg-gray-300"></span>Offline</span>`}
                </div>
                <div class="flex gap-2">
                    <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        aria-label="Refresh dashboards" @click=${() => this.load()}>Refresh</button>
                    <button class="px-4 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                        aria-expanded=${this.showCreate} aria-label="Create new dashboard"
                        @click=${() => { this.showCreate = !this.showCreate; }}>+ New Dashboard</button>
                </div>
            </div>

            <!-- Create Dashboard Modal -->
            ${this.showCreate ? html`
            <div class="bg-white rounded-xl border border-gray-100 p-6 mb-6">
                <h3 class="text-sm font-semibold text-gray-500 mb-4">Create New Dashboard</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Name *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            placeholder="My Dashboard" .value=${this.createName}
                            @input=${(e: Event) => { this.createName = (e.target as HTMLInputElement).value; }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Description</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            placeholder="Dashboard description" .value=${this.createDescription}
                            @input=${(e: Event) => { this.createDescription = (e.target as HTMLInputElement).value; }} />
                    </div>
                </div>
                <div class="flex justify-end gap-2">
                    <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        @click=${() => { this.showCreate = false; }}>Cancel</button>
                    <button class="px-4 py-2 text-sm font-bold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.creating ? 'opacity-50' : ''}"
                        ?disabled=${this.creating}
                        @click=${() => this.createDashboard()}>
                        ${this.creating ? 'Creating...' : 'Create Dashboard'}
                    </button>
                </div>
            </div>` : nothing}

            <!-- Dashboard Grid -->
            ${this.loading ? html`<div class="text-center text-gray-400 py-16" role="status" aria-live="polite">Loading...</div>` : html`
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" aria-live="polite">
                ${this.dashboards.length === 0
                    ? html`<div class="col-span-full text-center text-gray-400 py-16">No dashboards found. Create one to get started.</div>`
                    : this.dashboards.map(d => html`
                    <div class="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow cursor-pointer group"
                        role="button" tabindex="0" aria-label="Dashboard: ${d.name}"
                        @click=${() => this.viewDetail(d)} @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.viewDetail(d); } }}>
                        <div class="flex items-start justify-between mb-3">
                            <div class="h-10 w-10 rounded-lg bg-gray-100 flex items-center justify-center">
                                <svg class="h-5 w-5 text-gray-400" viewBox="0 0 24 24" fill="none"
                                    stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                                    <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
                                </svg>
                            </div>
                            <div class="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                                <button class="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50"
                                    aria-label="Delete dashboard ${d.name}"
                                    @click=${(e: Event) => { e.stopPropagation(); this.deleteDashboard(d.id); }}>Delete</button>
                            </div>
                        </div>
                        <h3 class="font-bold text-sm mb-1">${d.name}</h3>
                        ${d.description ? html`<p class="text-xs text-gray-400 mb-3 line-clamp-2">${d.description}</p>` : nothing}
                        <div class="flex items-center gap-3 text-xs text-gray-400">
                            <span>${d.widget_count || 0} widget${(d.widget_count || 0) !== 1 ? 's' : ''}</span>
                            <span>&middot;</span>
                            <span>${new Date(d.updated_at).toLocaleDateString()}</span>
                        </div>
                    </div>`)}
            </div>`}

            <!-- Dashboard Detail Panel -->
            ${this.selectedDashboard && !this.editMode ? this.renderDetailPanel() : nothing}
        `;
    }

    // ── Detail Panel ─────────────────────────────────────────────────────

    private renderDetailPanel() {
        const d = this.selectedDashboard!;
        return html`
        <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Dashboard detail: ${d.name}"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') { this.selectedDashboard = null; } }}>
            <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedDashboard = null; }}></div>
            <div class="relative w-[600px] bg-white h-full overflow-y-auto shadow-2xl border-l border-gray-200" tabindex="-1">
                <div class="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between z-10">
                    <h2 class="font-bold text-lg">${d.name}</h2>
                    <button class="text-gray-400 hover:text-ink" aria-label="Close"
                        @click=${() => { this.selectedDashboard = null; }}>&#10005;</button>
                </div>
                <div class="p-6 space-y-6">
                    ${d.description ? html`
                    <div>
                        <span class="text-xs text-gray-400">Description</span>
                        <p class="text-sm mt-1">${d.description}</p>
                    </div>` : nothing}

                    <div class="grid grid-cols-3 gap-4">
                        <div class="bg-gray-50 rounded-lg p-3 text-center">
                            <div class="text-lg font-bold">${d.widget_count || 0}</div>
                            <div class="text-xs text-gray-400">Widgets</div>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-3 text-center">
                            <div class="text-xs font-semibold">${new Date(d.created_at).toLocaleDateString()}</div>
                            <div class="text-xs text-gray-400">Created</div>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-3 text-center">
                            <div class="text-xs font-semibold">${new Date(d.updated_at).toLocaleDateString()}</div>
                            <div class="text-xs text-gray-400">Updated</div>
                        </div>
                    </div>

                    <!-- Widget Grid Preview -->
                    <div>
                        <h4 class="text-xs font-semibold text-gray-500 mb-3">Widgets</h4>
                        ${this.detailLoading
                            ? html`<div class="text-center text-gray-400 py-8">Loading widgets...</div>`
                            : (d.widgets || []).length === 0
                                ? html`
                                <div class="text-center py-8 bg-gray-50 rounded-lg">
                                    <div class="text-gray-400 text-sm mb-2">No widgets yet</div>
                                    <p class="text-xs text-gray-300">Open the editor to add widgets via drag & drop</p>
                                </div>`
                                : html`
                                <div class="grid grid-cols-2 gap-3">
                                    ${(d.widgets || []).map(w => html`
                                    <div class="bg-gray-50 rounded-lg p-4 border border-gray-100">
                                        <div class="flex items-center gap-2 mb-2">
                                            <svg class="h-4 w-4 text-gray-400" viewBox="0 0 24 24" fill="none"
                                                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                                <path d="${this.widgetIcon(w.type)}"/>
                                            </svg>
                                            <span class="text-sm font-semibold">${w.title}</span>
                                        </div>
                                        <span class="text-xs text-gray-400 px-1.5 py-0.5 bg-gray-200 rounded">${w.type}</span>
                                        <span class="text-xs text-gray-300 ml-2">${w.position.w}x${w.position.h}</span>
                                    </div>`)}
                                </div>`}
                    </div>

                    <!-- Actions -->
                    <div class="flex flex-wrap gap-2 pt-4 border-t border-gray-100">
                        <button class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                            @click=${() => { this.editMode = true; }}>
                            Open Editor
                        </button>
                        <button class="px-4 py-2 text-sm font-semibold border border-gray-200 rounded-lg bg-white hover:bg-gray-50 flex items-center gap-1.5 ${this.exporting ? 'opacity-50' : ''}"
                            ?disabled=${this.exporting}
                            @click=${() => this.exportDashboard('pdf')}>
                            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>
                            PDF
                        </button>
                        <button class="px-4 py-2 text-sm font-semibold border border-gray-200 rounded-lg bg-white hover:bg-gray-50 flex items-center gap-1.5 ${this.exporting ? 'opacity-50' : ''}"
                            ?disabled=${this.exporting}
                            @click=${() => this.exportDashboard('png')}>
                            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
                            PNG
                        </button>
                        <button class="px-4 py-2 text-sm font-semibold text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
                            @click=${() => { this.deleteDashboard(d.id); }}>
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    // ── Editor View (12-column grid + palette + config panel) ────────────

    private renderEditor() {
        const d = this.selectedDashboard!;
        return html`
            <!-- Editor Header -->
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                    <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        @click=${() => { this.editMode = false; }}>
                        &larr; Back
                    </button>
                    <h1 class="text-xl font-black font-display tracking-tight">${d.name}</h1>
                    ${this.wsConnected
                        ? html`<span class="inline-flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                            <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>Live</span>`
                        : nothing}
                </div>
                <div class="flex gap-2">
                    <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50 flex items-center gap-1.5"
                        @click=${() => { this.showWidgetPalette = !this.showWidgetPalette; }}>
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                        Widget Palette
                    </button>
                    <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50 flex items-center gap-1.5 ${this.exporting ? 'opacity-50' : ''}"
                        ?disabled=${this.exporting}
                        @click=${() => this.exportDashboard('pdf')}>PDF</button>
                    <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50 flex items-center gap-1.5 ${this.exporting ? 'opacity-50' : ''}"
                        ?disabled=${this.exporting}
                        @click=${() => this.exportDashboard('png')}>PNG</button>
                </div>
            </div>

            <div class="flex gap-4">
                <!-- Widget Palette Sidebar -->
                ${this.showWidgetPalette ? html`
                <div class="w-56 flex-shrink-0">
                    <div class="bg-white rounded-xl border border-gray-100 p-4 sticky top-4">
                        <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Widgets</h3>
                        <p class="text-xs text-gray-400 mb-3">Drag a widget onto the grid</p>
                        <div class="space-y-2">
                            ${WIDGET_PALETTE.map(item => html`
                            <div class="flex items-center gap-3 p-3 rounded-lg border border-gray-100 bg-gray-50 cursor-grab hover:border-brand hover:bg-brand/5 transition-colors"
                                draggable="true"
                                @dragstart=${(e: DragEvent) => this.handlePaletteDragStart(e, item)}>
                                <div class="h-8 w-8 rounded bg-white border border-gray-200 flex items-center justify-center flex-shrink-0">
                                    <svg class="h-4 w-4 text-gray-500" viewBox="0 0 24 24" fill="none"
                                        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="${item.icon}"/>
                                    </svg>
                                </div>
                                <div>
                                    <div class="text-sm font-semibold text-gray-700">${item.label}</div>
                                    <div class="text-xs text-gray-400">${item.defaultW}x${item.defaultH} default</div>
                                </div>
                            </div>`)}
                        </div>
                    </div>
                </div>` : nothing}

                <!-- 12-Column Grid -->
                <div class="flex-1 min-w-0">
                    <div class="bg-white rounded-xl border border-gray-100 p-4"
                        @dragover=${(e: DragEvent) => this.handleGridDragOver(e)}
                        @drop=${(e: DragEvent) => this.handleGridDrop(e)}>
                        <!-- Grid Header -->
                        <div class="flex items-center justify-between mb-3">
                            <div class="flex items-center gap-2">
                                <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                    Grid Layout
                                </h3>
                                <span class="text-xs text-gray-300">${GRID_COLUMNS}-column</span>
                            </div>
                            <span class="text-xs text-gray-400">${(d.widgets || []).length} widgets</span>
                        </div>

                        <!-- Column Guide -->
                        <div class="grid gap-1 mb-4" style="grid-template-columns: repeat(${GRID_COLUMNS}, 1fr);">
                            ${Array.from({ length: GRID_COLUMNS }, (_, i) => html`
                            <div class="h-4 bg-gray-50 rounded text-center text-[9px] text-gray-300 leading-4">${i + 1}</div>`)}
                        </div>

                        <!-- Widget Grid -->
                        ${(d.widgets || []).length === 0
                            ? html`
                            <div class="text-center py-16 border-2 border-dashed border-gray-200 rounded-lg">
                                <svg class="h-8 w-8 text-gray-300 mx-auto mb-2" viewBox="0 0 24 24" fill="none"
                                    stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M12 5v14M5 12h14"/>
                                </svg>
                                <p class="text-sm text-gray-400">Drag widgets from the palette to build your dashboard</p>
                                <p class="text-xs text-gray-300 mt-1">Or click "Widget Palette" to get started</p>
                            </div>`
                            : html`
                            <div class="space-y-2">
                                ${(d.widgets || []).map((w, idx) => html`
                                <div class="relative group rounded-lg border border-gray-200 bg-gray-50 overflow-hidden"
                                    style="min-height: ${w.position.h * CELL_HEIGHT}px;"
                                    draggable="true"
                                    @dragstart=${(e: DragEvent) => this.handleWidgetDragStart(e, w, idx)}
                                    @dragover=${(e: DragEvent) => this.handleWidgetDragOver(e)}
                                    @drop=${(e: DragEvent) => this.handleWidgetDrop(e, idx)}>
                                    <!-- Widget Header -->
                                    <div class="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-100">
                                        <div class="flex items-center gap-2">
                                            <svg class="h-4 w-4 text-gray-400 cursor-grab" viewBox="0 0 24 24" fill="none"
                                                stroke="currentColor" stroke-width="2">
                                                <circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/>
                                                <circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/>
                                                <circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/>
                                            </svg>
                                            <svg class="h-4 w-4 text-gray-400" viewBox="0 0 24 24" fill="none"
                                                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                                <path d="${this.widgetIcon(w.type)}"/>
                                            </svg>
                                            <span class="text-sm font-semibold text-gray-700">${w.title}</span>
                                            <span class="text-[10px] text-gray-400 px-1.5 py-0.5 bg-gray-100 rounded">${w.type}</span>
                                            <span class="text-[10px] text-gray-300">${w.position.w}x${w.position.h}</span>
                                        </div>
                                        <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button class="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                                                title="Shrink width" @click=${() => this.resizeWidget(w.id, -1, 0)}>
                                                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 12h8"/></svg>
                                            </button>
                                            <button class="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                                                title="Grow width" @click=${() => this.resizeWidget(w.id, 1, 0)}>
                                                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                                            </button>
                                            <button class="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                                                title="Shrink height" @click=${() => this.resizeWidget(w.id, 0, -1)}>
                                                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 8v8"/></svg>
                                            </button>
                                            <button class="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                                                title="Grow height" @click=${() => this.resizeWidget(w.id, 0, 1)}>
                                                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14"/></svg>
                                            </button>
                                            <button class="p-1 rounded hover:bg-blue-50 text-gray-400 hover:text-blue-600"
                                                title="Configure" @click=${() => this.openWidgetConfig(w)}>
                                                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
                                            </button>
                                            <button class="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-600"
                                                title="Remove" @click=${() => this.removeWidget(w.id)}>
                                                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
                                            </button>
                                        </div>
                                    </div>
                                    <!-- Widget Body Placeholder -->
                                    <div class="p-4 flex items-center justify-center" style="min-height: ${(w.position.h - 1) * CELL_HEIGHT}px;">
                                        ${this.renderWidgetPlaceholder(w)}
                                    </div>
                                </div>`)}
                            </div>`}
                    </div>
                </div>
            </div>

            <!-- Widget Configuration Panel (slide-over) -->
            ${this.editingWidget ? this.renderWidgetConfigPanel() : nothing}
        `;
    }

    // ── Widget Placeholders ──────────────────────────────────────────────

    private renderWidgetPlaceholder(w: Widget) {
        switch (w.type) {
            case 'chart':
                return html`
                <div class="w-full flex items-end gap-1 px-4">
                    ${[40, 65, 30, 80, 55, 70, 45, 90, 60, 75, 50, 85].map(h => html`
                    <div class="flex-1 bg-brand/20 rounded-t" style="height: ${h}%"></div>`)}
                </div>`;
            case 'table':
                return html`
                <div class="w-full space-y-1.5">
                    ${[1,2,3].map(() => html`
                    <div class="flex gap-2">
                        <div class="flex-1 h-3 bg-gray-200 rounded"></div>
                        <div class="flex-1 h-3 bg-gray-100 rounded"></div>
                        <div class="flex-1 h-3 bg-gray-200 rounded"></div>
                    </div>`)}
                </div>`;
            case 'kpi':
                return html`
                <div class="text-center">
                    <div class="text-3xl font-black text-gray-700">12,847</div>
                    <div class="text-xs text-green-500 font-semibold mt-1">+12.4% vs last period</div>
                </div>`;
            case 'text':
                return html`
                <div class="w-full space-y-2">
                    <div class="h-3 bg-gray-200 rounded w-3/4"></div>
                    <div class="h-3 bg-gray-100 rounded w-full"></div>
                    <div class="h-3 bg-gray-100 rounded w-5/6"></div>
                </div>`;
            case 'iframe':
                return html`
                <div class="w-full h-full flex items-center justify-center border border-dashed border-gray-300 rounded">
                    <div class="text-center">
                        <svg class="h-6 w-6 text-gray-300 mx-auto mb-1" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
                        <span class="text-xs text-gray-400">${(w.config as Record<string, string>)?.url || 'Embed URL'}</span>
                    </div>
                </div>`;
            default:
                return html`<span class="text-xs text-gray-400">Widget</span>`;
        }
    }

    // ── Widget Config Panel ──────────────────────────────────────────────

    private renderWidgetConfigPanel() {
        const w = this.editingWidget!;
        return html`
        <div class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Configure widget">
            <div class="absolute inset-0 bg-black/20" @click=${() => this.closeWidgetConfig()}></div>
            <div class="relative w-96 bg-white h-full overflow-y-auto shadow-2xl border-l border-gray-200" tabindex="-1">
                <div class="sticky top-0 bg-white border-b border-gray-100 px-5 py-4 flex items-center justify-between z-10">
                    <h3 class="font-bold text-sm">Configure Widget</h3>
                    <button class="text-gray-400 hover:text-ink" @click=${() => this.closeWidgetConfig()}>&#10005;</button>
                </div>
                <div class="p-5 space-y-5">
                    <!-- Widget Type Badge -->
                    <div class="flex items-center gap-2">
                        <svg class="h-5 w-5 text-gray-400" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="${this.widgetIcon(w.type)}"/>
                        </svg>
                        <span class="text-sm font-semibold text-gray-700">${w.type}</span>
                        <span class="text-xs text-gray-300">${w.position.w}x${w.position.h}</span>
                    </div>

                    <!-- Title -->
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Title</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            .value=${this.widgetFormTitle}
                            @input=${(e: Event) => { this.widgetFormTitle = (e.target as HTMLInputElement).value; }} />
                    </div>

                    <!-- Type-specific config fields -->
                    ${w.type === 'chart' ? html`
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Data Source</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            placeholder="SQL query or endpoint URL"
                            .value=${(w.config as Record<string, string>)?.dataSource || ''}
                            @input=${(e: Event) => {
                                try { this.widgetFormConfig = JSON.stringify({ ...JSON.parse(this.widgetFormConfig), dataSource: (e.target as HTMLInputElement).value }); } catch {}
                            }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Chart Type</label>
                        <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            @change=${(e: Event) => {
                                try { this.widgetFormConfig = JSON.stringify({ ...JSON.parse(this.widgetFormConfig), chartType: (e.target as HTMLSelectElement).value }); } catch {}
                            }}>
                            <option value="bar">Bar</option>
                            <option value="line">Line</option>
                            <option value="area">Area</option>
                            <option value="pie">Pie</option>
                            <option value="scatter">Scatter</option>
                        </select>
                    </div>` : nothing}

                    ${w.type === 'iframe' ? html`
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Embed URL</label>
                        <input type="url" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            placeholder="https://example.com/embed"
                            .value=${(w.config as Record<string, string>)?.url || ''}
                            @input=${(e: Event) => {
                                try { this.widgetFormConfig = JSON.stringify({ ...JSON.parse(this.widgetFormConfig), url: (e.target as HTMLInputElement).value }); } catch {}
                            }} />
                    </div>` : nothing}

                    ${w.type === 'kpi' ? html`
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Metric Endpoint</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            placeholder="/v1/metrics/my-kpi"
                            .value=${(w.config as Record<string, string>)?.endpoint || ''}
                            @input=${(e: Event) => {
                                try { this.widgetFormConfig = JSON.stringify({ ...JSON.parse(this.widgetFormConfig), endpoint: (e.target as HTMLInputElement).value }); } catch {}
                            }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Format</label>
                        <select class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            @change=${(e: Event) => {
                                try { this.widgetFormConfig = JSON.stringify({ ...JSON.parse(this.widgetFormConfig), format: (e.target as HTMLSelectElement).value }); } catch {}
                            }}>
                            <option value="number">Number</option>
                            <option value="currency">Currency</option>
                            <option value="percent">Percentage</option>
                        </select>
                    </div>` : nothing}

                    <!-- Raw JSON config (advanced) -->
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">
                            Config JSON
                            <span class="text-gray-300 font-normal">(advanced)</span>
                        </label>
                        <textarea class="w-full px-3 py-2 text-xs font-mono border border-gray-200 rounded-lg h-32 resize-y"
                            .value=${this.widgetFormConfig}
                            @input=${(e: Event) => { this.widgetFormConfig = (e.target as HTMLTextAreaElement).value; }}></textarea>
                    </div>

                    <div class="flex justify-end gap-2 pt-2">
                        <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                            @click=${() => this.closeWidgetConfig()}>Cancel</button>
                        <button class="px-4 py-2 text-sm font-bold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                            @click=${() => this.saveWidgetConfig()}>Save</button>
                    </div>
                </div>
            </div>
        </div>`;
    }
}
