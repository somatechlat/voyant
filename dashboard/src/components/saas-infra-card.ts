import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import './saas-status-dot';

@customElement('saas-infra-card')
export class InfraCard extends LitElement {
    @property({ type: String }) name = '';
    @property({ type: String }) status: 'connected' | 'error' | 'pending' = 'pending';

    createRenderRoot() {
        return this;
    }

    render() {
        return html`
      <div class="flex items-center justify-between rounded-xl bg-white p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
        <div class="flex items-center gap-4">
          <saas-status-dot status="${this.status}"></saas-status-dot>
          <div>
            <h3 class="font-semibold text-saas-text">${this.name}</h3>
            <p class="text-xs text-gray-500 capitalize">${this.status}</p>
          </div>
        </div>
        
        <button 
          class="rounded-lg p-2 text-gray-400 hover:bg-gray-50 hover:text-saas-text transition-colors"
          @click="${() => this.dispatchEvent(new CustomEvent('edit'))}"
          aria-label="Edit Configuration"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>
        </button>
      </div>
    `;
    }
}
