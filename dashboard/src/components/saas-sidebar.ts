import { LitElement, html, svg } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { unsafeSVG } from 'lit/directives/unsafe-svg.js';

interface NavItem {
    label: string;
    path: string;
    icon: string;
}

const NAV_ITEMS: NavItem[] = [
    { label: 'Dashboard', path: '/admin', icon: 'grid' },
    { label: 'Jobs', path: '/admin/jobs', icon: 'activity' },
    { label: 'Sources', path: '/admin/sources', icon: 'database' },
    { label: 'Governance', path: '/admin/governance', icon: 'shield' },
    { label: 'Capsules', path: '/admin/capsules', icon: 'box' },
    { label: 'Ontology', path: '/admin/ontology', icon: 'layers' },
    { label: 'Audit Log', path: '/admin/audit', icon: 'file-text' },
    { label: 'SQL Console', path: '/admin/sql', icon: 'terminal' },
    { label: 'Search', path: '/admin/search', icon: 'search' },
    { label: 'Scraper', path: '/admin/scraper', icon: 'globe' },
    { label: 'Settings', path: '/admin/settings', icon: 'settings' },
    { label: 'Tenants', path: '/admin/tenants', icon: 'users' },
    { label: 'Agents', path: '/admin/agents', icon: 'bot' },
    { label: 'Drift Monitor', path: '/admin/drift', icon: 'activity' },
    { label: 'Pipelines', path: '/admin/pipelines', icon: 'workflow' },
    { label: 'Dashboards', path: '/admin/dashboards', icon: 'grid' },
    { label: 'MCP Playground', path: '/admin/mcp', icon: 'puzzle' },
    { label: 'Notifications', path: '/admin/notifications', icon: 'bell' },
    { label: 'Workspaces', path: '/admin/workspaces', icon: 'people' },
    { label: 'Approvals', path: '/admin/approvals', icon: 'check-circle' },
    { label: 'Feature Store', path: '/admin/features', icon: 'grid' },
    { label: 'Model Serving', path: '/admin/models', icon: 'box' },
    { label: 'Data Connectors', path: '/admin/connectors', icon: 'database' },
    { label: 'Webhooks', path: '/admin/webhooks', icon: 'workflow' },
    { label: 'Streaming', path: '/admin/streaming', icon: 'activity' },
    { label: 'Alert Rules', path: '/admin/alerting', icon: 'bell' },
];

const ICONS: Record<string, string> = {
    grid: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    activity: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    box: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
    terminal: '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>',
    search: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    globe: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    bot: '<rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/>',
    puzzle: '<path d="M19.439 7.85c-.049.322.059.648.289.878l1.568 1.568c.47.47.706 1.087.706 1.704s-.235 1.233-.706 1.704l-1.611 1.611a.98.98 0 0 1-.837.276c-.47-.07-.802-.48-.968-.925a2.501 2.501 0 1 0-3.214 3.214c.446.166.855.497.925.968a.979.979 0 0 1-.276.837l-1.61 1.61a2.404 2.404 0 0 1-1.705.707 2.402 2.402 0 0 1-1.704-.706l-1.568-1.568a1.026 1.026 0 0 0-.877-.29c-.493.074-.84.504-1.02.968a2.5 2.5 0 1 1-3.237-3.237c.464-.18.894-.527.967-1.02a1.026 1.026 0 0 0-.289-.877l-1.568-1.568A2.402 2.402 0 0 1 1.998 12c0-.617.236-1.234.706-1.704L4.23 8.77c.24-.24.581-.353.917-.303.515.077.877.528 1.073 1.01a2.5 2.5 0 1 0 3.259-3.259c-.482-.196-.933-.558-1.01-1.073-.05-.336.062-.676.303-.917l1.525-1.525A2.402 2.402 0 0 1 12 1.998c.617 0 1.234.236 1.704.706l1.568 1.568c.23.23.556.338.877.29.493-.074.84-.504 1.02-.969a2.5 2.5 0 1 1 3.237 3.237c-.464.18-.894.527-.967 1.02z"/>',
    workflow: '<circle cx="12" cy="12" r="2"/><path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/>',
    bell: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    people: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
};

@customElement('saas-sidebar')
export class SaaSSidebar extends LitElement {
    @property({ type: String }) currentPath = '/admin';
    @property({ type: String }) version = '3.0.0';
    @property({ type: String }) env = 'local';

    createRenderRoot() { return this; }

    private navigate(path: string) {
        window.history.pushState({}, '', path);
        window.dispatchEvent(new PopStateEvent('popstate'));
    }

    private logout() {
        localStorage.removeItem('voyant_token');
        window.location.href = '/admin/login';
    }

    render() {
        return html`
        <aside class="fixed left-0 top-0 bottom-0 w-60 bg-white border-r border-gray-100 flex flex-col z-30">
            <!-- Logo -->
            <div class="h-16 flex items-center px-6 border-b border-gray-100">
                <div class="flex items-center gap-3">
                    <div class="h-8 w-8 rounded-lg bg-gray-900 flex items-center justify-center">
                        <svg class="h-4 w-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/>
                            <line x1="12" y1="22" x2="12" y2="15.5"/>
                            <polyline points="22 8.5 12 15.5 2 8.5"/>
                        </svg>
                    </div>
                    <div>
                        <div class="font-semibold text-sm">Voyant</div>
                        <div class="text-xs text-gray-400">v${this.version} · ${this.env}</div>
                    </div>
                </div>
            </div>

            <!-- Navigation -->
            <nav class="flex-1 overflow-y-auto py-4 px-3">
                ${NAV_ITEMS.map(item => {
                    const isActive = this.currentPath === item.path ||
                        (item.path !== '/admin' && this.currentPath.startsWith(item.path));
                    return html`
                    <button
                        class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm mb-0.5 transition-colors
                            ${isActive
                                ? 'bg-brand text-white'
                                : 'text-gray-600 hover:bg-gray-50 hover:text-ink'}"
                        @click=${() => this.navigate(item.path)}
                    >
                        <svg class="h-4 w-4 ${isActive ? 'text-white' : 'text-gray-400'}" viewBox="0 0 24 24"
                            fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            ${unsafeSVG(ICONS[item.icon] || ICONS.grid)}
                        </svg>
                        ${item.label}
                    </button>`;
                })}
            </nav>

            <!-- Footer -->
            <div class="p-3 border-t border-gray-100">
                <button
                    class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50 hover:text-red-600 transition-colors"
                    @click=${this.logout}
                >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round">
                        ${unsafeSVG(ICONS.logout)}
                    </svg>
                    Logout
                </button>
            </div>
        </aside>`;
    }
}
