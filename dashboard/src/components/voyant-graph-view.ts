import { LitElement, html, svg } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

/* ──────────────────────────────────────────────
   Types
   ────────────────────────────────────────────── */

export interface GraphNode {
    id: string;
    label: string;
    type: string;
    size?: number;
    color?: string;
    data?: Record<string, unknown>;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    label?: string;
}

interface SimNode extends GraphNode {
    x: number;
    y: number;
    vx: number;
    vy: number;
    expanded?: boolean;
}

type LayoutMode = 'force' | 'hierarchical';

const TYPE_COLORS: Record<string, string> = {
    object_type: '#FF4D00',
    Cliente: '#FF4D00',
    Plan: '#3B82F6',
    Servicio: '#22C55E',
    Factura: '#F59E0B',
    TicketSoporte: '#EF4444',
    NodoRed: '#8B5CF6',
    ZonaCobertura: '#06B6D4',
    default: '#FF4D00',
};

/* ──────────────────────────────────────────────
   Physics constants
   ────────────────────────────────────────────── */

const REPULSION_K = 100;
const ATTRACTION_K = 0.01;
const GRAVITY_K = 0.02;
const DAMPING = 0.95;
const MIN_DISTANCE = 60;
const MIN_ZOOM = 0.1;
const MAX_ZOOM = 10;
const MINIMAP_W = 160;
const MINIMAP_H = 120;
const TARGET_FRAME_MS = 16; // ~60 fps

/* ──────────────────────────────────────────────
   Component
   ────────────────────────────────────────────── */

@customElement('voyant-graph-view')
export class VoyantGraphView extends LitElement {
    /* ---- public properties ---- */
    @property({ type: Array }) nodes: GraphNode[] = [];
    @property({ type: Array }) edges: GraphEdge[] = [];
    @property({ type: String }) apiUrl = '/api';

    /* ---- internal state ---- */
    @state() private _selectedNode: SimNode | null = null;
    @state() private _layoutMode: LayoutMode = 'force';
    @state() private _searchQuery = '';
    @state() private _zoom = 1;
    @state() private _panX = 0;
    @state() private _panY = 0;
    @state() private _tick = 0; // bumped each frame to trigger re-render

    /* ---- simulation bookkeeping (non-reactive) ---- */
    private _simNodes: SimNode[] = [];
    private _simNodeMap = new Map<string, SimNode>();
    private _rafId = 0;
    private _lastFrame = 0;
    private _paused = false;
    private _canvasW = 1120;
    private _canvasH = 520;
    private _draggingNode: SimNode | null = null;
    private _panning = false;
    private _panStartX = 0;
    private _panStartY = 0;
    private _panStartPanX = 0;
    private _panStartPanY = 0;
    private _containerRef: HTMLElement | null = null;

    /* ── Shadow DOM disabled (spec) ── */
    createRenderRoot() { return this; }

    /* ────────────────────────────────────────────
       Lifecycle
       ──────────────────────────────────────────── */

    connectedCallback() {
        super.connectedCallback();
        this._initSimulation();
        this._startLoop();
        document.addEventListener('visibilitychange', this._onVisibility);
        this.addEventListener('wheel', this._onWheel, { passive: false });
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        cancelAnimationFrame(this._rafId);
        document.removeEventListener('visibilitychange', this._onVisibility);
        this.removeEventListener('wheel', this._onWheel);
    }

    updated(changed: Map<string, unknown>) {
        if (changed.has('nodes') || changed.has('edges')) {
            this._initSimulation();
        }
    }

    /* ────────────────────────────────────────────
       Simulation
       ──────────────────────────────────────────── */

