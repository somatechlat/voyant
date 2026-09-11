import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface Notification {
    id: string;
    user_id: string;
    type: string;
    title: string;
    message: string;
    resource_type: string;
    resource_id: string;
    is_read: boolean;
    read_at: string | null;
    tenant_id: string;
    created_at: string;
    updated_at: string;
}

interface NotificationListOut {
    items: Notification[];
    total: number;
    unread_count: number;
}

interface NotificationPreference {
    id: string;
    user_id: string;
    event_type: string;
    channel: string;
    enabled: boolean;
}

/* ── Constants ─────────────────────────────────────────────────────────────── */

const TYPE_ICONS: Record<string, string> = {
    information: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    warning: '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    error: '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
    success: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
};

const TYPE_COLORS: Record<string, string> = {
    information: 'bg-blue-50 text-blue-600 border-blue-200',
    warning: 'bg-amber-50 text-amber-600 border-amber-200',
    error: 'bg-red-50 text-red-600 border-red-200',
    success: 'bg-green-50 text-green-600 border-green-200',
};

const TYPE_DOT_COLORS: Record<string, string> = {
    information: 'bg-blue-500',
    warning: 'bg-amber-500',
    error: 'bg-red-500',
    success: 'bg-green-500',
};

const CHANNELS = ['in_app', 'email', 'slack'] as const;

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-notifications')
export class ViewNotifications extends LitElement {
    @state() tab: 'notifications' | 'preferences' = 'notifications';
    @state() notifications: Notification[] = [];
    @state() totalCount = 0;
    @state() unreadCount = 0;
    @state() loading = true;

    // Filters
    @state() readFilter: 'all' | 'unread' | 'read' = 'all';
    @state() typeFilter = '';

    // Preferences
    @state() preferences: NotificationPreference[] = [];
    @state() prefsLoading = true;

