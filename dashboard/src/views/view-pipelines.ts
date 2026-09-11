import { LitElement, html, nothing, svg } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

/* ──────────────────────────────────────────────────────────────────────
   Interfaces
   ────────────────────────────────────────────────────────────────────── */

interface PipelineStep {
    id: string;
    step_type: string;
    name: string;
    order: number;
    config: Record<string, unknown>;
    retry_count: number;
    timeout_seconds: number;
}

interface Pipeline {
    id: string;
    name: string;
    description: string;
    status: string;
    schedule: string;
    schedule_timezone: string;
    config: Record<string, unknown>;
    version: number;
    step_count: number;
    tenant_id: string;
    created_at: string;
    updated_at: string;
}

interface PipelineRun {
    id: string;
    pipeline_id: string;
    status: string;
    triggered_by: string;
    trigger_type: string;
    started_at: string | null;
    completed_at: string | null;
    steps_completed: number;
    steps_total: number;
    error_message: string;
    created_at: string;
}

interface DAGNode {
    id: string;
    step_type: string;
    name: string;
    x: number;
    y: number;
    config: Record<string, unknown>;
}

interface DAGEdge {
    source: string;
    target: string;
}

interface DAGValidationError {
    message: string;
    severity: string;
    step_id?: string;
    edge?: { source: string; target: string };
}

interface DAGValidationResult {
    valid: boolean;
    errors: DAGValidationError[];
    warnings: DAGValidationError[];
    execution_order: string[];
}

interface TransformInfo {
    type: string;
    label: string;
    input_schema: Record<string, unknown> | null;
    output_schema: Record<string, unknown> | null;
}

/* ──────────────────────────────────────────────────────────────────────
   Constants
   ────────────────────────────────────────────────────────────────────── */

const NODE_W = 180;
const NODE_H = 64;
const PORT_R = 7;

const NODE_COLORS: Record<string, string> = {
    source: '#3B82F6',
    ingest: '#3B82F6',
    transform: '#8B5CF6',
    filter: '#F59E0B',
    aggregate: '#EC4899',
    join: '#06B6D4',
    sort: '#84CC16',
    dedup: '#F97316',
    flatten: '#6366F1',
    map: '#A855F7',
    export: '#22C55E',
    quality_check: '#EF4444',
    profile: '#14B8A6',
    custom: '#6B7280',
    scrape: '#D946EF',
    sql_query: '#0EA5E9',
};

const PALETTE_ITEMS = [
    { type: 'ingest', label: 'Source', icon: '📥' },
    { type: 'transform', label: 'Transform', icon: '⚙️' },
    { type: 'filter', label: 'Filter', icon: '🔍' },
    { type: 'aggregate', label: 'Aggregate', icon: '📊' },
    { type: 'join', label: 'Join', icon: '🔗' },
    { type: 'sort', label: 'Sort', icon: '↕️' },
    { type: 'dedup', label: 'Dedup', icon: '🧹' },
    { type: 'flatten', label: 'Flatten', icon: '📐' },
    { type: 'map', label: 'Map', icon: '🗺️' },
    { type: 'export', label: 'Export', icon: '📤' },
    { type: 'quality_check', label: 'Quality', icon: '✅' },
    { type: 'custom', label: 'Custom', icon: '🔧' },
];

/* ──────────────────────────────────────────────────────────────────────
   Config schema per transform type
   ────────────────────────────────────────────────────────────────────── */

const CONFIG_FIELDS: Record<string, Array<{ key: string; label: string; type: string; placeholder?: string }>> = {
    filter: [
        { key: 'field', label: 'Field', type: 'text', placeholder: 'column name' },
        { key: 'operator', label: 'Operator', type: 'select', placeholder: '==' },
        { key: 'value', label: 'Value', type: 'text', placeholder: 'value to match' },
    ],
    map: [
        { key: 'expression', label: 'Expression', type: 'text', placeholder: "row['price'] * 1.1" },
        { key: 'output_field', label: 'Output Field', type: 'text', placeholder: 'result_column' },
    ],
    join: [
        { key: 'left_key', label: 'Left Key', type: 'text', placeholder: 'left column' },
        { key: 'right_key', label: 'Right Key', type: 'text', placeholder: 'right column' },
        { key: 'join_type', label: 'Join Type', type: 'select', placeholder: 'inner' },
        { key: 'right_data_field', label: 'Right Data Source', type: 'text', placeholder: 'step id or context key' },
    ],
    aggregate: [
        { key: 'group_by', label: 'Group By (comma-sep)', type: 'text', placeholder: 'category, region' },
    ],
    sort: [
        { key: 'sort_by', label: 'Sort Column', type: 'text', placeholder: 'column name' },
        { key: 'sort_direction', label: 'Direction', type: 'select', placeholder: 'asc' },
    ],
    dedup: [
        { key: 'fields', label: 'Fields (comma-sep)', type: 'text', placeholder: 'email, name (empty = all)' },
        { key: 'keep', label: 'Keep', type: 'select', placeholder: 'first' },
    ],
    flatten: [
        { key: 'field', label: 'Field', type: 'text', placeholder: 'nested field name' },
        { key: 'flatten_type', label: 'Type', type: 'select', placeholder: 'list' },
    ],
};

/* ──────────────────────────────────────────────────────────────────────
   View Component
   ────────────────────────────────────────────────────────────────────── */

@customElement('view-pipelines')
export class ViewPipelines extends LitElement {
    @state() pipelines: Pipeline[] = [];
    @state() loading = true;

