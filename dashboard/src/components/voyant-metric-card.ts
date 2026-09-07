import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('voyant-metric-card')
export class VoyantMetricCard extends LitElement {
    @property({ type: String }) label = '';
    @property({ type: String }) value = '';
    @property({ type: String }) trend = '';
    @property({ type: String }) trendDirection = 'neutral';
    @property({ type: String }) icon = '';
    @property({ type: String }) color = '#FF4D00';

    createRenderRoot() { return this; }

    render() {
        const trendColors: Record<string, string> = { up: '#22C55E', down: '#EF4444', neutral: '#6B7280' };
        const trendIcons: Record<string, string> = { up: '↑', down: '↓', neutral: '→' };
        return html`
            <div style="background:#141414;border:1px solid #262626;border-radius:12px;padding:20px;font-family:Inter,system-ui,sans-serif;transition:border-color 0.2s"
                @mouseenter=${(e: Event) => (e.currentTarget as HTMLElement).style.borderColor = this.color}
                @mouseleave=${(e: Event) => (e.currentTarget as HTMLElement).style.borderColor = '#262626'}>
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
                    <span style="font-size:12px;color:#6B7280;font-weight:500">${this.label}</span>
                    ${this.icon ? html`<span style="font-size:16px;opacity:0.6">${this.icon}</span>` : ''}
                </div>
                <div style="font-size:28px;font-weight:800;color:#FAFAFA;font-family:Geist,Inter,system-ui,sans-serif;letter-spacing:-0.02em">${this.value}</div>
                ${this.trend ? html`
                <div style="display:flex;align-items:center;gap:4px;margin-top:8px;font-size:12px;font-weight:600;color:${trendColors[this.trendDirection]}">
                    <span>${trendIcons[this.trendDirection]}</span>
                    <span>${this.trend}</span>
                </div>` : ''}
            </div>
        `;
    }
}
