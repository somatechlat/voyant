/**
 * Voyant Toast — Production-grade notification system.
 *
 * Usage:
 *   import { showToast } from './voyant-toast';
 *   showToast('Saved successfully', 'success');
 *   showToast('Failed to load', 'error', { duration: 5000 });
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
    id: number;
    message: string;
    type: ToastType;
    duration: number;
    action?: { label: string; callback: () => void };
}

let _nextId = 0;
let _addToast: ((toast: Omit<Toast, 'id'>) => void) | null = null;

/**
 * Show a toast notification. Safe to call from anywhere — the toast container
 * is a singleton mounted once at page load.
 */
export function showToast(
    message: string,
    type: ToastType = 'info',
    opts?: { duration?: number; action?: { label: string; callback: () => void } },
) {
    if (_addToast) {
        _addToast({
            message,
            type,
            duration: opts?.duration ?? (type === 'error' ? 6000 : 4000),
            action: opts?.action,
        });
    }
}

@customElement('voyant-toast-container')
export class VoyantToastContainer extends LitElement {
    @state() private _toasts: Toast[] = [];

    createRenderRoot() { return this; }

    connectedCallback() {
        super.connectedCallback();
        _addToast = (toast) => {
            const id = ++_nextId;
            this._toasts = [...this._toasts, { ...toast, id }];
            setTimeout(() => this._dismiss(id), toast.duration);
        };
    }

    disconnectedCallback() {
        _addToast = null;
        super.disconnectedCallback();
    }

    private _dismiss(id: number) {
        this._toasts = this._toasts.filter(t => t.id !== id);
    }

    private _icon(type: ToastType): string {
        switch (type) {
            case 'success': return '✓';
            case 'error': return '✕';
            case 'warning': return '⚠';
            case 'info': return 'ℹ';
        }
    }

    private _color(type: ToastType): string {
        switch (type) {
            case 'success': return '#22C55E';
            case 'error': return '#EF4444';
            case 'warning': return '#F59E0B';
            case 'info': return '#3B82F6';
        }
    }

    render() {
        if (this._toasts.length === 0) return html``;

        return html`
        <div style="position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column-reverse;gap:8px;pointer-events:none">
            ${this._toasts.map(t => html`
            <div
                style="pointer-events:auto;display:flex;align-items:center;gap:12px;padding:12px 16px;border-radius:10px;background:var(--saas-bg-card, #fff);border:1px solid var(--saas-border, #E5E7EB);border-left:4px solid ${this._color(t.type)};box-shadow:0 8px 24px rgba(0,0,0,0.12);font-size:13px;font-family:Inter,system-ui,sans-serif;min-width:280px;max-width:420px;animation:toast-in 300ms cubic-bezier(0.34,1.56,0.64,1)"
                role="alert"
                aria-live="polite"
            >
                <span style="width:20px;height:20px;border-radius:50%;background:${this._color(t.type)}20;color:${this._color(t.type)};display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0">${this._icon(t.type)}</span>
                <span style="flex:1;color:var(--saas-text-primary, #050505)">${t.message}</span>
                ${t.action ? html`
                <button
                    @click=${() => { t.action!.callback(); this._dismiss(t.id); }}
                    style="padding:4px 10px;border-radius:6px;border:1px solid ${this._color(t.type)}40;background:transparent;color:${this._color(t.type)};font-size:11px;font-weight:600;cursor:pointer;font-family:inherit"
                >${t.action.label}</button>
                ` : ''}
                <button
                    @click=${() => this._dismiss(t.id)}
                    aria-label="Dismiss notification"
                    style="width:20px;height:20px;border-radius:4px;border:none;background:transparent;color:var(--saas-text-muted, #9CA3AF);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0"
                >×</button>
            </div>`)}
        </div>
        <style>
            @keyframes toast-in {
                from { opacity: 0; transform: translateX(24px) scale(0.95); }
                to { opacity: 1; transform: translateX(0) scale(1); }
            }
        </style>`;
    }
}
