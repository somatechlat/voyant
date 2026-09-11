/**
 * Voyant Virtual List — Renders only visible rows for 10K+ row tables.
 *
 * Usage:
 *   html`<voyant-virtual-list
 *       .items=${rows}
 *       .itemHeight=${48}
 *       .height=${600}
 *       .renderItem=${(row, i) => html`<div>${row.name}</div>`}
 *   ></voyant-virtual-list>`
 */

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('voyant-virtual-list')
export class VoyantVirtualList extends LitElement {
    @property({ type: Array }) items: unknown[] = [];
    @property({ type: Number }) itemHeight = 48;
    @property({ type: Number }) height = 600;
    @property({ type: Number }) overscan = 5; // Extra rows rendered above/below viewport
    @property({ attribute: false }) renderItem: ((item: unknown, index: number) => unknown) | null = null;

    @state() private _scrollTop = 0;
    private _container: HTMLElement | null = null;

    createRenderRoot() { return this; }

    private get _totalCount(): number {
        return this.items.length;
    }

    private get _totalHeight(): number {
        return this._totalCount * this.itemHeight;
    }

    private get _startIndex(): number {
        const raw = Math.floor(this._scrollTop / this.itemHeight) - this.overscan;
        return Math.max(0, raw);
    }

    private get _endIndex(): number {
        const visibleCount = Math.ceil(this.height / this.itemHeight);
        const raw = this._startIndex + visibleCount + this.overscan * 2;
        return Math.min(this._totalCount, raw);
    }

    private get _visibleItems(): Array<{ item: unknown; index: number; offsetY: number }> {
        const items: Array<{ item: unknown; index: number; offsetY: number }> = [];
        for (let i = this._startIndex; i < this._endIndex; i++) {
            items.push({
                item: this.items[i],
                index: i,
                offsetY: i * this.itemHeight,
            });
        }
        return items;
    }

    private _onScroll(e: Event) {
        this._scrollTop = (e.target as HTMLElement).scrollTop;
    }

    render() {
        if (this._totalCount === 0) {
            return html`<div style="height:${this.height}px;display:flex;align-items:center;justify-content:center;color:var(--saas-text-muted, #9CA3AF);font-size:13px">No data</div>`;
        }

        return html`
        <div
            style="height:${this.height}px;overflow-y:auto;position:relative;will-change:transform"
            @scroll=${this._onScroll}
        >
            <div style="height:${this._totalHeight}px;position:relative">
                ${this._visibleItems.map(({ item, index, offsetY }) => html`
                <div style="position:absolute;top:${offsetY}px;left:0;right:0;height:${this.itemHeight}px">
                    ${this.renderItem ? this.renderItem(item, index) : html`<div style="padding:12px 16px;font-size:13px">${JSON.stringify(item)}</div>`}
                </div>
                `)}
            </div>
        </div>`;
    }
}