    // Toast
    @state() toast = '';

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadNotifications();
    }

    /* ── Data loading ──────────────────────────────────────────────────────── */

    async loadNotifications() {
        this.loading = true;
        try {
            let path = '/notifications?limit=100';
            if (this.readFilter === 'unread') path += '&is_read=false';
            if (this.readFilter === 'read') path += '&is_read=true';
            if (this.typeFilter) path += `&notification_type=${this.typeFilter}`;
            const data = await api.get<NotificationListOut>(path);
            this.notifications = data.items;
            this.totalCount = data.total;
            this.unreadCount = data.unread_count;
        } catch { this.notifications = []; }
        finally { this.loading = false; }
    }

    async loadPreferences() {
        this.prefsLoading = true;
        try {
            this.preferences = await api.get<NotificationPreference[]>('/notifications/preferences');
        } catch { this.preferences = []; }
        finally { this.prefsLoading = false; }
    }

    /* ── Actions ───────────────────────────────────────────────────────────── */

    async markRead(id: string) {
        try {
            await api.put(`/notifications/${id}/read`);
            await this.loadNotifications();
        } catch { /* empty */ }
    }

    async markAllRead() {
        try {
            await api.put('/notifications/read-all');
            this.showToast('All notifications marked as read');
            await this.loadNotifications();
        } catch { this.showToast('Failed to mark all as read'); }
    }

    async handleNotificationClick(n: Notification) {
        if (!n.is_read) {
            await this.markRead(n.id);
        }
        if (n.resource_type && n.resource_id) {
            const routeMap: Record<string, string> = {
                job: '/admin/jobs',
                pipeline: '/admin/pipelines',
                source: '/admin/sources',
                capsule: '/admin/capsules',
                agent: '/admin/agents',
                approval: '/admin/approvals',
                workspace: '/admin/workspaces',
            };
            const route = routeMap[n.resource_type];
            if (route) {
                window.history.pushState({}, '', route);
                window.dispatchEvent(new PopStateEvent('popstate'));
            }
        }
    }

    async togglePreference(pref: NotificationPreference) {
        try {
            await api.put('/notifications/preferences', {
                preferences: [{
                    event_type: pref.event_type,
                    channel: pref.channel,
                    enabled: !pref.enabled,
                }],
            });
            await this.loadPreferences();
        } catch { /* empty */ }
    }

    /* ── Helpers ───────────────────────────────────────────────────────────── */

    private showToast(msg: string) {
        this.toast = msg;
        setTimeout(() => { this.toast = ''; }, 3000);
    }

    private relativeTime(iso: string): string {
        const diff = Date.now() - new Date(iso).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        const days = Math.floor(hrs / 24);
        return `${days}d ago`;
    }

    private get readCount() {
        return this.totalCount - this.unreadCount;
    }

    /* ── Render ────────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/notifications"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Notification Center">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Notifications</h1>
                    <p class="text-sm text-gray-400 mt-1">Stay informed about system events and updates</p>
                </div>
                <div class="flex gap-2">
                    ${this.tab === 'notifications' ? html`
                    <button class="px-4 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                        aria-label="Mark all notifications as read" @click=${() => this.markAllRead()}>
                        Mark All Read
                    </button>` : ''}
                </div>
            </div>

            <!-- Tabs -->
            <div class="flex gap-1 mb-6 bg-white rounded-lg p-1 border border-gray-100 w-fit" role="tablist">
                ${(['notifications', 'preferences'] as const).map(t => html`
                <button class="px-4 py-2 text-sm font-semibold rounded-md transition-colors ${this.tab === t ? 'bg-brand text-white' : 'text-gray-500 hover:text-ink'}"
                    role="tab" aria-selected=${this.tab === t}
                    @click=${() => { this.tab = t; if (t === 'preferences') this.loadPreferences(); }}>
                    ${t === 'notifications' ? 'Notifications' : 'Preferences'}
                </button>`)}
            </div>

            ${this.tab === 'notifications' ? this.renderNotificationsTab() : this.renderPreferencesTab()}

            ${this.toast ? html`
            <div class="fixed bottom-6 right-6 px-4 py-3 rounded-xl shadow-lg text-sm font-semibold z-50 bg-green-600 text-white">
                ${this.toast}
            </div>` : ''}
        </main>`;
    }

    /* ── Notifications Tab ─────────────────────────────────────────────────── */

    private renderNotificationsTab() {
        return html`
            <!-- Summary Cards -->
            <div class="grid grid-cols-3 gap-4 mb-6">
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Total</div>
                    <div class="text-2xl font-bold">${this.totalCount}</div>
                </div>
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Unread</div>
                    <div class="text-2xl font-bold text-blue-600">${this.unreadCount}</div>
                </div>
                <div class="bg-white rounded-xl border border-gray-100 p-5">
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Read</div>
                    <div class="text-2xl font-bold text-gray-400">${this.readCount}</div>
                </div>
            </div>

            <!-- Filters -->
            <div class="flex gap-2 mb-4">
                <select class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
                    aria-label="Filter by read status"
                    @change=${(e: Event) => { this.readFilter = (e.target as HTMLSelectElement).value as 'all' | 'unread' | 'read'; this.loadNotifications(); }}>
                    <option value="all">All</option>
                    <option value="unread">Unread</option>
                    <option value="read">Read</option>
                </select>
                <select class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
                    aria-label="Filter by notification type"
                    @change=${(e: Event) => { this.typeFilter = (e.target as HTMLSelectElement).value; this.loadNotifications(); }}>
                    <option value="">All Types</option>
                    <option value="information">Information</option>
                    <option value="warning">Warning</option>
                    <option value="error">Error</option>
                    <option value="success">Success</option>
                </select>
                <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                    aria-label="Refresh notifications" @click=${() => this.loadNotifications()}>Refresh</button>
            </div>

            ${this.loading ? html`<div class="text-center text-gray-400 py-16" role="status" aria-live="polite">Loading...</div>` : html`
            <div class="space-y-2" aria-live="polite">
                ${this.notifications.length === 0 ? html`
                <div class="bg-white rounded-xl border border-gray-100 p-12 text-center text-gray-400">
                    No notifications found
                </div>` : ''}
                ${this.notifications.map(n => html`
                <div class="bg-white rounded-xl border border-gray-100 p-4 hover:border-gray-200 transition-all cursor-pointer flex items-start gap-4 ${!n.is_read ? 'border-l-4 border-l-blue-500' : ''}"
                    role="button" tabindex="0" aria-label="${n.title}${!n.is_read ? ' (unread)' : ''}"
                    @click=${() => this.handleNotificationClick(n)}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.handleNotificationClick(n); } }}>
                    <!-- Type Icon -->
                    <div class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center border ${TYPE_COLORS[n.type] || TYPE_COLORS.information}">
                        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <g innerHTML="${TYPE_ICONS[n.type] || TYPE_ICONS.information}"></g>
                        </svg>
                    </div>
                    <!-- Content -->
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2">
                            <h3 class="text-sm font-semibold ${!n.is_read ? 'text-ink' : 'text-gray-600'}">${n.title}</h3>
                            ${!n.is_read ? html`<span class="w-2 h-2 rounded-full ${TYPE_DOT_COLORS[n.type] || 'bg-blue-500'}"></span>` : ''}
                        </div>
                        <p class="text-xs text-gray-500 mt-0.5 line-clamp-2">${n.message}</p>
                        <div class="flex items-center gap-3 mt-2 text-xs text-gray-400">
                            <span class="px-1.5 py-0.5 rounded ${TYPE_COLORS[n.type] || TYPE_COLORS.information}">${n.type}</span>
                            ${n.resource_type ? html`<span>${n.resource_type}</span>` : ''}
                            <span>${this.relativeTime(n.created_at)}</span>
                        </div>
                    </div>
                    <!-- Actions -->
                    <div class="flex-shrink-0">
                        ${!n.is_read ? html`
                        <button class="text-xs text-blue-600 hover:underline px-2 py-1"
                            aria-label="Mark as read"
                            @click=${(e: Event) => { e.stopPropagation(); this.markRead(n.id); }}>Mark Read</button>` : html`
                        <span class="text-xs text-gray-300 px-2 py-1">Read</span>`}
                    </div>
                </div>`)}
            </div>`}
        `;
    }

    /* ── Preferences Tab ───────────────────────────────────────────────────── */

    private renderPreferencesTab() {
        if (this.prefsLoading) {
            return html`<div class="text-center text-gray-400 py-16" role="status" aria-live="polite">Loading preferences...</div>`;
        }

        // Group preferences by event_type
        const grouped = new Map<string, NotificationPreference[]>();
        for (const p of this.preferences) {
            const existing = grouped.get(p.event_type) || [];
            existing.push(p);
            grouped.set(p.event_type, existing);
        }

        return html`
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100">
                    <h2 class="text-sm font-bold">Notification Preferences</h2>
                    <p class="text-xs text-gray-400 mt-0.5">Control which channels receive notifications for each event type</p>
                </div>
                ${grouped.size === 0 ? html`
                <div class="px-5 py-12 text-center text-gray-400">No preferences configured</div>` : html`
                <table class="w-full text-sm" role="table" aria-label="Notification preferences">
                    <thead><tr class="border-b border-gray-100 text-left text-xs text-gray-500 uppercase">
                        <th class="px-5 py-3">Event Type</th>
                        ${CHANNELS.map(ch => html`<th class="px-5 py-3 text-center">${ch.replace('_', '-')}</th>`)}
                    </tr></thead>
                    <tbody>
                    ${Array.from(grouped.entries()).map(([eventType, prefs]) => html`
                    <tr class="border-b border-gray-50 hover:bg-gray-50">
                        <td class="px-5 py-3 font-mono text-xs font-semibold">${eventType}</td>
                        ${CHANNELS.map(ch => {
                            const pref = prefs.find(p => p.channel === ch);
                            if (!pref) return html`<td class="px-5 py-3 text-center text-gray-300">—</td>`;
                            return html`
                            <td class="px-5 py-3 text-center">
                                <button class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${pref.enabled ? 'bg-brand' : 'bg-gray-200'}"
                                    role="switch" aria-checked=${pref.enabled} aria-label="Toggle ${eventType} ${ch}"
                                    @click=${() => this.togglePreference(pref)}>
                                    <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${pref.enabled ? 'translate-x-4.5' : 'translate-x-0.5'}"></span>
                                </button>
                            </td>`;
                        })}
                    </tr>`)}
                    </tbody>
                </table>`}
            </div>
        `;
    }
}
