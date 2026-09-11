import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface Workspace {
    id: string;
    name: string;
    description: string;
    owner_id: string;
    is_public: boolean;
    tags: string[];
    tenant_id: string;
    created_at: string;
    updated_at: string;
}

interface WorkspaceMember {
    id: string;
    workspace_id: string;
    user_id: string;
    role: string;
    joined_at: string;
}

interface WorkspaceAsset {
    id: string;
    workspace_id: string;
    asset_type: string;
    asset_id: string;
    shared_by: string;
    shared_at: string;
}

interface Comment {
    id: string;
    workspace_id: string | null;
    asset_type: string;
    asset_id: string;
    content: string;
    parent_comment_id: string | null;
    mentions: string[];
    created_by: string;
    tenant_id: string;
    created_at: string;
    updated_at: string;
}

interface ActivityItem {
    action: string;
    actor: string;
    resource_type: string;
    resource_id: string;
    timestamp: string;
    details: Record<string, unknown>;
}

/* ── Constants ─────────────────────────────────────────────────────────────── */

const ASSET_TYPE_ICONS: Record<string, string> = {
    dashboard: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    dataset: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
    pipeline: '<circle cx="12" cy="12" r="2"/><path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/>',
    model: '<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>',
    query: '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>',
};

const ROLE_COLORS: Record<string, string> = {
    owner: 'bg-purple-50 text-purple-700 border-purple-200',
    admin: 'bg-blue-50 text-blue-700 border-blue-200',
    member: 'bg-green-50 text-green-700 border-green-200',
    viewer: 'bg-gray-50 text-gray-500 border-gray-200',
};

/* ── Component ─────────────────────────────────────────────────────────────── */

@customElement('view-workspaces')
export class ViewWorkspaces extends LitElement {
    @state() workspaces: Workspace[] = [];
    @state() loading = true;

    // Create modal
    @state() showCreate = false;
    @state() createName = '';
    @state() createDescription = '';
    @state() createIsPublic = false;
    @state() creating = false;

    // Detail panel
    @state() selectedWs: Workspace | null = null;
    @state() detailTab: 'overview' | 'members' | 'assets' | 'comments' | 'activity' = 'overview';
    @state() members: WorkspaceMember[] = [];
    @state() assets: WorkspaceAsset[] = [];
    @state() comments: Comment[] = [];
    @state() activity: ActivityItem[] = [];
    @state() detailLoading = false;

    // Add member form
    @state() newMemberId = '';
    @state() newMemberRole = 'member';

    // Comment form
    @state() commentText = '';

