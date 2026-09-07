import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import Graph from 'graphology';
import Sigma from 'sigma';

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
    color?: string;
    data?: Record<string, unknown>;
}

const TYPE_COLORS: Record<string, string> = {
    object_type: '#FF4D00',
    link_type: '#3B82F6',
    interface: '#8B5CF6',
    struct: '#10B981',
    shared_property: '#F59E0B',
    value_type: '#EC4899',
    action: '#EF4444',
    function: '#06B6D4',
    instance: '#6B7280',
    default: '#FF4D00',
};

@customElement('voyant-graph-view')
export class VoyantGraphView extends LitElement {
    @property({ type: Array }) nodes: GraphNode[] = [];
    @property({ type: Array }) edges: GraphEdge[] = [];
    @property({ type: String }) layout = 'force';
    @property({ type: Boolean }) interactive = true;

    @state() selectedNode: GraphNode | null = null;
    @state() hoveredNode: GraphNode | null = null;

    private container: HTMLElement | null = null;
    private sigma: Sigma | null = null;
    private graph: Graph | null = null;

    createRenderRoot() { return this; }

    static styles = css`
        :host { display: block; position: relative; width: 100%; height: 100%; }
        .graph-container { width: 100%; height: 100%; min-height: 400px; background: var(--voyant-bg-canvas, #0A0A0A); border-radius: 12px; overflow: hidden; }
        .controls { position: absolute; top: 12px; right: 12px; display: flex; gap: 4px; z-index: 10; }
        .controls button { width: 32px; height: 32px; border-radius: 8px; border: 1px solid var(--voyant-border, #262626); background: var(--voyant-bg-elevated, #141414); color: var(--voyant-text, #FAFAFA); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px; }
        .controls button:hover { background: var(--voyant-bg-hover, #1A1A1A); }
        .legend { position: absolute; bottom: 12px; left: 12px; background: var(--voyant-bg-elevated, #141414); border: 1px solid var(--voyant-border, #262626); border-radius: 8px; padding: 8px 12px; z-index: 10; }
        .legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--voyant-text-secondary, #9CA3AF); margin: 2px 0; }
        .legend-dot { width: 8px; height: 8px; border-radius: 50%; }
        .tooltip { position: absolute; background: var(--voyant-bg-elevated, #141414); border: 1px solid var(--voyant-border, #262626); border-radius: 8px; padding: 8px 12px; font-size: 12px; color: var(--voyant-text, #FAFAFA); pointer-events: none; z-index: 20; max-width: 240px; }
        .tooltip-label { font-weight: 600; margin-bottom: 4px; }
        .tooltip-meta { color: var(--voyant-text-secondary, #9CA3AF); font-size: 11px; }
    `;

    firstUpdated() {
        this.container = this.renderRoot.querySelector('.graph-container') as HTMLElement;
        this._buildGraph();
    }

    updated(changed: Map<string, unknown>) {
        if (changed.has('nodes') || changed.has('edges')) {
            this._buildGraph();
        }
    }

    disconnectedCallback() {
        this.sigma?.kill();
        super.disconnectedCallback();
    }

    private _buildGraph() {
        if (!this.container) return;
        this.sigma?.kill();

        this.graph = new Graph();
        for (const node of this.nodes) {
            this.graph.addNode(node.id, {
                label: node.label,
                size: node.size || 12,
                color: node.color || TYPE_COLORS[node.type] || TYPE_COLORS.default,
                x: Math.random() * 10,
                y: Math.random() * 10,
                type: node.type,
                data: node.data || {},
            });
        }
        for (const edge of this.edges) {
            if (this.graph.hasNode(edge.source) && this.graph.hasNode(edge.target)) {
                this.graph.addEdge(edge.source, edge.target, {
                    label: edge.label || '',
                    color: edge.color || 'rgba(255,255,255,0.15)',
                    size: 1.5,
                    data: edge.data || {},
                });
            }
        }

        this.sigma = new Sigma(this.graph, this.container, {
            renderEdgeLabels: true,
            labelFont: 'Inter, system-ui, sans-serif',
            labelSize: 11,
            labelColor: { color: '#FAFAFA' },
            labelWeight: '600',
            edgeLabelFont: 'Inter, system-ui, sans-serif',
            edgeLabelSize: 9,
            edgeLabelColor: { color: 'rgba(255,255,255,0.5)' },
            defaultEdgeColor: 'rgba(255,255,255,0.15)',
            defaultNodeColor: '#FF4D00',
            minCameraRatio: 0.1,
            maxCameraRatio: 10,
            enableEdgeEvents: false,
        });

        this.sigma.on('enterNode', ({ node }) => {
            const attrs = this.graph!.getNodeAttributes(node);
            this.hoveredNode = { id: node, label: attrs.label, type: attrs.type, data: attrs.data };
        });
        this.sigma.on('leaveNode', () => { this.hoveredNode = null; });
        this.sigma.on('clickNode', ({ node }) => {
            const attrs = this.graph!.getNodeAttributes(node);
            this.selectedNode = { id: node, label: attrs.label, type: attrs.type, data: attrs.data };
            this.dispatchEvent(new CustomEvent('node-click', { detail: this.selectedNode }));
        });
        this.sigma.on('clickStage', () => {
            this.selectedNode = null;
            this.dispatchEvent(new CustomEvent('node-deselect'));
        });
    }

    private _zoomIn() { this.sigma?.getCamera().animatedZoom({ duration: 200 }); }
    private _zoomOut() { this.sigma?.getCamera().animatedUnzoom({ duration: 200 }); }
    private _resetView() { this.sigma?.getCamera().animatedReset({ duration: 300 }); }

    render() {
        const types = [...new Set(this.nodes.map(n => n.type))];
        return html`
            <div class="graph-container"></div>
            <div class="controls">
                <button @click=${this._zoomIn} title="Zoom in">+</button>
                <button @click=${this._zoomOut} title="Zoom out">−</button>
                <button @click=${this._resetView} title="Reset view">⌂</button>
            </div>
            <div class="legend">
                ${types.map(t => html`
                    <div class="legend-item">
                        <div class="legend-dot" style="background:${TYPE_COLORS[t] || TYPE_COLORS.default}"></div>
                        ${t.replace(/_/g, ' ')}
                    </div>
                `)}
            </div>
            ${this.hoveredNode ? html`
                <div class="tooltip" style="left:${(this.hoveredNode as any)._x || 200}px;top:${(this.hoveredNode as any)._y || 200}px">
                    <div class="tooltip-label">${this.hoveredNode.label}</div>
                    <div class="tooltip-meta">${this.hoveredNode.type} · ${this.hoveredNode.id}</div>
                </div>
            ` : ''}
        `;
    }
}
