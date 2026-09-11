/**
 * Voyant Error Boundary — Wraps content and shows error UI on failure.
 *
 * Usage:
 *   html`<voyant-error-boundary .error=${this.error} .retry=${() => this.loadData()}>
 *     <div>Normal content here</div>
 *   </voyant-error-boundary>`
 */

import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('voyant-error-boundary')
export class VoyantErrorBoundary extends LitElement {
    @property({ type: String }) error = '';
    @property({ type: String }) title = 'Something went wrong';
    @property({ attribute: false }) retry: (() => void) | null = null;

    createRenderRoot() { return this; }

    render() {
        if (!this.error) return html`<slot></slot>`;

        return html`
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:48px 24px;text-align:center;max-width:400px;margin:0 auto" role="alert" aria-live="assertive">
            <!-- Error icon -->
            <div style="width:56px;height:56px;border-radius:50%;background:var(--saas-danger-bg, rgba(239,68,68,0.08));display:flex;align-items:center;justify-content:center;margin-bottom:16px">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
            </div>

            <!-- Title -->
            <h3 style="font-size:16px;font-weight:600;color:var(--saas-text-primary, #050505);margin-bottom:8px">${this.title}</h3>

            <!-- Error message -->
            <p style="font-size:13px;color:var(--saas-text-secondary, #6B7280);margin-bottom:24px;line-height:1.5;word-break:break-word">${this.error}</p>

            <!-- Actions -->
            <div style="display:flex;gap:12px">
                ${this.retry ? html`
                <button
                    @click=${this.retry}
                    style="padding:8px 20px;border-radius:8px;border:1px solid var(--saas-brand, #FF4D00);background:var(--saas-brand, #FF4D00);color:white;font-size:13px;font-weight:500;cursor:pointer;font-family:Inter,system-ui,sans-serif;transition:all 150ms ease"
                    aria-label="Retry loading"
                >Try Again</button>
                ` : ''}
                <button
                    @click=${() => { this.error = ''; }}
                    style="padding:8px 20px;border-radius:8px;border:1px solid var(--saas-border, #E5E7EB);background:transparent;color:var(--saas-text-primary, #050505);font-size:13px;font-weight:500;cursor:pointer;font-family:Inter,system-ui,sans-serif;transition:all 150ms ease"
                    aria-label="Dismiss error"
                >Dismiss</button>
            </div>
        </div>`;
    }
}
