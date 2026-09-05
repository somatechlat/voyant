import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { api, setToken, isAuthenticated } from '../lib/api';

@customElement('view-login')
export class ViewLogin extends LitElement {
    @state() loading = false;
    @state() error = '';
    @state() username = '';
    @state() password = '';

    createRenderRoot() { return this; }

    connectedCallback() {
        super.connectedCallback();
        if (isAuthenticated()) {
            this.navigate('/admin');
        }
    }

    private navigate(path: string) {
        window.history.pushState({}, '', path);
        window.dispatchEvent(new PopStateEvent('popstate'));
    }

    async handleLogin(e: Event) {
        e.preventDefault();
        this.loading = true;
        this.error = '';

        try {
            // In production, this would call Keycloak token endpoint.
            // For now, we accept any credentials in local mode and
            // the API returns a mock token.
            const res = await fetch('/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: this.username,
                    password: this.password,
                }),
            });

            if (res.ok) {
                const data = await res.json();
                setToken(data.token || data.access_token || '');
                this.navigate('/admin');
            } else if (res.status === 401) {
                this.error = 'Invalid credentials';
            } else {
                // In local dev mode without auth, skip login
                setToken('local-dev-token');
                this.navigate('/admin');
            }
        } catch {
            // If auth endpoint doesn't exist (local mode), allow through
            setToken('local-dev-token');
            this.navigate('/admin');
        } finally {
            this.loading = false;
        }
    }

    render() {
        return html`
        <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <div class="w-full max-w-sm">
                <!-- Logo -->
                <div class="text-center mb-8">
                    <div class="h-12 w-12 rounded-xl bg-gray-900 flex items-center justify-center mx-auto mb-4">
                        <svg class="h-6 w-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/>
                            <line x1="12" y1="22" x2="12" y2="15.5"/>
                            <polyline points="22 8.5 12 15.5 2 8.5"/>
                        </svg>
                    </div>
                    <h1 class="text-xl font-semibold text-gray-900">Voyant Admin</h1>
                    <p class="text-sm text-gray-500 mt-1">Sign in to manage your data platform</p>
                </div>

                <!-- Form -->
                <form @submit=${this.handleLogin} class="bg-white rounded-xl border border-gray-100 p-6 shadow-sm">
                    ${this.error ? html`
                    <div class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                        ${this.error}
                    </div>` : ''}

                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-1.5">Username</label>
                        <input
                            type="text"
                            .value=${this.username}
                            @input=${(e: Event) => { this.username = (e.target as HTMLInputElement).value; }}
                            class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
                            placeholder="admin"
                            autocomplete="username"
                        />
                    </div>

                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
                        <input
                            type="password"
                            .value=${this.password}
                            @input=${(e: Event) => { this.password = (e.target as HTMLInputElement).value; }}
                            class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
                            placeholder="••••••••"
                            autocomplete="current-password"
                        />
                    </div>

                    <button
                        type="submit"
                        ?disabled=${this.loading}
                        class="w-full py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
                    >
                        ${this.loading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>
            </div>
        </div>`;
    }
}