    private _initSimulation() {
        // Preserve positions for existing nodes
        const oldMap = new Map(this._simNodes.map(n => [n.id, n]));
        this._simNodes = this.nodes.map(n => {
            const old = oldMap.get(n.id);
            if (old) {
                // carry over position + velocity
                old.label = n.label;
                old.type = n.type;
                old.size = n.size;
                old.color = n.color;
                old.data = n.data;
                return old;
            }
            // New node: random position near center
            return {
                ...n,
                x: this._canvasW / 2 + (Math.random() - 0.5) * 200,
                y: this._canvasH / 2 + (Math.random() - 0.5) * 200,
                vx: 0,
                vy: 0,
                expanded: false,
            };
        });
        this._simNodeMap = new Map(this._simNodes.map(n => [n.id, n]));

        if (this._layoutMode === 'hierarchical') {
            this._applyHierarchicalLayout();
        }
    }

    /** Force-directed step (Velocity Verlet-lite) */
    private _stepForce() {
        const nodes = this._simNodes;
        const n = nodes.length;
        if (n === 0) return;

        const cx = this._canvasW / 2;
        const cy = this._canvasH / 2;

        // Reset forces → apply as acceleration into vx/vy directly
        for (let i = 0; i < n; i++) {
            const a = nodes[i];
            if (a === this._draggingNode) continue;

            let fx = 0;
            let fy = 0;

            // Repulsion (Coulomb) — O(n^2), fine for <500 nodes
            for (let j = 0; j < n; j++) {
                if (i === j) continue;
                const b = nodes[j];
                let dx = a.x - b.x;
                let dy = a.y - b.y;
                let dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; dist = 1; }
                const force = REPULSION_K / (dist * dist);
                fx += (dx / dist) * force;
                fy += (dy / dist) * force;
            }

            // Attraction (Hooke) along edges
            for (const edge of this.edges) {
                let other: SimNode | undefined;
                if (edge.source === a.id) other = this._simNodeMap.get(edge.target);
                else if (edge.target === a.id) other = this._simNodeMap.get(edge.source);
                if (!other) continue;
                const dx = other.x - a.x;
                const dy = other.y - a.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                fx += ATTRACTION_K * dx;
                fy += ATTRACTION_K * dy;
            }

            // Center gravity
            fx += (cx - a.x) * GRAVITY_K;
            fy += (cy - a.y) * GRAVITY_K;

            // Integrate
            a.vx = (a.vx + fx) * DAMPING;
            a.vy = (a.vy + fy) * DAMPING;
        }