    // Editor mode
    @state() editorMode: 'list' | 'editor' = 'list';
    @state() editorPipeline: Pipeline | null = null;
    @state() dagNodes: DAGNode[] = [];
    @state() dagEdges: DAGEdge[] = [];
    @state() selectedNode: DAGNode | null = null;
    @state() connecting: { fromId: string } | null = null;
    @state() dagValidation: DAGValidationResult | null = null;
    @state() transforms: TransformInfo[] = [];
    @state() saving = false;

    // Runs
    @state() pipelineRuns: PipelineRun[] = [];
    @state() runsLoading = false;
    @state() showRunHistory = false;

    // Canvas pan
    @state() canvasPanX = 0;
    @state() canvasPanY = 0;
    @state() canvasZoom = 1;

    // Create modal
    @state() showCreate = false;
    @state() createName = '';
    @state() createDescription = '';
    @state() createSchedule = '';

    // Drag state (non-reactive)
    private _dragNode: DAGNode | null = null;
    private _dragOffX = 0;
    private _dragOffY = 0;
    private _panning = false;
    private _panStartX = 0;
    private _panStartY = 0;
    private _panStartPX = 0;
    private _panStartPY = 0;

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.load();
        await this.loadTransforms();
    }

    /* ── Data Loading ─────────────────────────────────────────────────── */

    async load() {
        this.loading = true;
        try {
            this.pipelines = await api.get<Pipeline[]>('/v1/pipelines');
        } catch {
            this.pipelines = [];
        } finally {
            this.loading = false;
        }
    }

    async loadTransforms() {
        try {
            this.transforms = await api.get<TransformInfo[]>('/v1/pipelines/transforms/catalog');
        } catch {
            this.transforms = [];
        }
    }

    /* ── Pipeline CRUD ────────────────────────────────────────────────── */

    async createPipeline() {
        if (!this.createName.trim()) return;
        try {
            await api.post('/v1/pipelines', {
                name: this.createName,
                description: this.createDescription,
                schedule: this.createSchedule,
            });
            this.showCreate = false;
            this.createName = '';
            this.createDescription = '';
            this.createSchedule = '';
            await this.load();
        } catch (e: unknown) {
            console.error('Failed to create pipeline:', e);
        }
    }

    async deletePipeline(id: string) {
        if (!confirm('Delete this pipeline?')) return;
        try {
            await api.del(`/v1/pipelines/${id}`);
            if (this.editorPipeline?.id === id) this.closeEditor();
            await this.load();
        } catch (e: unknown) {
            console.error('Failed to delete pipeline:', e);
        }
    }

    /* ── DAG Editor ───────────────────────────────────────────────────── */

    async openEditor(pipeline: Pipeline) {
        this.editorPipeline = pipeline;
        this.editorMode = 'editor';
        this.selectedNode = null;
        this.connecting = null;
        this.dagValidation = null;
        this.showRunHistory = false;
        this.canvasPanX = 0;
        this.canvasPanY = 0;
        this.canvasZoom = 1;

        // Load steps
        try {
            const steps = await api.get<PipelineStep[]>(`/v1/pipelines/${pipeline.id}/steps`);
            this.dagNodes = steps.map((s, i) => ({
                id: s.id,
                step_type: s.step_type,
                name: s.name || s.step_type,
                x: 40 + (i % 4) * 220,
                y: 40 + Math.floor(i / 4) * 120,
                config: s.config || {},
            }));
            // Build edges from depends_on in config
            this.dagEdges = [];
            for (const s of steps) {
                const deps = (s.config as Record<string, unknown>)?.depends_on as string[] | undefined;
                if (Array.isArray(deps)) {
                    for (const depId of deps) {
                        this.dagEdges.push({ source: depId, target: s.id });
                    }
                }
            }
        } catch {
            this.dagNodes = [];
            this.dagEdges = [];
        }

        // Load runs
        await this.loadRuns();
    }

    closeEditor() {
        this.editorMode = 'list';
        this.editorPipeline = null;
        this.dagNodes = [];
        this.dagEdges = [];
        this.selectedNode = null;
        this.connecting = null;
    }

    /* ── DAG Node Operations ──────────────────────────────────────────── */

    addNodeFromPalette(stepType: string, e: DragEvent) {
        const rect = (e.target as HTMLElement).closest('.dag-canvas')?.getBoundingClientRect();
        const dropX = e.clientX - (rect?.left || 0);
        const dropY = e.clientY - (rect?.top || 0);

        const id = `node-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
        const label = PALETTE_ITEMS.find(p => p.type === stepType)?.label || stepType;
        const node: DAGNode = {
            id,
            step_type: stepType,
            name: label,
            x: (dropX - this.canvasPanX) / this.canvasZoom - NODE_W / 2,
            y: (dropY - this.canvasPanY) / this.canvasZoom - NODE_H / 2,
            config: {},
        };
        this.dagNodes = [...this.dagNodes, node];
        this.selectedNode = node;
    }

    addNodeAtCenter(stepType: string) {
        const id = `node-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
        const label = PALETTE_ITEMS.find(p => p.type === stepType)?.label || stepType;
        const node: DAGNode = {
            id,
            step_type: stepType,
            name: label,
            x: 100 + Math.random() * 300,
            y: 80 + Math.random() * 200,
            config: {},
        };
        this.dagNodes = [...this.dagNodes, node];
        this.selectedNode = node;
    }

    removeNode(id: string) {
        this.dagNodes = this.dagNodes.filter(n => n.id !== id);
        this.dagEdges = this.dagEdges.filter(e => e.source !== id && e.target !== id);
        if (this.selectedNode?.id === id) this.selectedNode = null;
    }

    selectNode(node: DAGNode) {
        if (this.connecting) {
            // Complete connection
            if (this.connecting.fromId !== node.id) {
                const exists = this.dagEdges.some(
                    e => e.source === this.connecting!.fromId && e.target === node.id
                );
                if (!exists) {
                    this.dagEdges = [...this.dagEdges, { source: this.connecting.fromId, target: node.id }];
                }
            }
            this.connecting = null;
        } else {
            this.selectedNode = node;
        }
    }

    startConnect(nodeId: string) {
        this.connecting = { fromId: nodeId };
    }

    removeEdge(source: string, target: string) {
        this.dagEdges = this.dagEdges.filter(e => !(e.source === source && e.target === target));
    }

    updateNodeName(name: string) {
        if (!this.selectedNode) return;
        this.selectedNode = { ...this.selectedNode, name };
        this.dagNodes = this.dagNodes.map(n => n.id === this.selectedNode!.id ? this.selectedNode! : n);
    }

    updateNodeConfig(key: string, value: string) {
        if (!this.selectedNode) return;
        const config = { ...this.selectedNode.config, [key]: value };
        this.selectedNode = { ...this.selectedNode, config };
        this.dagNodes = this.dagNodes.map(n => n.id === this.selectedNode!.id ? this.selectedNode! : n);
    }

    /* ── Canvas Drag ──────────────────────────────────────────────────── */

    onNodeMouseDown(node: DAGNode, e: MouseEvent) {
        e.stopPropagation();
        if (this.connecting) {
            this.selectNode(node);
            return;
        }
        this._dragNode = node;
        this._dragOffX = e.clientX - node.x * this.canvasZoom - this.canvasPanX;
        this._dragOffY = e.clientY - node.y * this.canvasZoom - this.canvasPanY;

        const onMove = (ev: MouseEvent) => {
            if (!this._dragNode) return;
            const nx = (ev.clientX - this._dragOffX - this.canvasPanX) / this.canvasZoom;
            const ny = (ev.clientY - this._dragOffY - this.canvasPanY) / this.canvasZoom;
            this._dragNode.x = nx;
            this._dragNode.y = ny;
            this.dagNodes = [...this.dagNodes]; // trigger re-render
        };
        const onUp = () => {
            this._dragNode = null;
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    }

    onCanvasMouseDown(e: MouseEvent) {
        if ((e.target as HTMLElement).closest('.dag-node')) return;
        this.selectedNode = null;
        this.connecting = null;
        this._panning = true;
        this._panStartX = e.clientX;
        this._panStartY = e.clientY;
        this._panStartPX = this.canvasPanX;
        this._panStartPY = this.canvasPanY;

        const onMove = (ev: MouseEvent) => {
            if (!this._panning) return;
            this.canvasPanX = this._panStartPX + (ev.clientX - this._panStartX);
            this.canvasPanY = this._panStartPY + (ev.clientY - this._panStartY);
        };
        const onUp = () => {
            this._panning = false;
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    }

    onCanvasWheel(e: WheelEvent) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.92 : 1.08;
        this.canvasZoom = Math.max(0.2, Math.min(3, this.canvasZoom * delta));
    }

    /* ── Validation / Save / Run ───────────────────────────────────────── */

    async validateDag() {
        if (!this.editorPipeline) return;
        try {
            const result = await api.post<DAGValidationResult>(
                `/v1/pipelines/${this.editorPipeline.id}/validate`,
                {
                    steps: this.dagNodes.map(n => ({
                        id: n.id,
                        step_type: n.step_type,
                        name: n.name,
                        config: { ...n.config, transform_type: n.step_type },
                    })),
                    edges: this.dagEdges,
                },
            );
            this.dagValidation = result;
        } catch (e: unknown) {
            console.error('Validation failed:', e);
        }
    }

    async saveDag() {
        if (!this.editorPipeline) return;
        this.saving = true;
        try {
            // Delete existing steps then recreate
            const existing = await api.get<PipelineStep[]>(`/v1/pipelines/${this.editorPipeline.id}/steps`);
            for (const s of existing) {
                await api.del(`/v1/pipelines/steps/${s.id}`);
            }

            // Create steps
            const idMap: Record<string, string> = {};
            for (let i = 0; i < this.dagNodes.length; i++) {
                const n = this.dagNodes[i];
                const edgeTargets = this.dagEdges.filter(e => e.target === n.id);
                const dependsOn: string[] = [];
                for (const e of edgeTargets) {
                    if (idMap[e.source]) dependsOn.push(idMap[e.source]);
                }

                const step = await api.post<PipelineStep>(
                    `/v1/pipelines/${this.editorPipeline.id}/steps`,
                    {
                        step_type: n.step_type,
                        name: n.name,
                        order: i,
                        config: { ...n.config, transform_type: n.step_type, depends_on: dependsOn },
                    },
                );
                idMap[n.id] = step.id;
                // Update local node to server id
                this.dagNodes[i] = { ...n, id: step.id };
            }
            this.dagNodes = [...this.dagNodes];

            // Update edge references to server IDs
            this.dagEdges = this.dagEdges.map(e => ({
                source: idMap[e.source] || e.source,
                target: idMap[e.target] || e.target,
            }));

            await this.load();
        } catch (e: unknown) {
            console.error('Save failed:', e);
        } finally {
            this.saving = false;
        }
    }

    async runPipeline(id: string) {
        try {
            await api.post(`/v1/pipelines/${id}/run`, {});
            await this.loadRuns();
            await this.load();
        } catch (e: unknown) {
            console.error('Failed to run pipeline:', e);
        }
    }

    async loadRuns() {
        if (!this.editorPipeline) return;
        this.runsLoading = true;
        try {
            this.pipelineRuns = await api.get<PipelineRun[]>(`/v1/pipelines/${this.editorPipeline.id}/runs`);
        } catch {
            this.pipelineRuns = [];
        } finally {
            this.runsLoading = false;
        }
    }

    /* ── Import / Export ──────────────────────────────────────────────── */

    exportPipeline() {
        const data = {
            name: this.editorPipeline?.name || '',
            description: this.editorPipeline?.description || '',
            schedule: this.editorPipeline?.schedule || '',
            steps: this.dagNodes.map(n => ({
                id: n.id,
                step_type: n.step_type,
                name: n.name,
                config: n.config,
                x: n.x,
                y: n.y,
            })),
            edges: this.dagEdges,
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pipeline-${this.editorPipeline?.name || 'export'}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    importPipeline() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.onchange = async () => {
            const file = input.files?.[0];
            if (!file) return;
            try {
                const text = await file.text();
                const data = JSON.parse(text);
                // Create pipeline then populate
                const pipeline = await api.post<Pipeline>('/v1/pipelines/import', {
                    name: data.name || 'Imported Pipeline',
                    description: data.description || '',
                    schedule: data.schedule || '',
                    steps: (data.steps || []).map((s: Record<string, unknown>) => ({
                        id: s.id,
                        step_type: s.step_type,
                        name: s.name,
                        config: s.config || {},
                    })),
                    edges: data.edges || [],
                });
                await this.load();
                await this.openEditor(pipeline);
            } catch (e: unknown) {
                console.error('Import failed:', e);
                alert('Failed to import pipeline. Check JSON format.');
            }
        };
        input.click();
    }

    /* ── Helpers ──────────────────────────────────────────────────────── */

    private statusBadge(s: string) {
        const colors: Record<string, string> = {
            active: 'bg-green-50 text-green-700 border-green-200',
            draft: 'bg-gray-50 text-gray-600 border-gray-200',
            running: 'bg-blue-50 text-blue-700 border-blue-200',
            queued: 'bg-blue-50 text-blue-600 border-blue-200',
            succeeded: 'bg-green-50 text-green-700 border-green-200',
            paused: 'bg-amber-50 text-amber-700 border-amber-200',
            failed: 'bg-red-50 text-red-700 border-red-200',
            cancelled: 'bg-gray-50 text-gray-500 border-gray-200',
            inactive: 'bg-gray-50 text-gray-500 border-gray-200',
        };
        return html`<span class="px-2 py-0.5 text-xs font-medium rounded border ${colors[s] || colors.inactive}">${s}</span>`;
    }

    private nodeColor(type: string): string {
        return NODE_COLORS[type] || NODE_COLORS.custom;
    }

    private formatDuration(start: string | null, end: string | null): string {
        if (!start) return '-';
        const s = new Date(start).getTime();
        const e = end ? new Date(end).getTime() : Date.now();
        const secs = Math.round((e - s) / 1000);
        if (secs < 60) return `${secs}s`;
        return `${Math.floor(secs / 60)}m ${secs % 60}s`;
    }

    /* ── Render ────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/pipelines"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50" role="main" aria-label="Pipelines management">
            ${this.editorMode === 'editor' ? this.renderEditor() : this.renderList()}
        </main>`;
    }

    /* ── List View ────────────────────────────────────────────────────── */

    renderList() {
        return html`
        <div class="p-8">
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-black font-display tracking-tight">Pipelines</h1>
                <div class="flex gap-2">
                    <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        @click=${() => this.importPipeline()}>Import JSON</button>
                    <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        aria-label="Refresh pipelines" @click=${() => this.load()}>Refresh</button>
                    <button class="px-4 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                        aria-label="Create new pipeline"
                        @click=${() => { this.showCreate = !this.showCreate; }}>+ New Pipeline</button>
                </div>
            </div>

            ${this.showCreate ? html`
            <div class="bg-white rounded-xl border border-gray-100 p-6 mb-6">
                <h3 class="text-sm font-semibold text-gray-500 mb-4">Create New Pipeline</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Name *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            placeholder="My Pipeline" .value=${this.createName}
                            @input=${(e: Event) => { this.createName = (e.target as HTMLInputElement).value; }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Description</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            placeholder="Pipeline description" .value=${this.createDescription}
                            @input=${(e: Event) => { this.createDescription = (e.target as HTMLInputElement).value; }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Schedule (cron)</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg font-mono"
                            placeholder="0 */6 * * *" .value=${this.createSchedule}
                            @input=${(e: Event) => { this.createSchedule = (e.target as HTMLInputElement).value; }} />
                    </div>
                </div>
                <div class="flex justify-end gap-2">
                    <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        @click=${() => { this.showCreate = false; }}>Cancel</button>
                    <button class="px-4 py-2 text-sm font-bold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                        @click=${() => this.createPipeline()}>Create Pipeline</button>
                </div>
            </div>` : nothing}

            ${this.loading ? html`<div class="text-center text-gray-500 py-16">Loading...</div>` : html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <table class="w-full text-sm">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                        <th class="px-4 py-3">Name</th>
                        <th class="px-4 py-3">Status</th>
                        <th class="px-4 py-3">Schedule</th>
                        <th class="px-4 py-3">Steps</th>
                        <th class="px-4 py-3">Version</th>
                        <th class="px-4 py-3">Created</th>
                        <th class="px-4 py-3">Actions</th>
                    </tr></thead>
                    <tbody>
                    ${this.pipelines.length === 0
                        ? html`<tr><td colspan="7" class="px-4 py-12 text-center text-gray-500">No pipelines found. Create one to get started.</td></tr>`
                        : this.pipelines.map(p => html`
                        <tr class="border-b border-gray-50 hover:bg-gray-50">
                            <td class="px-4 py-3">
                                <button class="font-semibold text-blue-600 hover:underline text-left"
                                    @click=${() => this.openEditor(p)}>${p.name}</button>
                                ${p.description ? html`<div class="text-xs text-gray-500">${p.description}</div>` : nothing}
                            </td>
                            <td class="px-4 py-3">${this.statusBadge(p.status)}</td>
                            <td class="px-4 py-3 font-mono text-xs">${p.schedule || 'Manual'}</td>
                            <td class="px-4 py-3 text-xs">${p.step_count} steps</td>
                            <td class="px-4 py-3 text-xs text-gray-500">v${p.version}</td>
                            <td class="px-4 py-3 text-xs text-gray-500">${new Date(p.created_at).toLocaleString()}</td>
                            <td class="px-4 py-3">
                                <div class="flex gap-2">
                                    <button class="text-xs text-blue-600 hover:underline"
                                        @click=${() => this.openEditor(p)}>Edit</button>
                                    <button class="text-xs text-green-600 hover:underline"
                                        @click=${() => this.runPipeline(p.id)}>Run</button>
                                    <button class="text-xs text-red-500 hover:underline"
                                        @click=${() => this.deletePipeline(p.id)}>Delete</button>
                                </div>
                            </td>
                        </tr>`)}
                    </tbody>
                </table>
            </div>`}
        </div>`;
    }

    /* ── DAG Editor View ──────────────────────────────────────────────── */

    renderEditor() {
        const pipeline = this.editorPipeline!;
        return html`
        <!-- Top bar -->
        <div class="sticky top-0 z-30 bg-white border-b border-gray-200 px-4 py-2 flex items-center gap-4">
            <button class="text-gray-500 hover:text-ink text-lg" @click=${() => this.closeEditor()}>&larr;</button>
            <h2 class="font-bold text-base flex-1">${pipeline.name}</h2>
            ${this.statusBadge(pipeline.status)}
            <span class="text-xs text-gray-500">${this.dagNodes.length} nodes &middot; ${this.dagEdges.length} edges</span>
            <button class="px-3 py-1.5 text-xs border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                @click=${() => this.exportPipeline()}>Export JSON</button>
            <button class="px-3 py-1.5 text-xs border border-blue-200 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100"
                @click=${() => this.validateDag()}>Validate</button>
            <button class="px-3 py-1.5 text-xs font-semibold bg-gray-800 text-white rounded-lg hover:bg-gray-900 ${this.saving ? 'opacity-50' : ''}"
                ?disabled=${this.saving}
                @click=${() => this.saveDag()}>${this.saving ? 'Saving...' : 'Save'}</button>
            <button class="px-3 py-1.5 text-xs font-semibold bg-brand text-white rounded-lg hover:bg-black"
                @click=${() => this.runPipeline(pipeline.id)}>Run</button>
            <button class="px-2 py-1.5 text-xs border rounded-lg ${this.showRunHistory ? 'bg-gray-100' : 'bg-white'} hover:bg-gray-50"
                @click=${() => { this.showRunHistory = !this.showRunHistory; if (this.showRunHistory) this.loadRuns(); }}>
                Runs (${this.pipelineRuns.length})
            </button>
        </div>

        <div class="flex" style="height: calc(100vh - 52px)">
            <!-- Left: Node Palette -->
            <div class="w-48 bg-white border-r border-gray-200 p-3 overflow-y-auto flex-shrink-0">
                <h4 class="text-xs font-semibold text-gray-500 uppercase mb-3">Node Palette</h4>
                <div class="space-y-1.5">
                    ${PALETTE_ITEMS.map(item => html`
                    <div class="flex items-center gap-2 px-2.5 py-2 rounded-lg border border-gray-100 bg-gray-50 hover:bg-gray-100 cursor-grab text-sm select-none"
                        draggable="true"
                        @dragstart=${(e: DragEvent) => {
                            e.dataTransfer?.setData('text/plain', item.type);
                        }}
                        @click=${() => this.addNodeAtCenter(item.type)}>
                        <span class="text-base">${item.icon}</span>
                        <span class="font-medium text-xs">${item.label}</span>
                    </div>`)}
                </div>

                <!-- Validation results -->
                ${this.dagValidation ? html`
                <div class="mt-4 pt-3 border-t border-gray-100">
                    <h4 class="text-xs font-semibold mb-2 ${this.dagValidation.valid ? 'text-green-600' : 'text-red-600'}">
                        ${this.dagValidation.valid ? '✓ Valid DAG' : '✗ Invalid DAG'}
                    </h4>
                    ${this.dagValidation.errors.map(err => html`
                    <div class="text-xs text-red-600 mb-1">• ${err.message}</div>`)}
                    ${this.dagValidation.warnings.map(w => html`
                    <div class="text-xs text-amber-600 mb-1">⚠ ${w.message}</div>`)}
                    ${this.dagValidation.execution_order.length > 0 ? html`
                    <div class="mt-2">
                        <div class="text-xs text-gray-500 mb-1">Execution order:</div>
                        ${this.dagValidation.execution_order.map((id, i) => {
                            const node = this.dagNodes.find(n => n.id === id);
                            return html`<div class="text-xs text-gray-600">${i + 1}. ${node?.name || id.slice(0, 8)}</div>`;
                        })}
                    </div>` : nothing}
                </div>` : nothing}

                <!-- Help -->
                <div class="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-500 space-y-1">
                    <div><b>Click</b> node = select</div>
                    <div><b>Drag</b> node = move</div>
                    <div><b>Drag</b> canvas = pan</div>
                    <div><b>Scroll</b> = zoom</div>
                    <div><b>Click port</b> = connect</div>
                </div>
            </div>

            <!-- Center: Canvas -->
            <div class="flex-1 relative overflow-hidden dag-canvas"
                style="background:#FAFAFA;cursor:${this.connecting ? 'crosshair' : this._panning ? 'grabbing' : 'grab'}"
                @mousedown=${this.onCanvasMouseDown}
                @wheel=${(e: WheelEvent) => this.onCanvasWheel(e)}
                @dragover=${(e: DragEvent) => { e.preventDefault(); }}
                @drop=${(e: DragEvent) => {
                    e.preventDefault();
                    const type = e.dataTransfer?.getData('text/plain');
                    if (type) this.addNodeFromPalette(type, e);
                }}>

                <!-- Zoom controls -->
                <div class="absolute top-3 right-3 z-20 flex items-center gap-1">
                    <button class="w-7 h-7 border border-gray-200 rounded bg-white text-sm flex items-center justify-center hover:bg-gray-50"
                        @click=${() => { this.canvasZoom = Math.min(3, this.canvasZoom * 1.2); }}>+</button>
                    <span class="text-xs text-gray-500 w-10 text-center">${(this.canvasZoom * 100).toFixed(0)}%</span>
                    <button class="w-7 h-7 border border-gray-200 rounded bg-white text-sm flex items-center justify-center hover:bg-gray-50"
                        @click=${() => { this.canvasZoom = Math.max(0.2, this.canvasZoom * 0.8); }}>−</button>
                    <button class="px-2 h-7 border border-gray-200 rounded bg-white text-xs hover:bg-gray-50"
                        @click=${() => { this.canvasZoom = 1; this.canvasPanX = 0; this.canvasPanY = 0; }}>Fit</button>
                </div>

                <!-- Connecting mode banner -->
                ${this.connecting ? html`
                <div class="absolute top-3 left-1/2 -translate-x-1/2 z-20 px-4 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-full shadow">
                    Click a target node to connect &middot; <button class="underline" @click=${() => { this.connecting = null; }}>Cancel</button>
                </div>` : nothing}

                <!-- Canvas transform layer -->
                <div style="position:absolute;top:0;left:0;width:100%;height:100%;transform-origin:0 0;transform:translate(${this.canvasPanX}px,${this.canvasPanY}px) scale(${this.canvasZoom})">

                    <!-- Grid pattern -->
                    <svg style="position:absolute;top:0;left:0;width:2000px;height:2000px;pointer-events:none;opacity:0.3">
                        <defs>
                            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#E5E7EB" stroke-width="0.5"/>
                            </pattern>
                        </defs>
                        <rect width="2000" height="2000" fill="url(#grid)"/>
                    </svg>

                    <!-- Edges (SVG) -->
                    <svg style="position:absolute;top:0;left:0;width:2000px;height:2000px;pointer-events:none;overflow:visible">
                        ${this.dagEdges.map(edge => {
                            const srcNode = this.dagNodes.find(n => n.id === edge.source);
                            const tgtNode = this.dagNodes.find(n => n.id === edge.target);
                            if (!srcNode || !tgtNode) return svg``;

                            const sx = srcNode.x + NODE_W;
                            const sy = srcNode.y + NODE_H / 2;
                            const tx = tgtNode.x;
                            const ty = tgtNode.y + NODE_H / 2;
                            const mx = (sx + tx) / 2;

                            return svg`
                            <path d="M ${sx} ${sy} C ${mx} ${sy}, ${mx} ${ty}, ${tx} ${ty}"
                                fill="none" stroke="#94A3B8" stroke-width="2" stroke-dasharray="${this.connecting ? '6,3' : 'none'}"
                            />
                            <!-- Arrowhead -->
                            <polygon points="${tx},${ty} ${tx - 8},${ty - 5} ${tx - 8},${ty + 5}"
                                fill="#94A3B8"/>
                            <!-- Delete edge button (hover area) -->
                            <circle cx="${(sx + tx) / 2}" cy="${(sy + ty) / 2}" r="8"
                                fill="white" stroke="#CBD5E1" stroke-width="1"
                                style="pointer-events:all;cursor:pointer"
                                @click=${() => this.removeEdge(edge.source, edge.target)}
                            />
                            <text x="${(sx + tx) / 2}" y="${(sy + ty) / 2 + 4}" text-anchor="middle"
                                font-size="10" fill="#94A3B8" style="pointer-events:none">×</text>
                            `;
                        })}
                    </svg>

                    <!-- Nodes -->
                    ${this.dagNodes.map(node => {
                        const color = this.nodeColor(node.step_type);
                        const isSelected = this.selectedNode?.id === node.id;
                        const isConnectSource = this.connecting?.fromId === node.id;
                        const paletteItem = PALETTE_ITEMS.find(p => p.type === node.step_type);
                        const icon = paletteItem?.icon || '⬡';

                        return html`
                        <div class="dag-node"
                            style="position:absolute;left:${node.x}px;top:${node.y}px;width:${NODE_W}px;height:${NODE_H}px;cursor:pointer;z-index:${isSelected ? 10 : 1}"
                            @mousedown=${(e: MouseEvent) => this.onNodeMouseDown(node, e)}
                            @click=${(e: Event) => { e.stopPropagation(); this.selectNode(node); }}>

                            <!-- Node body -->
                            <div style="width:100%;height:100%;background:white;border:2px solid ${isSelected ? color : isConnectSource ? '#3B82F6' : '#E5E7EB'};border-radius:10px;box-shadow:${isSelected ? `0 0 0 3px ${color}30, 0 4px 12px rgba(0,0,0,0.1)` : '0 1px 3px rgba(0,0,0,0.06)'};display:flex;align-items:center;gap:8px;padding:0 14px;transition:border-color 150ms,box-shadow 150ms">
                                <div style="width:32px;height:32px;border-radius:8px;background:${color}15;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0">${icon}</div>
                                <div style="flex:1;min-width:0">
                                    <div style="font-size:12px;font-weight:600;color:#1F2937;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${node.name}</div>
                                    <div style="font-size:10px;color:#4B5563">${node.step_type}</div>
                                </div>
                            </div>

                            <!-- Input port (left) -->
                            <div style="position:absolute;left:${-PORT_R}px;top:${NODE_H / 2 - PORT_R}px;width:${PORT_R * 2}px;height:${PORT_R * 2}px;border-radius:50%;background:${this.connecting ? '#3B82F6' : '#CBD5E1'};border:2px solid white;cursor:crosshair;z-index:5"
                                @click=${(e: Event) => { e.stopPropagation(); /* Input port — no action, select node handles it */ }}></div>

                            <!-- Output port (right) -->
                            <div style="position:absolute;right:${-PORT_R}px;top:${NODE_H / 2 - PORT_R}px;width:${PORT_R * 2}px;height:${PORT_R * 2}px;border-radius:50%;background:${isConnectSource ? '#3B82F6' : '#CBD5E1'};border:2px solid white;cursor:crosshair;z-index:5"
                                @click=${(e: Event) => { e.stopPropagation(); this.startConnect(node.id); }}></div>
                        </div>`;
                    })}

                    <!-- Empty state -->
                    ${this.dagNodes.length === 0 ? html`
                    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center">
                        <div style="font-size:48px;opacity:0.15;margin-bottom:12px">⬡</div>
                        <div style="font-size:14px;color:#4B5563;margin-bottom:4px">Drag nodes from the palette to build your pipeline</div>
                        <div style="font-size:12px;color:#CBD5E1">or click a palette item to add it at center</div>
                    </div>` : nothing}
                </div>
            </div>

            <!-- Right: Config Panel / Run History -->
            ${this.showRunHistory ? this.renderRunHistory() : this.renderConfigPanel()}
        </div>`;
    }

    /* ── Config Panel ─────────────────────────────────────────────────── */

    renderConfigPanel() {
        const node = this.selectedNode;
        if (!node) {
            return html`
            <div class="w-72 bg-white border-l border-gray-200 p-4 overflow-y-auto flex-shrink-0">
                <div class="text-center text-gray-500 py-12">
                    <div style="font-size:32px;opacity:0.2;margin-bottom:8px">⚙️</div>
                    <div class="text-sm">Select a node to configure</div>
                </div>
            </div>`;
        }

        const configFields = CONFIG_FIELDS[node.step_type] || [];
        const color = this.nodeColor(node.step_type);
        const paletteItem = PALETTE_ITEMS.find(p => p.type === node.step_type);

        return html`
        <div class="w-72 bg-white border-l border-gray-200 overflow-y-auto flex-shrink-0">
            <div class="p-4 border-b border-gray-100">
                <div class="flex items-center gap-2 mb-3">
                    <div class="w-8 h-8 rounded-lg flex items-center justify-center text-lg" style="background:${color}15">${paletteItem?.icon || '⬡'}</div>
                    <div>
                        <div class="font-semibold text-sm">${node.name}</div>
                        <div class="text-xs text-gray-500">${node.step_type}</div>
                    </div>
                </div>
                <div class="text-xs text-gray-500 mb-2">ID: ${node.id.slice(0, 12)}...</div>
            </div>

            <div class="p-4 space-y-4">
                <!-- Name -->
                <div>
                    <label class="block text-xs font-medium text-gray-500 mb-1">Node Name</label>
                    <input type="text" class="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg"
                        .value=${node.name}
                        @input=${(e: Event) => this.updateNodeName((e.target as HTMLInputElement).value)} />
                </div>

                <!-- Transform-specific config fields -->
                ${configFields.length > 0 ? html`
                <div class="pt-3 border-t border-gray-100">
                    <h5 class="text-xs font-semibold text-gray-500 mb-3">Configuration</h5>
                    ${configFields.map(field => html`
                    <div class="mb-3">
                        <label class="block text-xs font-medium text-gray-500 mb-1">${field.label}</label>
                        ${field.type === 'select' ? html`
                        <select class="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
                            .value=${(node.config[field.key] as string) || ''}
                            @change=${(e: Event) => this.updateNodeConfig(field.key, (e.target as HTMLSelectElement).value)}>
                            <option value="">Select...</option>
                            ${field.key === 'operator' ? html`
                                <option value="==">== (equals)</option>
                                <option value="!=">!= (not equals)</option>
                                <option value=">">> (greater)</option>
                                <option value="<">< (less)</option>
                                <option value=">=">>= (greater or equal)</option>
                                <option value="<="><= (less or equal)</option>
                                <option value="in">in (list contains)</option>
                                <option value="not_in">not in</option>
                                <option value="contains">contains</option>
                                <option value="starts_with">starts with</option>
                                <option value="ends_with">ends with</option>
                            ` : field.key === 'join_type' ? html`
                                <option value="inner">Inner</option>
                                <option value="left">Left</option>
                                <option value="right">Right</option>
                                <option value="full">Full</option>
                            ` : field.key === 'sort_direction' ? html`
                                <option value="asc">Ascending</option>
                                <option value="desc">Descending</option>
                            ` : field.key === 'keep' ? html`
                                <option value="first">First</option>
                                <option value="last">Last</option>
                            ` : field.key === 'flatten_type' ? html`
                                <option value="list">List (explode)</option>
                                <option value="nested_dict">Nested Dict (flatten keys)</option>
                            ` : nothing}
                        </select>` : html`
                        <input type="text" class="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg font-mono"
                            placeholder=${field.placeholder || ''}
                            .value=${(node.config[field.key] as string) || ''}
                            @input=${(e: Event) => this.updateNodeConfig(field.key, (e.target as HTMLInputElement).value)} />`}
                    </div>`)}
                </div>` : nothing}

                <!-- Raw config editor -->
                <div class="pt-3 border-t border-gray-100">
                    <h5 class="text-xs font-semibold text-gray-500 mb-2">Raw Config (JSON)</h5>
                    <textarea class="w-full px-3 py-2 text-xs font-mono border border-gray-200 rounded-lg h-24 resize-none"
                        .value=${JSON.stringify(node.config, null, 2)}
                        @change=${(e: Event) => {
                            try {
                                const parsed = JSON.parse((e.target as HTMLTextAreaElement).value);
                                this.selectedNode = { ...node, config: parsed };
                                this.dagNodes = this.dagNodes.map(n => n.id === node.id ? this.selectedNode! : n);
                            } catch { /* ignore invalid JSON */ }
                        }}></textarea>
                </div>

                <!-- Connected edges -->
                <div class="pt-3 border-t border-gray-100">
                    <h5 class="text-xs font-semibold text-gray-500 mb-2">Connections</h5>
                    ${(() => {
                        const incoming = this.dagEdges.filter(e => e.target === node.id);
                        const outgoing = this.dagEdges.filter(e => e.source === node.id);
                        return html`
                        ${incoming.length > 0 ? html`
                        <div class="mb-2">
                            <div class="text-xs text-gray-500 mb-1">Inputs:</div>
                            ${incoming.map(e => {
                                const srcNode = this.dagNodes.find(n => n.id === e.source);
                                return html`<div class="text-xs flex items-center gap-1 mb-0.5">
                                    <span style="color:${this.nodeColor(srcNode?.step_type || '')}">${srcNode?.name || e.source.slice(0, 8)}</span>
                                    <button class="text-red-400 hover:text-red-600 ml-auto" @click=${() => this.removeEdge(e.source, e.target)}>×</button>
                                </div>`;
                            })}
                        </div>` : nothing}
                        ${outgoing.length > 0 ? html`
                        <div>
                            <div class="text-xs text-gray-500 mb-1">Outputs:</div>
                            ${outgoing.map(e => {
                                const tgtNode = this.dagNodes.find(n => n.id === e.target);
                                return html`<div class="text-xs flex items-center gap-1 mb-0.5">
                                    <span style="color:${this.nodeColor(tgtNode?.step_type || '')}">${tgtNode?.name || e.target.slice(0, 8)}</span>
                                    <button class="text-red-400 hover:text-red-600 ml-auto" @click=${() => this.removeEdge(e.source, e.target)}>×</button>
                                </div>`;
                            })}
                        </div>` : nothing}
                        ${incoming.length === 0 && outgoing.length === 0 ? html`
                        <div class="text-xs text-gray-500">No connections</div>` : nothing}`;
                    })()}
                </div>

                <!-- Actions -->
                <div class="pt-3 border-t border-gray-100 flex gap-2">
                    <button class="flex-1 px-3 py-1.5 text-xs border border-blue-200 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100"
                        @click=${() => this.startConnect(node.id)}>
                        Connect →
                    </button>
                    <button class="px-3 py-1.5 text-xs border border-red-200 rounded-lg bg-red-50 text-red-600 hover:bg-red-100"
                        @click=${() => this.removeNode(node.id)}>
                        Delete
                    </button>
                </div>
            </div>
        </div>`;
    }

    /* ── Run History Panel ────────────────────────────────────────────── */

    renderRunHistory() {
        return html`
        <div class="w-80 bg-white border-l border-gray-200 overflow-y-auto flex-shrink-0">
            <div class="sticky top-0 bg-white border-b border-gray-100 px-4 py-3 flex items-center justify-between">
                <h4 class="text-sm font-semibold">Run History</h4>
                <button class="text-gray-500 hover:text-ink text-sm" @click=${() => { this.showRunHistory = false; }}>×</button>
            </div>
            <div class="p-3">
                ${this.runsLoading ? html`
                <div class="text-center text-gray-500 py-8 text-xs">Loading runs...</div>` :
                this.pipelineRuns.length === 0 ? html`
                <div class="text-center text-gray-500 py-8 text-xs">No runs yet</div>` : html`
                <div class="space-y-2">
                    ${this.pipelineRuns.map(run => html`
                    <div class="p-3 rounded-lg border border-gray-100 hover:border-gray-200 bg-gray-50">
                        <div class="flex items-center justify-between mb-1.5">
                            <span class="font-mono text-xs text-gray-500">${run.id.slice(0, 8)}</span>
                            ${this.statusBadge(run.status)}
                        </div>
                        <div class="grid grid-cols-2 gap-1 text-xs text-gray-500">
                            <div>Trigger: ${run.trigger_type}</div>
                            <div>By: ${run.triggered_by || '-'}</div>
                            <div>Steps: ${run.steps_completed}/${run.steps_total}</div>
                            <div>Duration: ${this.formatDuration(run.started_at, run.completed_at)}</div>
                        </div>
                        <div class="text-xs text-gray-500 mt-1.5">${run.started_at ? new Date(run.started_at).toLocaleString() : 'Not started'}</div>
                        ${run.error_message ? html`
                        <div class="text-xs text-red-500 mt-1.5 truncate">${run.error_message}</div>` : nothing}
                    </div>`)}
                </div>`}
            </div>
        </div>`;
    }
}
