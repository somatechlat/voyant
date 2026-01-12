import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('saas-status-dot')
export class StatusDot extends LitElement {
    @property({ type: String }) status: 'connected' | 'error' | 'pending' = 'pending';

    createRenderRoot() {
        return this;
    }

    render() {
        const statusConfig = {
            connected: {
                color: "bg-saas-success",
                shadow: "shadow-[0_0_8px_#22c55e]",
                animate: "animate-pulse"
            },
            error: {
                color: "bg-red-500",
                shadow: "shadow-[0_0_8px_#ef4444]",
                animate: ""
            },
            pending: {
                color: "bg-yellow-400",
                shadow: "shadow-[0_0_8px_#facc15]",
                animate: "animate-pulse"
            }
        };

        const config = statusConfig[this.status] || statusConfig.pending;

        return html`
      <div
        class="h-3 w-3 rounded-full ${config.color} ${config.shadow} ${config.animate}"
        aria-label="Status: ${this.status}"
      ></div>
    `;
    }
}
