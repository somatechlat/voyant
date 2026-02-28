import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import '../components/saas-layout';

@customElement('view-login')
export class ViewLogin extends LitElement {
    @state() loading = false;

    createRenderRoot() {
        return this;
    }

    async handleLogin() {
        this.loading = true;
        this.requestUpdate();
        // Simulate login delay
        await new Promise(r => setTimeout(r, 800));
        // Navigate to setup (client-side routing)
        window.history.pushState({}, '', '/admin/setup');
        window.dispatchEvent(new PopStateEvent('popstate'));
        // Note: In a real app the Router would handle this cleaner, but dispatching popstate triggers lit-router re-render if compatible
    }

    render() {
        return html`
      <saas-layout>
        <!-- Header -->
        <header class="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-6">
          <div class="flex items-center gap-3">
            <div class="h-8 w-8 rounded-lg bg-saas-text flex items-center justify-center">
              <div class="h-3 w-3 bg-white rounded-full"></div>
            </div>
            <span class="font-bold text-lg tracking-tight text-saas-text">AgentVoiceBox</span>
          </div>
        </header>

        <!-- Main Card -->
        <main class="flex min-h-screen flex-1 flex-col items-center justify-center px-4">
          <div class="relative w-full max-w-[400px]">
            <div class="overflow-hidden rounded-2xl bg-saas-card p-10 shadow-xl border border-black/5">
              
              <div class="mb-8 text-center">
                <h1 class="text-2xl font-bold tracking-tight text-saas-text mb-2">Welcome Back</h1>
                <p class="text-sm text-gray-500">Sign in to access your platform</p>
              </div>

              <div class="space-y-4">
                <button
                  @click="${this.handleLogin}"
                  ?disabled="${this.loading}"
                  class="relative flex w-full items-center justify-center rounded-xl bg-saas-text px-4 py-4 text-sm font-semibold text-white transition-transform active:scale-[0.98] hover:bg-black/90 disabled:opacity-70 disabled:cursor-not-allowed ${this.loading ? 'cursor-wait' : ''}"
                >
                  ${this.loading ? html`<span class="animate-pulse">Redirecting...</span>` : 'Sign in with SSO'}
                </button>

                <div class="relative py-2">
                  <div class="absolute inset-0 flex items-center"><span class="w-full border-t border-gray-100"></span></div>
                  <div class="relative flex justify-center text-xs uppercase"><span class="bg-saas-card px-2 text-gray-400">Or continue with</span></div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <button class="flex h-12 items-center justify-center rounded-xl border border-gray-100 bg-white hover:bg-gray-50 transition-colors">
                    <span class="text-sm font-medium text-saas-text">Google</span>
                  </button>
                  <button class="flex h-12 items-center justify-center rounded-xl border border-gray-100 bg-white hover:bg-gray-50 transition-colors">
                    <span class="text-sm font-medium text-saas-text">GitHub</span>
                  </button>
                </div>
              </div>

              <div class="mt-8 text-center text-xs text-gray-400">
                <p>Secure Enterprise Gateway v2.0</p>
              </div>
              
            </div>
          </div>
        </main>
      </saas-layout>
    `;
    }
}
