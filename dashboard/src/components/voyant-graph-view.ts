import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

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

@customElement('voyant-graph-view')
export class VoyantGraphView extends LitElement {
    @property({ type: Array }) nodes: GraphNode[] = [];
    @property({ type: Array }) edges: GraphEdge[] = [];

    @state() selectedNode: GraphNode | null = null;

    createRenderRoot() { return this; }

    connectedCallback() {
        super.connectedCallback();
        // Force render when connected to DOM
        this.requestUpdate();
    }

    private _layoutNodes(): Array<GraphNode & { x: number; y: number }> {
        const n = this.nodes.length;
        if (n === 0) return [];

        const cx = 560;
        const cy = 260;
        const rx = Math.min(400, n * 50);
        const ry = Math.min(200, n * 25);

        return this.nodes.map((node, i) => {
            const angle = (2 * Math.PI * i) / n - Math.PI / 2;
            return {
                ...node,
                x: cx + rx * Math.cos(angle),
                y: cy + ry * Math.sin(angle),
            };
        });
    }

    private _getNodeColor(node: GraphNode): string {
        return node.color || TYPE_COLORS[node.label] || TYPE_COLORS[node.type] || TYPE_COLORS.default;
    }

    private _onNodeClick(node: GraphNode) {
        this.selectedNode = node;
        this.dispatchEvent(new CustomEvent('node-click', { detail: node }));
    }

    render() {
        const laid = this._layoutNodes();
        const nodeMap = new Map(laid.map(n => [n.id, n]));

        return html`
        <div style="position:relative;width:100%;height:520px;background:#FAFAFA;border-radius:12px;overflow:hidden">
            <!-- SVG edges -->
            <svg style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none">
                ${this.edges.map(e => {
                    const s = nodeMap.get(e.source);
                    const t = nodeMap.get(e.target);
                    if (!s || !t) return html``;
                    const mx = (s.x + t.x) / 2;
                    const my = (s.y + t.y) / 2 - 12;
                    return html`
                    <line x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" stroke="#D1D5DB" stroke-width="2" />
                    <text x="${mx}" y="${my}" text-anchor="middle" fill="#9CA3AF" font-size="10" font-family="Inter,sans-serif">${e.label || ''}</text>
                    <polygon points="${t.x},${t.y - 14} ${t.x - 5},${t.y - 22} ${t.x + 5},${t.y - 22}" fill="#D1D5DB" />
                    `;
                })}
            </svg>

            <!-- Nodes -->
            ${laid.map(node => {
                const color = this._getNodeColor(node);
                const r = Math.max(28, Math.min(50, (node.size || 10) * 2 + 20));
                const isSelected = this.selectedNode?.id === node.id;
                return html`
                <div style="position:absolute;left:${node.x - r}px;top:${node.y - r}px;width:${r * 2}px;height:${r * 2}px;cursor:pointer;transition:transform 200ms;z-index:${isSelected ? 10 : 1}"
                    @click=${() => this._onNodeClick(node)}
                    @mouseenter=${(e: Event) => { (e.currentTarget as HTMLElement).style.transform = 'scale(1.1)'; }}
                    @mouseleave=${(e: Event) => { (e.currentTarget as HTMLElement).style.transform = 'scale(1)'; }}>
                    <div style="width:100%;height:100%;border-radius:50%;background:${color};${isSelected ? `box-shadow:0 0 0 4px ${color}40,0 4px 12px rgba(0,0,0,0.15);` : 'box-shadow:0 2px 8px rgba(0,0,0,0.1);'}display:flex;flex-direction:column;align-items:center;justify-content:center">
                        <div style="color:white;font-size:${r > 35 ? '12' : '10'}px;font-weight:700;text-align:center;line-height:1.2;padding:4px">${node.label}</div>
                    </div>
                </div>`;
            })}

            <!-- Legend -->
            <div style="position:absolute;bottom:12px;left:12px;background:white;border:1px solid #E5E7EB;border-radius:8px;padding:8px 12px;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
                ${[...new Set(this.nodes.map(n => n.type))].map(t => html`
                <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:#6B7280;margin:2px 0">
                    <div style="width:8px;height:8px;border-radius:50%;background:${TYPE_COLORS[t] || TYPE_COLORS.default}"></div>
                    ${t.replace(/_/g, ' ')}
                </div>`)}
            </div>

            <!-- Empty state -->
            ${laid.length === 0 ? html`
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:8px">
                <div style="font-size:32px;opacity:0.2">🕸️</div>
                <div style="font-size:13px;color:#9CA3AF">No data to visualize</div>
            </div>` : ''}
        </div>`;
    }
}
