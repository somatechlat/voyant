import { html, render } from 'lit';
import { isAuthenticated } from './lib/api';
import { Router } from './lib/router';
import { initKeyboard, registerDefaultShortcuts } from './lib/keyboard';
import './styles/globals.css';

// Components
import './components/saas-sidebar';
import './components/saas-stat-card';
import './components/saas-glass-modal';

// Production UI components
import './components/voyant-toast';
import './components/voyant-skeleton';
import './components/voyant-theme-toggle';
import './components/voyant-command-palette';
import './components/voyant-error-boundary';

// Views
import './views/view-login';
import './views/view-dashboard';
import './views/view-jobs';
import './views/view-sources';
import './views/view-governance';
import './views/view-capsules';
import './views/view-ontology';
import './views/view-audit';
import './views/view-sql';
import './views/view-search';
import './views/view-scraper';
import './views/view-settings';
import './views/view-tenants';
import './views/view-agents';
import './views/view-mcp';
import './views/view-pipelines';
import './views/view-dashboards';
import './views/view-drift';
import './views/view-notifications';
import './views/view-workspaces';
import './views/view-approvals';
import './views/view-features';
import './views/view-models';
import './views/view-connectors';
import './views/view-webhooks';
import './views/view-streaming';
import './views/view-alerting';

// Initialize keyboard shortcuts
initKeyboard();
registerDefaultShortcuts();

// Mount global UI components
const toastContainer = document.createElement('voyant-toast-container');
document.body.appendChild(toastContainer);

const commandPalette = document.createElement('voyant-command-palette');
document.body.appendChild(commandPalette);

function auth(): boolean {
    if (!isAuthenticated()) { window.location.href = '/admin/login'; return false; }
    return true;
}

const outlet = document.getElementById('app') || document.body;
const router = new Router(outlet);

router.setRoutes([
    { path: '/admin/login', component: () => html`<view-login></view-login>` },
    { path: '/admin', component: () => auth() ? html`<view-dashboard></view-dashboard>` : html`` },
    { path: '/admin/jobs', component: () => auth() ? html`<view-jobs></view-jobs>` : html`` },
    { path: '/admin/sources', component: () => auth() ? html`<view-sources></view-sources>` : html`` },
    { path: '/admin/governance', component: () => auth() ? html`<view-governance></view-governance>` : html`` },
    { path: '/admin/capsules', component: () => auth() ? html`<view-capsules></view-capsules>` : html`` },
    { path: '/admin/ontology', component: () => auth() ? html`<view-ontology></view-ontology>` : html`` },
    { path: '/admin/audit', component: () => auth() ? html`<view-audit></view-audit>` : html`` },
    { path: '/admin/sql', component: () => auth() ? html`<view-sql></view-sql>` : html`` },
    { path: '/admin/search', component: () => auth() ? html`<view-search></view-search>` : html`` },
    { path: '/admin/scraper', component: () => auth() ? html`<view-scraper></view-scraper>` : html`` },
    { path: '/admin/settings', component: () => auth() ? html`<view-settings></view-settings>` : html`` },
    { path: '/admin/tenants', component: () => auth() ? html`<view-tenants></view-tenants>` : html`` },
    { path: '/admin/agents', component: () => auth() ? html`<view-agents></view-agents>` : html`` },
    { path: '/admin/mcp', component: () => auth() ? html`<view-mcp></view-mcp>` : html`` },
    { path: '/admin/pipelines', component: () => auth() ? html`<view-pipelines></view-pipelines>` : html`` },
    { path: '/admin/dashboards', component: () => auth() ? html`<view-dashboards></view-dashboards>` : html`` },
    { path: '/admin/drift', component: () => auth() ? html`<view-drift></view-drift>` : html`` },
    { path: '/admin/notifications', component: () => auth() ? html`<view-notifications></view-notifications>` : html`` },
    { path: '/admin/workspaces', component: () => auth() ? html`<view-workspaces></view-workspaces>` : html`` },
    { path: '/admin/approvals', component: () => auth() ? html`<view-approvals></view-approvals>` : html`` },
    { path: '/admin/features', component: () => auth() ? html`<view-features></view-features>` : html`` },
    { path: '/admin/models', component: () => auth() ? html`<view-models></view-models>` : html`` },
    { path: '/admin/connectors', component: () => auth() ? html`<view-connectors></view-connectors>` : html`` },
    { path: '/admin/webhooks', component: () => auth() ? html`<view-webhooks></view-webhooks>` : html`` },
    { path: '/admin/streaming', component: () => auth() ? html`<view-streaming></view-streaming>` : html`` },
    { path: '/admin/alerting', component: () => auth() ? html`<view-alerting></view-alerting>` : html`` },
    { path: '/', render: () => { window.location.href = '/admin/login'; return html``; } },
]);

if (window.location.pathname === '/' || window.location.pathname === '') {
    window.history.replaceState({}, '', '/admin/login');
}
