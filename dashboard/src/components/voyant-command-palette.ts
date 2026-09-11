/**
 * Voyant Command Palette — Cmd+K / Ctrl+K quick navigation and actions.
 *
 * Searches across navigation items, recent actions, and MCP tools.
 * Keyboard-driven: arrow keys navigate, Enter executes, Esc closes.
 */

import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';

interface CommandItem {
    id: string;
    label: string;
    description: string;
    category: string;
    icon: string;
    action: () => void;
}

let _registerCommands: ((commands: CommandItem[]) => void) | null = null;
let _openPalette: (() => void) | null = null;

/** Register commands for the palette. Call once at app init. */
export function registerCommands(commands: CommandItem[]) {
    _registerCommands?.(commands);
}

/** Programmatically open the palette. */
export function openCommandPalette() {
    _openPalette?.();
}

const NAV_COMMANDS: CommandItem[] = [
    { id: 'nav-dashboard', label: 'Dashboard', description: 'System overview', category: 'Navigation', icon: 'grid', action: () => { window.location.href = '/admin'; } },
    { id: 'nav-jobs', label: 'Jobs', description: 'View and manage jobs', category: 'Navigation', icon: 'activity', action: () => { window.location.href = '/admin/jobs'; } },
    { id: 'nav-sources', label: 'Sources', description: 'Data sources', category: 'Navigation', icon: 'database', action: () => { window.location.href = '/admin/sources'; } },
    { id: 'nav-ontology', label: 'Ontology', description: 'Knowledge graph explorer', category: 'Navigation', icon: 'layers', action: () => { window.location.href = '/admin/ontology'; } },
    { id: 'nav-sql', label: 'SQL Console', description: 'Execute SQL queries', category: 'Navigation', icon: 'terminal', action: () => { window.location.href = '/admin/sql'; } },
    { id: 'nav-scraper', label: 'Scraper', description: 'Web scraping engine', category: 'Navigation', icon: 'globe', action: () => { window.location.href = '/admin/scraper'; } },
    { id: 'nav-agents', label: 'Agents', description: 'AI agent management', category: 'Navigation', icon: 'bot', action: () => { window.location.href = '/admin/agents'; } },
    { id: 'nav-pipelines', label: 'Pipelines', description: 'Data pipelines', category: 'Navigation', icon: 'workflow', action: () => { window.location.href = '/admin/pipelines'; } },
    { id: 'nav-models', label: 'Models', description: 'ML model registry', category: 'Navigation', icon: 'box', action: () => { window.location.href = '/admin/models'; } },
    { id: 'nav-governance', label: 'Governance', description: 'Security & compliance', category: 'Navigation', icon: 'shield', action: () => { window.location.href = '/admin/governance'; } },
    { id: 'nav-settings', label: 'Settings', description: 'System configuration', category: 'Navigation', icon: 'settings', action: () => { window.location.href = '/admin/settings'; } },
    { id: 'nav-mcp', label: 'MCP Playground', description: 'Test MCP tools', category: 'Navigation', icon: 'puzzle', action: () => { window.location.href = '/admin/mcp'; } },
];

@customElement('voyant-command-palette')
export class VoyantCommandPalette extends LitElement {
    @state() private _open = false;
    @state() private _query = '';
    @state() private _selectedIndex = 0;
    @state() private _commands: CommandItem[] = NAV_COMMANDS;

    private _inputEl: HTMLInputElement | null = null;

    createRenderRoot() { return this; }

    connectedCallback() {
        super.connectedCallback();
        _registerCommands = (cmds) => {
            this._commands = [...NAV_COMMANDS, ...cmds];
        };
        _openPalette = () => { this._open = true; };

        // Global Cmd+K / Ctrl+K handler
        this._onKeyDown = this._onKeyDown.bind(this);
        document.addEventListener('keydown', this._onKeyDown);
    }

    disconnectedCallback() {
        document.removeEventListener('keydown', this._onKeyDown);
        _registerCommands = null;
        _openPalette = null;
        super.disconnectedCallback();
    }

