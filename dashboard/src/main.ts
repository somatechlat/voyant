import { html, render } from 'lit';
import { Router } from '@lit-labs/router';
import { isAuthenticated } from './lib/api';

// Components
import './components/saas-sidebar';
import './components/saas-stat-card';
import './components/saas-status-dot';
import './components/saas-infra-card';
import './components/saas-glass-modal';
import './components/saas-layout';

// Views
import './views/view-login';
import './views/view-dashboard';

function requireAuth(): boolean {
    if (!isAuthenticated()) {
        window.location.href = '/admin/login';
        return false;
    }
    return true;
}

const router = new Router(document.body);

router.setRoutes([
    { path: '/admin/login', component: () => html`<view-login></view-login>` },
    { path: '/admin', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    // Placeholder routes — pages to be built
    { path: '/admin/jobs', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/admin/sources', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/admin/governance', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/admin/capsules', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/admin/ontology', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/admin/audit', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/admin/sql', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/admin/search', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/admin/scraper', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/admin/settings', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/admin/tenants', component: () => {
        if (!requireAuth()) return html``;
        return html`<view-dashboard></view-dashboard>`;
    }},
    { path: '/', render: () => {
        window.location.href = '/admin/login';
        return html``;
    }},
]);

// Default route
if (window.location.pathname === '/' || window.location.pathname === '') {
    window.history.replaceState({}, '', '/admin/login');
}
