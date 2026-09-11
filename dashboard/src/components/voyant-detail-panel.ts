import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('voyant-detail-panel')
export class VoyantDetailPanel extends LitElement {
    @property({ type: Boolean }) open = false;
    @property({ type: String }) title = '';
    @property({ type: String }) subtitle = '';
    @property({ type: Number }) width = 400;

    createRenderRoot() { return this; }

    private _close() {
        this.open = false;
        this.dispatchEvent(new CustomEvent('close'));
    }

    render() {
        if (!this.open) return html``;
        return html`
            <div style="position:fixed;top:0;right:0;bottom:0;width:${this.width}px;background:#141414;border-left:1px solid #262626;z-index:50;overflow-y:auto;box-shadow:-4px 0 24px rgba(0,0,0,0.3);font-family:Inter,system-ui,sans-serif">
                <div style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid #262626;position:sticky;top:0;background:#141414;z-index:1">
                    <div>
                        <div style="font-size:16px;font-weight:700;color:#FAFAFA">${this.title}</div>
                        ${this.subtitle ? html`<div style="font-size:12px;color:#374151;margin-top:2px">${this.subtitle}</div>` : ''}
                    </div>
                    <button @click=${this._close}
                        style="width:28px;height:28px;border-radius:6px;border:1px solid #262626;background:transparent;color:#4B5563;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center">×</button>
                </div>
                <div style="padding:20px">
                    <slot></slot>
                </div>
            </div>
            <div style="position:fixed;inset:0;background:rgba(0,0,0,0.3);z-index:49" @click=${this._close}></div>
        `;
    }
}
