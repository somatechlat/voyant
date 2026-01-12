import { LitElement, html, css } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('saas-layout')
export class SaaSLayout extends LitElement {
    createRenderRoot() {
        return this; // Disable Shadow DOM to use global Tailwind styles
    }

    render() {
        return html`
      <div class="min-h-screen w-full bg-saas-page text-saas-text antialiased selection:bg-black selection:text-white">
        <!-- Optional Global Header or Abstract Background here -->
        <div class="relative z-10 flex min-h-screen flex-col">
          <slot></slot>
        </div>
      </div>
    `;
    }
}