    private _onKeyDown(e: KeyboardEvent) {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            this._open = !this._open;
            if (this._open) {
                this._query = '';
                this._selectedIndex = 0;
                requestAnimationFrame(() => this._inputEl?.focus());
            }
        }
        if (this._open && e.key === 'Escape') {
            e.preventDefault();
            this._open = false;
        }
    }

    private get filtered(): CommandItem[] {
        if (!this._query) return this._commands.slice(0, 12);
        const q = this._query.toLowerCase();
        return this._commands.filter(c =>
            c.label.toLowerCase().includes(q) ||
            c.description.toLowerCase().includes(q) ||
            c.category.toLowerCase().includes(q)
        ).slice(0, 12);
    }

    private _onInput(e: Event) {
        this._query = (e.target as HTMLInputElement).value;
        this._selectedIndex = 0;
    }

    private _onKeyNav(e: KeyboardEvent) {
        const items = this._filtered;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this._selectedIndex = Math.min(this._selectedIndex + 1, items.length - 1);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this._selectedIndex = Math.max(this._selectedIndex - 1, 0);
        } else if (e.key === 'Enter' && items[this._selectedIndex]) {
            e.preventDefault();
            this._execute(items[this._selectedIndex]);
        }
    }

    private _execute(item: CommandItem) {
        this._open = false;
        this._query = '';
        item.action();
    }

    render() {
        if (!this._open) return html``;

        const items = this._filtered;

        return html`
        <div
            style="position:fixed;inset:0;z-index:10000;display:flex;align-items:flex-start;justify-content:center;padding-top:20vh;background:rgba(0,0,0,0.5);backdrop-filter:blur(4px)"
            @click=${(e: Event) => { if ((e.target as HTMLElement).style.position === 'fixed') this._open = false; }}
        >
            <div style="width:560px;max-height:420px;background:var(--saas-bg-card, #fff);border:1px solid var(--saas-border, #E5E7EB);border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.3);overflow:hidden;animation:cmd-in 150ms ease-out">
                <!-- Search Input -->
                <div style="display:flex;align-items:center;gap:12px;padding:16px 20px;border-bottom:1px solid var(--saas-border, #E5E7EB)">
                    <span style="font-size:16px;color:var(--saas-text-muted, #9CA3AF)">🔍</span>
                    <input
                        type="text"
                        placeholder="Search commands, pages, tools..."
                        .value=${this._query}
                        @input=${this._onInput}
                        @keydown=${this._onKeyNav}
                        style="flex:1;border:none;outline:none;font-size:15px;font-family:Inter,system-ui,sans-serif;background:transparent;color:var(--saas-text-primary, #050505)"
                    />
                    <kbd style="font-size:10px;padding:2px 6px;border-radius:4px;background:var(--saas-bg-hover, #f5f5f5);border:1px solid var(--saas-border, #E5E7EB);color:var(--saas-text-muted, #9CA3AF);font-family:Inter,sans-serif">ESC</kbd>
                </div>

                <!-- Results -->
                <div style="max-height:340px;overflow-y:auto;padding:8px">
                    ${items.length === 0 ? html`
                    <div style="padding:24px;text-align:center;color:var(--saas-text-muted, #9CA3AF);font-size:13px">No results for "${this._query}"</div>
                    ` : ''}
                    ${items.map((item, i) => html`
                    <button
                        style="width:100%;display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:8px;border:none;background:${i === this._selectedIndex ? 'var(--saas-brand-light, rgba(255,77,0,0.08))' : 'transparent'};cursor:pointer;text-align:left;font-family:Inter,system-ui,sans-serif;transition:background 100ms"
                        @click=${() => this._execute(item)}
                        @mouseenter=${() => { this._selectedIndex = i; }}
                    >
                        <span style="width:28px;height:28px;border-radius:6px;background:var(--saas-bg-hover, #f5f5f5);display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0">${item.icon === 'grid' ? '📊' : item.icon === 'activity' ? '⚡' : item.icon === 'database' ? '🗄️' : item.icon === 'layers' ? '📐' : item.icon === 'terminal' ? '💻' : item.icon === 'globe' ? '🌐' : item.icon === 'bot' ? '🤖' : item.icon === 'workflow' ? '⚙️' : item.icon === 'box' ? '📦' : item.icon === 'shield' ? '🛡️' : item.icon === 'settings' ? '⚙️' : '🔧'}</span>
                        <div style="flex:1;min-width:0">
                            <div style="font-size:13px;font-weight:500;color:var(--saas-text-primary, #050505)">${item.label}</div>
                            <div style="font-size:11px;color:var(--saas-text-muted, #9CA3AF)">${item.description}</div>
                        </div>
                        <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:var(--saas-bg-hover, #f5f5f5);color:var(--saas-text-muted, #9CA3AF)">${item.category}</span>
                    </button>`)}
                </div>

                <!-- Footer -->
                <div style="display:flex;align-items:center;gap:16px;padding:8px 20px;border-top:1px solid var(--saas-border, #E5E7EB);font-size:10px;color:var(--saas-text-muted, #9CA3AF)">
                    <span><kbd style="padding:1px 4px;border-radius:3px;border:1px solid var(--saas-border, #E5E7EB)">↑↓</kbd> navigate</span>
                    <span><kbd style="padding:1px 4px;border-radius:3px;border:1px solid var(--saas-border, #E5E7EB)">↵</kbd> select</span>
                    <span><kbd style="padding:1px 4px;border-radius:3px;border:1px solid var(--saas-border, #E5E7EB)">esc</kbd> close</span>
                </div>
            </div>
        </div>
        <style>
            @keyframes cmd-in {
                from { opacity: 0; transform: scale(0.96) translateY(-8px); }
                to { opacity: 1; transform: scale(1) translateY(0); }
            }
        </style>`;
    }
}
