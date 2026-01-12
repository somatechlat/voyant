import { html, render } from 'lit';
import { Router } from '@lit-labs/router';
import './components/saas-layout';
import './views/view-login';
import './views/view-voyant-setup';

// Define the router
const router = new Router(document.body);
router.setRoutes([
    { path: '/login', component: () => html`<view-login></view-login>` },
    { path: '/admin/setup', component: () => html`<view-voyant-setup></view-voyant-setup>` },
    { path: '/', render: () => { window.location.href = '/login'; return html``; } }
]);

if (window.location.pathname === '/' || window.location.pathname === '') {
    window.history.replaceState({}, '', '/login');
}
