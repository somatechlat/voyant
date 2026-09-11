import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api } from '../lib/api';
import '../components/saas-sidebar';

interface SettingItem { key: string; value: string; value_type: string; description: string; is_secret: boolean; }

@customElement('view-settings')
export class ViewSettings extends LitElement {
    @state() settings: SettingItem[] = [];
    @state() loading = true;
    @state() editing = '';
    @state() editValue = '';

    createRenderRoot() { return this; }

    async connectedCallback() {
        super.connectedCallback();
        try { this.settings = await api.get<SettingItem[]>('/admin/settings'); }
        catch { this.settings = []; }
        finally { this.loading = false; }
    }

    async save(key: string) {
        await api.put(`/admin/settings/${key}`, { value: this.editValue });
        this.editing = '';
        await this.connectedCallback();
    }

    render() {
        return html`
        <saas-sidebar currentPath="/admin/settings"></saas-sidebar>
        <main class="ml-60 min-h-screen bg-surface p-8" role="main" aria-label="System settings">
            <h1 class="text-2xl font-black font-display tracking-tight mb-6">System Settings</h1>
            ${this.loading ? html`<div class="text-center text-gray-400 py-16" role="status" aria-live="polite">Loading...</div>` : html`
            <div class="space-y-3" aria-live="polite">
                ${this.settings.map(s => html`
                <div class="bg-white rounded-xl border border-gray-100 p-5 hover:border-brand transition-all">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-1">
                                <span class="font-mono text-sm font-semibold">${s.key}</span>
                                <span class="px-1.5 py-0.5 text-xs bg-gray-100 rounded">${s.value_type}</span>
                                ${s.is_secret ? html`<span class="px-1.5 py-0.5 text-xs bg-red-50 text-red-600 rounded">secret</span>` : ''}
                            </div>
                            <p class="text-xs text-gray-400 mb-2">${s.description || 'No description'}</p>
                            ${this.editing === s.key ? html`
                            <div class="flex gap-2 mt-2">
                                <input type="text" class="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg font-mono focus:ring-2 focus:ring-brand focus:outline-none" .value=${this.editValue} @input=${(e: Event) => { this.editValue = (e.target as HTMLInputElement).value; }} />
                                <button class="px-3 py-1.5 text-sm font-semibold bg-brand text-white rounded-lg hover:bg-black" aria-label="Save setting ${s.key}" @click=${() => this.save(s.key)}>Save</button>
                                <button class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50" aria-label="Cancel editing ${s.key}" @click=${() => { this.editing = ''; }}>Cancel</button>
                            </div>` : html`
                            <span class="text-sm font-mono ${s.is_secret ? 'text-gray-300' : 'text-gray-700'}">${s.value}</span>`}
                        </div>
                        ${this.editing !== s.key && !s.is_secret ? html`
                        <button class="text-xs text-brand font-semibold hover:underline ml-4" aria-label="Edit setting ${s.key}" @click=${() => { this.editing = s.key; this.editValue = s.value; }}>Edit</button>` : ''}
                    </div>
                </div>`)}
                ${this.settings.length === 0 ? html`<div class="text-center text-gray-400 py-12">No system settings</div>` : ''}
            </div>`}
        </main>`;
    }
}
