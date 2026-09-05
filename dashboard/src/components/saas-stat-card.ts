import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('saas-stat-card')
export class SaaSStatCard extends LitElement {
    @property({ type: String }) label = '';
    @property({ type: String }) value = '0';
    @property({ type: String }) icon = '';
    @property({ type: String }) color = 'gray'; // gray | green | red | blue | amber
    @property({ type: String }) sub = '';

    createRenderRoot() { return this; }

    render() {
        const colorMap: Record<string, string> = {
            gray: 'bg-gray-100 text-gray-600',
            green: 'bg-green-50 text-green-600',
            red: 'bg-red-50 text-red-600',
            blue: 'bg-blue-50 text-blue-600',
            amber: 'bg-amber-50 text-amber-600',
        };
        const iconBg = colorMap[this.color] || colorMap.gray;

        return html`
        <div class="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow">
            <div class="flex items-center justify-between mb-3">
                <span class="text-xs font-medium text-gray-400 uppercase tracking-wider">${this.label}</span>
                ${this.icon ? html`
                <div class="h-8 w-8 rounded-lg ${iconBg} flex items-center justify-center">
                    <span class="text-sm">${this.icon}</span>
                </div>` : ''}
            </div>
            <div class="text-2xl font-semibold text-gray-900">${this.value}</div>
            ${this.sub ? html`<div class="text-xs text-gray-400 mt-1">${this.sub}</div>` : ''}
        </div>`;
    }
}
