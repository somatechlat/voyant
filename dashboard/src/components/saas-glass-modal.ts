import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('saas-glass-modal')
export class GlassModal extends LitElement {
    @property({ type: Boolean }) open = false;
    @property({ type: String }) title = '';

    createRenderRoot() {
        return this; // Disable Shadow DOM specifically to simpler Tailwind integration in Phase 1
    }

    close() {
        this.dispatchEvent(new CustomEvent('close'));
    }

    render() {
        if (!this.open) return html``;

        return html`
      <div class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- Backdrop -->
        <div 
          class="absolute inset-0 bg-black/5 backdrop-blur-xl transition-opacity animate-[fadeIn_0.2s_ease-out]"
          @click="${this.close}"
        ></div>

        <!-- Content -->
        <div class="relative z-10 w-full max-w-lg overflow-hidden rounded-2xl border border-white/20 bg-white/70 p-6 shadow-2xl backdrop-blur-md animate-[scaleIn_0.2s_ease-out]">
          <div class="mb-6 flex items-center justify-between">
            <h2 class="text-xl font-semibold text-saas-text">${this.title}</h2>
            <button @click="${this.close}" class="rounded-full p-2 text-gray-500 hover:bg-black/5 hover:text-black transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>
          <slot></slot>
        </div>
      </div>
    `;
    }
}
