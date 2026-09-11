/**
 * Voyant Skeleton — Loading placeholder components.
 *
 * Usage:
 *   import './voyant-skeleton';
 *   html`<voyant-skeleton-text width="200px"></voyant-skeleton-text>`
 *   html`<voyant-skeleton-card></voyant-skeleton-card>`
 *   html`<voyant-skeleton-table rows="5" cols="4"></voyant-skeleton-table>`
 */

import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

// ── Base shimmer animation (shared) ────────────────────────────────────

const SHIMMER_CSS = `
    @keyframes voyant-shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    .voyant-shimmer {
        background: linear-gradient(90deg, var(--saas-bg-hover, #f0f0f0) 25%, var(--saas-bg-card, #e0e0e0) 50%, var(--saas-bg-hover, #f0f0f0) 75%);
        background-size: 200% 100%;
        animation: voyant-shimmer 1.5s ease-in-out infinite;
        border-radius: 6px;
    }
`;

// ── Skeleton Text ───────────────────────────────────────────────────────

@customElement('voyant-skeleton-text')
export class VoyantSkeletonText extends LitElement {
    @property({ type: String }) width = '100%';
    @property({ type: String }) height = '14px';
    @property({ type: Number }) lines = 1;

    createRenderRoot() { return this; }

    render() {
        const widths = this.lines > 1
            ? Array.from({ length: this.lines }, (_, i) => i === this.lines - 1 ? '60%' : '100%')
            : [this.width];

        return html`
        <style>${SHIMMER_CSS}</style>
        <div style="display:flex;flex-direction:column;gap:8px" aria-hidden="true" role="presentation">
            ${widths.map(w => html`
            <div class="voyant-shimmer" style="width:${w};height:${this.height}"></div>
            `)}
        </div>`;
    }
}

// ── Skeleton Card ───────────────────────────────────────────────────────

@customElement('voyant-skeleton-card')
export class VoyantSkeletonCard extends LitElement {
    @property({ type: String }) height = '120px';

    createRenderRoot() { return this; }

    render() {
        return html`
        <style>${SHIMMER_CSS}</style>
        <div style="background:var(--saas-bg-card, #fff);border:1px solid var(--saas-border, #E5E7EB);border-radius:12px;padding:20px" aria-hidden="true" role="presentation">
            <div class="voyant-shimmer" style="width:40%;height:14px;margin-bottom:12px"></div>
            <div class="voyant-shimmer" style="width:100%;height:${this.height}"></div>
            <div style="display:flex;gap:8px;margin-top:12px">
                <div class="voyant-shimmer" style="width:60px;height:20px"></div>
                <div class="voyant-shimmer" style="width:80px;height:20px"></div>
            </div>
        </div>`;
    }
}

// ── Skeleton Table ──────────────────────────────────────────────────────

@customElement('voyant-skeleton-table')
export class VoyantSkeletonTable extends LitElement {
    @property({ type: Number }) rows = 5;
    @property({ type: Number }) cols = 4;

    createRenderRoot() { return this; }

    render() {
        const colWidths = ['25%', '30%', '20%', '25%'];
        return html`
        <style>${SHIMMER_CSS}</style>
        <div style="background:var(--saas-bg-card, #fff);border:1px solid var(--saas-border, #E5E7EB);border-radius:12px;overflow:hidden" aria-hidden="true" role="presentation">
            <div style="display:flex;gap:16px;padding:12px 20px;border-bottom:1px solid var(--saas-border, #E5E7EB)">
                ${Array.from({ length: this.cols }, (_, i) => html`
                <div class="voyant-shimmer" style="width:${colWidths[i] || '20%'};height:12px"></div>
                `)}
            </div>
            ${Array.from({ length: this.rows }, () => html`
            <div style="display:flex;gap:16px;padding:14px 20px;border-bottom:1px solid var(--saas-border, #E5E7EB)">
                ${Array.from({ length: this.cols }, (_, i) => html`
                <div class="voyant-shimmer" style="width:${colWidths[i] || '20%'};height:14px"></div>
                `)}
            </div>`)}
        </div>`;
    }
}

// ── Skeleton Metric Cards ───────────────────────────────────────────────

@customElement('voyant-skeleton-metrics')
export class VoyantSkeletonMetrics extends LitElement {
    @property({ type: Number }) count = 4;

    createRenderRoot() { return this; }

    render() {
        return html`
        <style>${SHIMMER_CSS}</style>
        <div style="display:grid;grid-template-columns:repeat(${this.count},1fr);gap:16px" aria-hidden="true" role="presentation">
            ${Array.from({ length: this.count }, () => html`
            <div style="background:var(--saas-bg-card, #fff);border:1px solid var(--saas-border, #E5E7EB);border-radius:12px;padding:20px">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                    <div class="voyant-shimmer" style="width:36px;height:36px;border-radius:8px"></div>
                    <div class="voyant-shimmer" style="width:80px;height:12px"></div>
                </div>
                <div class="voyant-shimmer" style="width:60px;height:28px;margin-bottom:4px"></div>
                <div class="voyant-shimmer" style="width:40px;height:10px"></div>
            </div>`)}
        </div>`;
    }
}

// ── Skeleton Graph ──────────────────────────────────────────────────────

@customElement('voyant-skeleton-graph')
export class VoyantSkeletonGraph extends LitElement {
    createRenderRoot() { return this; }

    render() {
        return html`
        <style>${SHIMMER_CSS}</style>
        <div style="background:var(--saas-bg-card, #fff);border:1px solid var(--saas-border, #E5E7EB);border-radius:12px;height:400px;display:flex;align-items:center;justify-content:center" aria-hidden="true" role="presentation">
            <div style="display:flex;gap:24px;align-items:center">
                ${Array.from({ length: 5 }, () => html`
                <div class="voyant-shimmer" style="width:48px;height:48px;border-radius:50%"></div>
                `)}
            </div>
        </div>`;
    }
}
