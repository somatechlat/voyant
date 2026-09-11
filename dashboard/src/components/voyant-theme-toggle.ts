/**
 * Voyant Theme Toggle — Dark/light mode switch.
 *
 * Persists preference in localStorage. Reads system preference on first visit.
 * CSS variables in globals.css handle the actual color switching via [data-theme="dark"].
 */

import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';

export type Theme = 'light' | 'dark';

function getStoredTheme(): Theme {
    const stored = localStorage.getItem('voyant_theme');
    if (stored === 'dark' || stored === 'light') return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme: Theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('voyant_theme', theme);
}

// Apply immediately on module load
applyTheme(getStoredTheme());

@customElement('voyant-theme-toggle')
export class VoyantThemeToggle extends LitElement {
    @state() private _theme: Theme = getStoredTheme();

    createRenderRoot() { return this; }

    connectedCallback() {
        super.connectedCallback();
        // Listen for system preference changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('voyant_theme')) {
                this._theme = e.matches ? 'dark' : 'light';
                applyTheme(this._theme);
            }
        });
    }

    private _toggle() {
        this._theme = this._theme === 'dark' ? 'light' : 'dark';
        applyTheme(this._theme);
    }

    render() {
        const isDark = this._theme === 'dark';
        return html`
        <button
            @click=${this._toggle}
            aria-label="Switch to ${isDark ? 'light' : 'dark'} mode"
            title="${isDark ? 'Light' : 'Dark'} mode"
            style="width:36px;height:36px;border-radius:8px;border:1px solid var(--saas-border);background:var(--saas-bg-card);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;transition:all 150ms ease;color:var(--saas-text-secondary)"
        >${isDark ? '☀️' : '🌙'}</button>`;
    }
}