    // Toast
    @state() toast = '';

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        await this.loadWorkspaces();
    }

    /* ── Data loading ──────────────────────────────────────────────────────── */

    async loadWorkspaces() {
        this.loading = true;
        try {
            this.workspaces = await api.get<Workspace[]>('/workspaces?limit=100');
        } catch { this.workspaces = []; }
        finally { this.loading = false; }
    }

    async openDetail(ws: Workspace) {
        this.selectedWs = ws;
        this.detailTab = 'overview';
        await this.loadDetailData();
    }

    async loadDetailData() {
        if (!this.selectedWs) return;
        this.detailLoading = true;
        const wsId = this.selectedWs.id;
        try {
            const [members, assets, comments, activity] = await Promise.all([
                api.get<WorkspaceMember[]>(`/workspaces/${wsId}/members`).catch(() => []),
                api.get<WorkspaceAsset[]>(`/workspaces/${wsId}/assets`).catch(() => []),
                api.get<Comment[]>(`/workspaces/${wsId}/comments`).catch(() => []),
                api.get<ActivityItem[]>(`/workspaces/${wsId}/activity`).catch(() => []),
            ]);
            this.members = members;
            this.assets = assets;
            this.comments = comments;
            this.activity = activity;
        } finally { this.detailLoading = false; }
    }

    /* ── Actions ───────────────────────────────────────────────────────────── */

    async createWorkspace() {
        if (!this.createName.trim()) return;
        this.creating = true;
        try {
            await api.post('/workspaces', {
                name: this.createName,
                description: this.createDescription,
                is_public: this.createIsPublic,
            });
            this.showCreate = false;
            this.createName = '';
            this.createDescription = '';
            this.createIsPublic = false;
            this.showToast('Workspace created');
            await this.loadWorkspaces();
        } catch { this.showToast('Failed to create workspace'); }
        finally { this.creating = false; }
    }

    async deleteWorkspace(wsId: string) {
        if (!confirm('Delete this workspace? This cannot be undone.')) return;
        try {
            await api.del(`/workspaces/${wsId}`);
            this.selectedWs = null;
            this.showToast('Workspace deleted');
            await this.loadWorkspaces();
        } catch { this.showToast('Failed to delete workspace'); }
    }

    async addMember() {
        if (!this.selectedWs || !this.newMemberId.trim()) return;
        try {
            await api.post(`/workspaces/${this.selectedWs.id}/members`, {
                user_id: this.newMemberId,
                role: this.newMemberRole,
            });
            this.newMemberId = '';
            this.showToast('Member added');
            await this.loadDetailData();
        } catch { this.showToast('Failed to add member'); }
    }

    async removeMember(userId: string) {
        if (!this.selectedWs) return;
        if (!confirm(`Remove ${userId} from this workspace?`)) return;
        try {
            await api.del(`/workspaces/${this.selectedWs.id}/members/${userId}`);
            this.showToast('Member removed');
            await this.loadDetailData();
        } catch { this.showToast('Failed to remove member'); }
    }

    async postComment() {
        if (!this.selectedWs || !this.commentText.trim()) return;
        try {
            await api.post(`/workspaces/${this.selectedWs.id}/comments`, {
                content: this.commentText,
            });
            this.commentText = '';
            await this.loadDetailData();
        } catch { this.showToast('Failed to post comment'); }
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

    private activityIcon(action: string) {
        if (action === 'member.joined') return '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/>';
        if (action === 'asset.shared') return '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>';
        return '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>';
    }

    /* ── Render ────────────────────────────────────────────────────────────── */

    render() {
        return html`
        <saas-sidebar currentPath="/admin/workspaces"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-gray-50 p-8" role="main" aria-label="Workspace Management">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-black font-display tracking-tight">Workspaces</h1>
                    <p class="text-sm text-gray-400 mt-1">Collaborate with your team on shared resources</p>
                </div>
                <button class="px-4 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                    aria-label="Create new workspace" @click=${() => { this.showCreate = true; }}>
                    + New Workspace
                </button>
            </div>

            ${this.loading ? html`<div class="text-center text-gray-400 py-16" role="status" aria-live="polite">Loading...</div>` : html`
            <!-- Workspace Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" aria-live="polite">
                ${this.workspaces.length === 0 ? html`
                <div class="col-span-3 text-center text-gray-400 py-12">No workspaces found. Create one to get started.</div>` : ''}
                ${this.workspaces.map(ws => html`
                <div class="bg-white rounded-xl border border-gray-100 p-5 hover:border-brand hover:shadow-md transition-all group cursor-pointer"
                    role="article" tabindex="0" aria-label="Workspace: ${ws.name}"
                    @click=${() => this.openDetail(ws)}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.openDetail(ws); } }}>
                    <div class="flex items-start justify-between mb-3">
                        <div class="min-w-0 flex-1">
                            <h3 class="font-bold text-sm group-hover:text-brand transition-colors truncate">${ws.name}</h3>
                            <p class="text-xs text-gray-400 truncate mt-0.5">${ws.description || 'No description'}</p>
                        </div>
                        <span class="flex-shrink-0 ml-2 px-2 py-0.5 text-xs rounded border ${ws.is_public ? 'bg-green-50 text-green-700 border-green-200' : 'bg-gray-50 text-gray-500 border-gray-200'}">
                            ${ws.is_public ? 'Public' : 'Private'}
                        </span>
                    </div>
                    ${ws.tags.length > 0 ? html`
                    <div class="flex flex-wrap gap-1 mb-3">
                        ${ws.tags.map(t => html`<span class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-500">${t}</span>`)}
                    </div>` : ''}
                    <div class="flex items-center gap-4 text-xs text-gray-400 pt-3 border-t border-gray-50">
                        <span>Owner: ${ws.owner_id}</span>
                        <span>${this.relativeTime(ws.created_at)}</span>
                    </div>
                </div>`)}
            </div>`}

            <!-- Detail Slide-in Panel -->
            ${this.selectedWs ? this.renderDetailPanel() : ''}

            <!-- Create Modal -->
            ${this.showCreate ? this.renderCreateModal() : ''}

            <!-- Toast -->
            ${this.toast ? html`
            <div class="fixed bottom-6 right-6 px-4 py-3 rounded-xl shadow-lg text-sm font-semibold z-50 bg-green-600 text-white">
                ${this.toast}
            </div>` : ''}
        </main>`;
    }

    /* ── Create Modal ──────────────────────────────────────────────────────── */

    private renderCreateModal() {
        return html`
        <div class="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Create Workspace"
            @keydown=${(e: KeyboardEvent) => { if (e.key === 'Escape') this.showCreate = false; }}>
            <div class="absolute inset-0 bg-black/30" @click=${() => { this.showCreate = false; }}></div>
            <div class="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden" tabindex="-1">
                <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <h2 class="text-lg font-bold">Create Workspace</h2>
                    <button class="text-gray-400 hover:text-ink text-xl" aria-label="Close" @click=${() => { this.showCreate = false; }}>✕</button>
                </div>
                <div class="p-6 space-y-4">
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Name *</label>
                        <input type="text" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"
                            placeholder="My Workspace" .value=${this.createName}
                            @input=${(e: Event) => { this.createName = (e.target as HTMLInputElement).value; }} />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Description</label>
                        <textarea class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg h-20 resize-none"
                            placeholder="What is this workspace for?"
                            .value=${this.createDescription}
                            @input=${(e: Event) => { this.createDescription = (e.target as HTMLTextAreaElement).value; }}></textarea>
                    </div>
                    <div class="flex items-center gap-3">
                        <label class="text-xs font-medium text-gray-500">Visibility:</label>
                        <button class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${this.createIsPublic ? 'bg-brand' : 'bg-gray-200'}"
                            role="switch" aria-checked=${this.createIsPublic} aria-label="Toggle public visibility"
                            @click=${() => { this.createIsPublic = !this.createIsPublic; }}>
                            <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${this.createIsPublic ? 'translate-x-4.5' : 'translate-x-0.5'}"></span>
                        </button>
                        <span class="text-xs text-gray-500">${this.createIsPublic ? 'Public — visible to all tenant users' : 'Private — invite only'}</span>
                    </div>
                </div>
                <div class="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 bg-gray-50">
                    <button class="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
                        @click=${() => { this.showCreate = false; }}>Cancel</button>
                    <button class="px-4 py-2 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors ${this.creating || !this.createName.trim() ? 'opacity-50 pointer-events-none' : ''}"
                        @click=${() => this.createWorkspace()}>
                        ${this.creating ? 'Creating...' : 'Create'}
                    </button>
                </div>
            </div>
        </div>`;
    }

    /* ── Detail Panel ──────────────────────────────────────────────────────── */

    private renderDetailPanel() {
        const ws = this.selectedWs!;
        return html`
        <div class="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true" aria-label="Workspace: ${ws.name}">
            <div class="absolute inset-0 bg-black/20" @click=${() => { this.selectedWs = null; }}></div>
            <div class="relative w-full max-w-2xl bg-white shadow-2xl flex flex-col overflow-hidden">
                <!-- Panel Header -->
                <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <div>
                        <h2 class="text-lg font-bold">${ws.name}</h2>
                        <p class="text-xs text-gray-400">${ws.is_public ? 'Public' : 'Private'} workspace · Owner: ${ws.owner_id}</p>
                    </div>
                    <div class="flex gap-2">
                        <button class="text-xs text-red-600 hover:underline" @click=${() => this.deleteWorkspace(ws.id)}>Delete</button>
                        <button class="text-gray-400 hover:text-ink text-xl" aria-label="Close panel" @click=${() => { this.selectedWs = null; }}>✕</button>
                    </div>
                </div>

                <!-- Detail Tabs -->
                <div class="flex gap-1 px-6 pt-3 border-b border-gray-100" role="tablist">
                    ${(['overview', 'members', 'assets', 'comments', 'activity'] as const).map(t => html`
                    <button class="px-3 py-2 text-xs font-semibold rounded-t-md transition-colors ${this.detailTab === t ? 'bg-gray-50 text-brand border-b-2 border-brand' : 'text-gray-400 hover:text-ink'}"
                        role="tab" aria-selected=${this.detailTab === t}
                        @click=${() => { this.detailTab = t; }}>
                        ${t.charAt(0).toUpperCase() + t.slice(1)}
                    </button>`)}
                </div>

                <!-- Panel Content -->
                <div class="flex-1 overflow-y-auto p-6">
                    ${this.detailLoading ? html`<div class="text-center text-gray-400 py-8">Loading...</div>` : ''}
                    ${!this.detailLoading && this.detailTab === 'overview' ? this.renderOverviewTab(ws) : ''}
                    ${!this.detailLoading && this.detailTab === 'members' ? this.renderMembersTab() : ''}
                    ${!this.detailLoading && this.detailTab === 'assets' ? this.renderAssetsTab() : ''}
                    ${!this.detailLoading && this.detailTab === 'comments' ? this.renderCommentsTab() : ''}
                    ${!this.detailLoading && this.detailTab === 'activity' ? this.renderActivityTab() : ''}
                </div>
            </div>
        </div>`;
    }

    private renderOverviewTab(ws: Workspace) {
        return html`
        <div class="space-y-4">
            <div>
                <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Description</div>
                <div class="text-sm text-gray-700">${ws.description || 'No description provided'}</div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Owner</div>
                    <div class="text-sm font-mono">${ws.owner_id}</div>
                </div>
                <div>
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Visibility</div>
                    <span class="px-2 py-0.5 text-xs rounded border ${ws.is_public ? 'bg-green-50 text-green-700 border-green-200' : 'bg-gray-50 text-gray-500 border-gray-200'}">
                        ${ws.is_public ? 'Public' : 'Private'}
                    </span>
                </div>
                <div>
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Created</div>
                    <div class="text-sm">${new Date(ws.created_at).toLocaleString()}</div>
                </div>
                <div>
                    <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Last Updated</div>
                    <div class="text-sm">${new Date(ws.updated_at).toLocaleString()}</div>
                </div>
            </div>
            ${ws.tags.length > 0 ? html`
            <div>
                <div class="text-xs text-gray-400 uppercase tracking-wider mb-1">Tags</div>
                <div class="flex flex-wrap gap-1">
                    ${ws.tags.map(t => html`<span class="px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-600">${t}</span>`)}
                </div>
            </div>` : ''}
        </div>`;
    }

    private renderMembersTab() {
        return html`
        <div>
            <!-- Add Member Form -->
            <div class="flex gap-2 mb-4">
                <input type="text" class="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg"
                    placeholder="User ID" .value=${this.newMemberId}
                    @input=${(e: Event) => { this.newMemberId = (e.target as HTMLInputElement).value; }} />
                <select class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
                    .value=${this.newMemberRole}
                    @change=${(e: Event) => { this.newMemberRole = (e.target as HTMLSelectElement).value; }}>
                    <option value="viewer">Viewer</option>
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                </select>
                <button class="px-3 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                    @click=${() => this.addMember()}>Add</button>
            </div>

            <!-- Member List -->
            <div class="space-y-2">
                ${this.members.length === 0 ? html`<div class="text-center text-gray-400 py-8">No members yet</div>` : ''}
                ${this.members.map(m => html`
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-500">
                            ${m.user_id.charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <div class="text-sm font-semibold">${m.user_id}</div>
                            <div class="text-xs text-gray-400">Joined ${this.relativeTime(m.joined_at)}</div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-0.5 text-xs rounded border ${ROLE_COLORS[m.role] || ROLE_COLORS.viewer}">${m.role}</span>
                        ${m.role !== 'owner' ? html`
                        <button class="text-xs text-red-600 hover:underline"
                            @click=${() => this.removeMember(m.user_id)}>Remove</button>` : ''}
                    </div>
                </div>`)}
            </div>
        </div>`;
    }

    private renderAssetsTab() {
        return html`
        <div class="space-y-2">
            ${this.assets.length === 0 ? html`<div class="text-center text-gray-400 py-8">No shared assets</div>` : ''}
            ${this.assets.map(a => html`
            <div class="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div class="w-8 h-8 rounded-lg bg-white border border-gray-200 flex items-center justify-center">
                    <svg class="w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                        ><g innerHTML="${ASSET_TYPE_ICONS[a.asset_type] || ASSET_TYPE_ICONS.dataset}"></g></svg>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-semibold truncate">${a.asset_id}</div>
                    <div class="text-xs text-gray-400">${a.asset_type} · Shared by ${a.shared_by}</div>
                </div>
                <div class="text-xs text-gray-400">${this.relativeTime(a.shared_at)}</div>
            </div>`)}
        </div>`;
    }

    private renderCommentsTab() {
        // Build comment tree — separate top-level and replies
        const topLevel = this.comments.filter(c => !c.parent_comment_id);
        const repliesOf = (parentId: string) => this.comments.filter(c => c.parent_comment_id === parentId);

        const renderComment = (c: Comment, depth = 0): ReturnType<typeof html> => {
            const replies = repliesOf(c.id);
            return html`
            <div class="${depth > 0 ? 'ml-8 border-l-2 border-gray-100 pl-4' : ''} mb-3">
                <div class="p-3 bg-gray-50 rounded-lg">
                    <div class="flex items-center gap-2 mb-1">
                        <div class="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center text-[10px] font-bold text-gray-500">
                            ${c.created_by.charAt(0).toUpperCase()}
                        </div>
                        <span class="text-xs font-semibold">${c.created_by}</span>
                        <span class="text-xs text-gray-400">${this.relativeTime(c.created_at)}</span>
                        ${c.mentions.length > 0 ? html`
                        <span class="text-xs text-blue-500">${c.mentions.map(m => '@' + m).join(' ')}</span>` : ''}
                    </div>
                    <p class="text-sm text-gray-700">${c.content}</p>
                </div>
                ${replies.map(r => renderComment(r, depth + 1))}
            </div>`;
        };

        return html`
        <div>
            <!-- Comment Input -->
            <div class="flex gap-2 mb-4">
                <input type="text" class="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg"
                    placeholder="Write a comment... Use @user to mention"
                    .value=${this.commentText}
                    @input=${(e: Event) => { this.commentText = (e.target as HTMLInputElement).value; }}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter') this.postComment(); }} />
                <button class="px-3 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black transition-colors"
                    @click=${() => this.postComment()}>Post</button>
            </div>
            <!-- Comment List -->
            ${this.comments.length === 0 ? html`<div class="text-center text-gray-400 py-8">No comments yet</div>` : ''}
            ${topLevel.map(c => renderComment(c))}
        </div>`;
    }

    private renderActivityTab() {
        return html`
        <div class="space-y-3">
            ${this.activity.length === 0 ? html`<div class="text-center text-gray-400 py-8">No activity yet</div>` : ''}
            ${this.activity.map(a => html`
            <div class="flex items-start gap-3">
                <div class="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
                    <svg class="w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <g innerHTML="${this.activityIcon(a.action)}"></g>
                    </svg>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-sm">
                        <span class="font-semibold">${a.actor}</span>
                        ${a.action === 'member.joined' ? ' joined the workspace' : ''}
                        ${a.action === 'asset.shared' ? ` shared a ${a.resource_type}` : ''}
                        ${a.action === 'comment.created' ? ' posted a comment' : ''}
                    </div>
                    <div class="text-xs text-gray-400 mt-0.5">${this.relativeTime(a.timestamp)}</div>
                </div>
            </div>`)}
        </div>`;
    }
}