        // Collision detection — enforce minimum distance
        for (let i = 0; i < n; i++) {
            for (let j = i + 1; j < n; j++) {
                const a = nodes[i];
                const b = nodes[j];
                let dx = b.x - a.x;
                let dy = b.y - a.y;
                let dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < MIN_DISTANCE && dist > 0.01) {
                    const overlap = (MIN_DISTANCE - dist) / 2;
                    const nx = dx / dist;
                    const ny = dy / dist;
                    if (a !== this._draggingNode) { a.x -= nx * overlap; a.y -= ny * overlap; }
                    if (b !== this._draggingNode) { b.x += nx * overlap; b.y += ny * overlap; }
                }
            }
        }

        // Apply velocity
        for (const node of nodes) {
            if (node === this._draggingNode) continue;
            node.x += node.vx;
            node.y += node.vy;
        }
    }

    /** Hierarchical (top-down tree) layout — computed once */
    private _applyHierarchicalLayout() {
        // Build adjacency from edges (source → targets)
        const children = new Map<string, string[]>();
        const hasParent = new Set<string>();
        for (const e of this.edges) {
            if (!children.has(e.source)) children.set(e.source, []);
            children.get(e.source)!.push(e.target);
            hasParent.add(e.target);
        }
        // Roots = nodes with no incoming edge
        const roots = this._simNodes.filter(n => !hasParent.has(n.id)).map(n => n.id);
        if (roots.length === 0 && this._simNodes.length > 0) {
            roots.push(this._simNodes[0].id);
        }

        // BFS level assignment
        const level = new Map<string, number>();
        const queue: string[] = [...roots];
        for (const r of roots) level.set(r, 0);
        while (queue.length) {
            const id = queue.shift()!;
            const lvl = level.get(id)!;
            for (const child of children.get(id) || []) {
                if (!level.has(child)) {
                    level.set(child, lvl + 1);
                    queue.push(child);
                }
            }
        }
        // Orphans
        for (const node of this._simNodes) {
            if (!level.has(node.id)) level.set(node.id, 0);
        }

        // Group by level
        const maxLvl = Math.max(...level.values(), 0);
        const groups: string[][] = Array.from({ length: maxLvl + 1 }, () => []);
        for (const [id, lvl] of level) groups[lvl].push(id);

        const yStep = this._canvasH / (maxLvl + 2);
        for (let lvl = 0; lvl <= maxLvl; lvl++) {
            const ids = groups[lvl];
            const xStep = this._canvasW / (ids.length + 1);
            for (let i = 0; i < ids.length; i++) {
                const node = this._simNodeMap.get(ids[i]);
                if (node) {
                    node.x = xStep * (i + 1);
                    node.y = yStep * (lvl + 1);
                    node.vx = 0;
                    node.vy = 0;
                }
            }
        }
    }

    /* ────────────────────────────────────────────
       Render loop (rAF, 60fps throttle)
       ──────────────────────────────────────────── */

    private _startLoop() {
        const loop = (now: number) => {
            this._rafId = requestAnimationFrame(loop);
            if (this._paused) return;
            if (now - this._lastFrame < TARGET_FRAME_MS) return;
            this._lastFrame = now;

            if (this._layoutMode === 'force') {
                this._stepForce();
            }
            this._tick++;
            this.requestUpdate();
        };
        this._rafId = requestAnimationFrame(loop);
    }

    private _onVisibility = () => {
        this._paused = document.hidden;
    };

    /* ────────────────────────────────────────────
       Zoom / Pan
       ──────────────────────────────────────────── */

    private _onWheel = (e: WheelEvent) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        this._zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, this._zoom * delta));
    };

    private _onContainerMouseDown = (e: MouseEvent) => {
        // Only pan on empty space (not on a node)
        if ((e.target as HTMLElement).closest('.graph-node')) return;
        this._panning = true;
        this._panStartX = e.clientX;
        this._panStartY = e.clientY;
        this._panStartPanX = this._panX;
        this._panStartPanY = this._panY;
        const onMove = (ev: MouseEvent) => {
            if (!this._panning) return;
            this._panX = this._panStartPanX + (ev.clientX - this._panStartX);
            this._panY = this._panStartPanY + (ev.clientY - this._panStartY);
        };
        const onUp = () => {
            this._panning = false;
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    };

    private _zoomToFit() {
        if (this._simNodes.length === 0) {
            this._zoom = 1;
            this._panX = 0;
            this._panY = 0;
            return;
        }
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const n of this._simNodes) {
            const r = this._nodeRadius(n);
            minX = Math.min(minX, n.x - r);
            minY = Math.min(minY, n.y - r);
            maxX = Math.max(maxX, n.x + r);
            maxY = Math.max(maxY, n.y + r);
        }
        const graphW = maxX - minX || 1;
        const graphH = maxY - minY || 1;
        const pad = 40;
        const scaleX = (this._canvasW - pad * 2) / graphW;
        const scaleY = (this._canvasH - pad * 2) / graphH;
        this._zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.min(scaleX, scaleY)));
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        this._panX = this._canvasW / 2 - centerX * this._zoom;
        this._panY = this._canvasH / 2 - centerY * this._zoom;
    }

    /* ────────────────────────────────────────────
       Node interaction
       ──────────────────────────────────────────── */

    private _onNodeClick(node: SimNode) {
        this._selectedNode = node;
        this.dispatchEvent(new CustomEvent('node-click', { detail: node }));
    }

    private _onNodeDblClick(node: SimNode) {
        if (node.expanded) return;
        node.expanded = true;
        this.dispatchEvent(new CustomEvent('node-expand', {
            detail: { node, loadLinked: true },
            bubbles: true,
            composed: true,
        }));
        // Attempt API fetch for linked types
        this._expandNode(node);
    }

    private async _expandNode(node: SimNode) {
        try {
            const res = await fetch(`${this.apiUrl}/ontology/types/${encodeURIComponent(node.id)}/links`);
            if (!res.ok) return;
            const links: Array<{ name: string; source_type: string; target_type: string }> = await res.json();
            // Emit data so parent can merge into nodes/edges
            this.dispatchEvent(new CustomEvent('node-expanded', {
                detail: { parentNode: node, links },
                bubbles: true,
                composed: true,
            }));
        } catch {
            // API not available — graceful degradation
        }
    }

    private _onNodeDragStart(node: SimNode, e: MouseEvent) {
        e.stopPropagation();
        this._draggingNode = node;
        const onMove = (ev: MouseEvent) => {
            // Convert screen coords to graph coords
            const rect = this._containerRef?.getBoundingClientRect();
            if (!rect) return;
            node.x = (ev.clientX - rect.left - this._panX) / this._zoom;
            node.y = (ev.clientY - rect.top - this._panY) / this._zoom;
            node.vx = 0;
            node.vy = 0;
        };
        const onUp = () => {
            this._draggingNode = null;
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    }

    /* ────────────────────────────────────────────
       Search
       ──────────────────────────────────────────── */

    private _onSearchInput(e: Event) {
        this._searchQuery = (e.target as HTMLInputElement).value;
    }

    private _isMatch(node: SimNode): boolean {
        if (!this._searchQuery) return true;
        const q = this._searchQuery.toLowerCase();
        return node.label.toLowerCase().includes(q) ||
               node.type.toLowerCase().includes(q) ||
               node.id.toLowerCase().includes(q);
    }

    /* ────────────────────────────────────────────
       Helpers
       ──────────────────────────────────────────── */

    private _getNodeColor(node: GraphNode): string {
        return node.color || TYPE_COLORS[node.label] || TYPE_COLORS[node.type] || TYPE_COLORS.default;
    }

    private _nodeRadius(node: GraphNode): number {
        return Math.max(28, Math.min(50, (node.size || 10) * 2 + 20));
    }

    /* ────────────────────────────────────────────
       Minimap
       ──────────────────────────────────────────── */

    private _renderMinimap() {
        if (this._simNodes.length === 0) return html``;

        // Compute bounds
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const n of this._simNodes) {
            minX = Math.min(minX, n.x);
            minY = Math.min(minY, n.y);
            maxX = Math.max(maxX, n.x);
            maxY = Math.max(maxY, n.y);
        }
        const pad = 20;
        minX -= pad; minY -= pad; maxX += pad; maxY += pad;
        const gw = maxX - minX || 1;
        const gh = maxY - minY || 1;
        const scale = Math.min(MINIMAP_W / gw, MINIMAP_H / gh);

        return svg`
        <svg
            style="position:absolute;bottom:12px;right:12px;width:${MINIMAP_W}px;height:${MINIMAP_H}px;background:rgba(255,255,255,0.92);border:1px solid #E5E7EB;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.08);pointer-events:none;z-index:20"
            viewBox="0 0 ${MINIMAP_W} ${MINIMAP_H}"
        >
            ${this.edges.map(e => {
                const s = this._simNodeMap.get(e.source);
                const t = this._simNodeMap.get(e.target);
                if (!s || !t) return svg``;
                return svg`<line
                    x1="${(s.x - minX) * scale}" y1="${(s.y - minY) * scale}"
                    x2="${(t.x - minX) * scale}" y2="${(t.y - minY) * scale}"
                    stroke="#D1D5DB" stroke-width="0.5"
                />`;
            })}
            ${this._simNodes.map(n => svg`<circle
                cx="${(n.x - minX) * scale}" cy="${(n.y - minY) * scale}"
                r="2" fill="${this._getNodeColor(n)}"
            />`)}
            <!-- Viewport rectangle -->
            <rect
                x="${(-this._panX / this._zoom - minX) * scale}"
                y="${(-this._panY / this._zoom - minY) * scale}"
                width="${(this._canvasW / this._zoom) * scale}"
                height="${(this._canvasH / this._zoom) * scale}"
                fill="none" stroke="#FF4D00" stroke-width="1" rx="1"
            />
        </svg>`;
    }

    /* ────────────────────────────────────────────
       Render
       ──────────────────────────────────────────── */

    render() {
        // Bump _tick to force re-render (we update it in rAF)
        void this._tick;

        const searchActive = this._searchQuery.length > 0;

        return html`
        <div
            style="position:relative;width:100%;height:520px;background:#FAFAFA;border-radius:12px;overflow:hidden;cursor:${this._panning ? 'grabbing' : 'grab'}"
            @mousedown=${this._onContainerMouseDown}
            ${/* capture ref for coordinate transforms */ ''}
        >
            <!-- Controls bar -->
            <div style="position:absolute;top:8px;left:8px;right:8px;display:flex;gap:6px;align-items:center;z-index:30;pointer-events:auto">
                <!-- Search -->
                <input
                    type="text"
                    placeholder="Search nodes..."
                    .value=${this._searchQuery}
                    @input=${this._onSearchInput}
                    style="flex:0 1 200px;padding:5px 10px;border:1px solid #E5E7EB;border-radius:6px;font-size:12px;background:white;outline:none;font-family:Inter,sans-serif"
                />

                <!-- Layout toggle -->
                <button
                    @click=${() => {
                        this._layoutMode = this._layoutMode === 'force' ? 'hierarchical' : 'force';
                        if (this._layoutMode === 'hierarchical') this._applyHierarchicalLayout();
                    }}
                    style="padding:5px 10px;border:1px solid #E5E7EB;border-radius:6px;background:white;font-size:11px;cursor:pointer;font-family:Inter,sans-serif;color:#374151"
                    title="Toggle layout"
                >
                    ${this._layoutMode === 'force' ? '⚡ Force' : '🏗️ Tree'}
                </button>

                <!-- Zoom controls -->
                <button @click=${() => { this._zoom = Math.min(MAX_ZOOM, this._zoom * 1.25); }}
                    style="width:28px;height:28px;border:1px solid #E5E7EB;border-radius:6px;background:white;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center">+</button>
                <span style="font-size:11px;color:#6B7280;min-width:40px;text-align:center;font-family:Inter,sans-serif">${(this._zoom * 100).toFixed(0)}%</span>
                <button @click=${() => { this._zoom = Math.max(MIN_ZOOM, this._zoom * 0.8); }}
                    style="width:28px;height:28px;border:1px solid #E5E7EB;border-radius:6px;background:white;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center">−</button>
                <button @click=${() => this._zoomToFit()}
                    style="padding:5px 10px;border:1px solid #E5E7EB;border-radius:6px;background:white;font-size:11px;cursor:pointer;font-family:Inter,sans-serif;color:#374151"
                    title="Zoom to fit">⊞ Fit</button>
            </div>

            <!-- Main graph canvas with zoom/pan transform -->
            <div
                style="position:absolute;top:0;left:0;width:100%;height:100%;transform-origin:0 0;transform:translate(${this._panX}px,${this._panY}px) scale(${this._zoom})"
            >
                <!-- SVG edges layer -->
                <svg style="position:absolute;top:0;left:0;width:${this._canvasW}px;height:${this._canvasH}px;pointer-events:none;overflow:visible">
                    ${this.edges.map(e => {
                        const s = this._simNodeMap.get(e.source);
                        const t = this._simNodeMap.get(e.target);
                        if (!s || !t) return svg``;

                        const dimmed = searchActive && (!this._isMatch(s) || !this._isMatch(t));

                        // Bezier curve: slight offset for visual curve
                        const dx = t.x - s.x;
                        const dy = t.y - s.y;
                        const mx = (s.x + t.x) / 2;
                        const my = (s.y + t.y) / 2;
                        // Perpendicular offset for curve
                        const len = Math.sqrt(dx * dx + dy * dy) || 1;
                        const offX = (-dy / len) * 15;
                        const offY = (dx / len) * 15;

                        return svg`
                        <path
                            d="M ${s.x} ${s.y} Q ${mx + offX} ${my + offY} ${t.x} ${t.y}"
                            fill="none"
                            stroke="${dimmed ? '#E5E7EB' : '#D1D5DB'}"
                            stroke-width="2"
                            opacity="${dimmed ? 0.3 : 0.8}"
                        />
                        <text
                            x="${mx + offX * 0.5}" y="${my + offY * 0.5 - 4}"
                            text-anchor="middle"
                            fill="${dimmed ? '#E5E7EB' : '#9CA3AF'}"
                            font-size="9" font-family="Inter,sans-serif"
                        >${e.label || ''}</text>
                        <!-- Arrowhead at target -->
                        <polygon
                            points="${t.x},${t.y - 14} ${t.x - 5},${t.y - 22} ${t.x + 5},${t.y - 22}"
                            fill="${dimmed ? '#E5E7EB' : '#D1D5DB'}"
                            opacity="${dimmed ? 0.3 : 0.8}"
                        />`;
                    })}
                </svg>

                <!-- Nodes -->
                ${this._simNodes.map(node => {
                    const color = this._getNodeColor(node);
                    const r = this._nodeRadius(node);
                    const isSelected = this._selectedNode?.id === node.id;
                    const matched = this._isMatch(node);
                    const dimmed = searchActive && !matched;

                    return html`
                    <div
                        class="graph-node"
                        style="position:absolute;left:${node.x - r}px;top:${node.y - r}px;width:${r * 2}px;height:${r * 2}px;cursor:pointer;transition:transform 150ms;z-index:${isSelected ? 10 : 1};opacity:${dimmed ? 0.2 : 1}"
                        @click=${() => this._onNodeClick(node)}
                        @dblclick=${() => this._onNodeDblClick(node)}
                        @mousedown=${(e: MouseEvent) => this._onNodeDragStart(node, e)}
                        @mouseenter=${(e: Event) => { if (!dimmed) (e.currentTarget as HTMLElement).style.transform = 'scale(1.1)'; }}
                        @mouseleave=${(e: Event) => { (e.currentTarget as HTMLElement).style.transform = 'scale(1)'; }}
                    >
                        <div style="width:100%;height:100%;border-radius:50%;background:${color};${isSelected ? `box-shadow:0 0 0 4px ${color}40,0 4px 12px rgba(0,0,0,0.15);` : 'box-shadow:0 2px 8px rgba(0,0,0,0.1);'}display:flex;flex-direction:column;align-items:center;justify-content:center">
                            <div style="color:white;font-size:${r > 35 ? '12' : '10'}px;font-weight:700;text-align:center;line-height:1.2;padding:4px">${node.label}</div>
                            ${node.size ? html`<div style="color:rgba(255,255,255,0.75);font-size:9px">${node.size}</div>` : ''}
                        </div>
                        ${node.expanded ? html`<div style="position:absolute;top:-4px;right:-4px;width:10px;height:10px;border-radius:50%;background:#22C55E;border:2px solid white"></div>` : ''}
                    </div>`;
                })}
            </div>

            <!-- Minimap (SVG overlay, fixed position) -->
            ${this._renderMinimap()}

            <!-- Legend -->
            <div style="position:absolute;bottom:12px;left:12px;background:white;border:1px solid #E5E7EB;border-radius:8px;padding:8px 12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);z-index:20">
                ${[...new Set(this.nodes.map(n => n.type))].map(t => html`
                <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:#6B7280;margin:2px 0">
                    <div style="width:8px;height:8px;border-radius:50%;background:${TYPE_COLORS[t] || TYPE_COLORS.default}"></div>
                    ${t.replace(/_/g, ' ')}
                </div>`)}
            </div>

            <!-- Node count / status -->
            <div style="position:absolute;bottom:12px;left:50%;transform:translateX(-50%);font-size:10px;color:#9CA3AF;z-index:20;font-family:Inter,sans-serif">
                ${this._simNodes.length} nodes · ${this.edges.length} edges · ${this._layoutMode} layout
            </div>

            <!-- Empty state -->
            ${this._simNodes.length === 0 ? html`
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:8px">
                <div style="font-size:32px;opacity:0.2">🕸️</div>
                <div style="font-size:13px;color:#9CA3AF">No data to visualize</div>
            </div>` : ''}
        </div>`;
    }
}
