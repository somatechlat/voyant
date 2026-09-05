import { html, render } from 'lit';
import { isAuthenticated } from './lib/api';
import { Router } from './lib/router';

// Components
import './components/saas-sidebar';
import './components/saas-stat-card';
import './components/saas-glass-modal';

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
    { path: '/', render: () => { window.location.href = '/admin/login'; return html``; } },
]);

if (window.location.pathname === '/' || window.location.pathname === '') {
    window.history.replaceState({}, '', '/admin/login');
}
