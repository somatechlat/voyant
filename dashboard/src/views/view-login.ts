import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { setToken, isAuthenticated } from '../lib/api';

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
                setToken(data.access_token);

                // Store user info and refresh token
                if (data.user) {
                    localStorage.setItem('voyant_user', JSON.stringify(data.user));
                }
                if (data.refresh_token) {
                    localStorage.setItem('voyant_refresh_token', data.refresh_token);
                }

                this.navigate('/admin');
            } else {
                const data = await res.json().catch(() => ({}));
                this.error = data.detail || data.message || 'Invalid credentials';
            }
        } catch (err) {
            // Fallback for local dev without Keycloak (only when VITE_ALLOW_LOCAL_LOGIN is enabled)
            if (import.meta.env.VITE_ALLOW_LOCAL_LOGIN && window.location.hostname === 'localhost') {
                setToken('local-dev-token');
                this.navigate('/admin');
            } else {
                this.error = 'Authentication service unavailable';
            }
        } finally {
            this.loading = false;
        }
    }

    render() {
        return html`
        <div role="main" aria-label="Login page" style="min-height:100vh;background:var(--saas-bg-page);display:flex;align-items:center;justify-content:center;padding:16px;font-family:Inter,system-ui,sans-serif">
            <div style="width:100%;max-width:380px">
                <!-- Logo -->
                <div style="text-align:center;margin-bottom:32px">
                    <div aria-hidden="true" style="width:48px;height:48px;border-radius:12px;background:#050505;display:flex;align-items:center;justify-content:center;margin:0 auto 16px">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                            <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/>
                            <line x1="12" y1="22" x2="12" y2="15.5"/>
                            <polyline points="22 8.5 12 15.5 2 8.5"/>
                        </svg>
                    </div>
                    <h1 style="font-size:20px;font-weight:700;color:#050505;margin:0">Voyant</h1>
                    <p style="font-size:13px;color:#4B5563;margin-top:4px">Sign in to your data platform</p>
                </div>

                <!-- Form -->
                <form @submit=${this.handleLogin} style="background:white;border-radius:12px;border:1px solid #E5E7EB;padding:24px">
                    ${this.error ? html`
                    <div role="alert" aria-live="assertive" style="margin-bottom:16px;padding:10px 14px;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);border-radius:8px;font-size:13px;color:#EF4444">
                        ${this.error}
                    </div>` : ''}

                    <div style="margin-bottom:16px">
                        <label style="display:block;font-size:12px;font-weight:600;color:#374151;margin-bottom:6px">Username</label>
                        <input type="text"
                            .value=${this.username}
                            @input=${(e: Event) => { this.username = (e.target as HTMLInputElement).value; }}
                            style="width:100%;padding:8px 12px;border:1px solid #E5E7EB;border-radius:8px;font-size:13px;outline:none;transition:border-color 120ms"
                            placeholder="admin"
                            autocomplete="username"
                            @focus=${(e: Event) => { (e.target as HTMLElement).style.borderColor = '#FF4D00'; }}
                            @blur=${(e: Event) => { (e.target as HTMLElement).style.borderColor = '#E5E7EB'; }}
                        />
                    </div>

                    <div style="margin-bottom:24px">
                        <label style="display:block;font-size:12px;font-weight:600;color:#374151;margin-bottom:6px">Password</label>
                        <input type="password"
                            .value=${this.password}
                            @input=${(e: Event) => { this.password = (e.target as HTMLInputElement).value; }}
                            style="width:100%;padding:8px 12px;border:1px solid #E5E7EB;border-radius:8px;font-size:13px;outline:none;transition:border-color 120ms"
                            placeholder="••••••••"
                            autocomplete="current-password"
                            @focus=${(e: Event) => { (e.target as HTMLElement).style.borderColor = '#FF4D00'; }}
                            @blur=${(e: Event) => { (e.target as HTMLElement).style.borderColor = '#E5E7EB'; }}
                        />
                    </div>

                    <button type="submit" ?disabled=${this.loading} aria-label="${this.loading ? 'Signing in, please wait' : 'Sign in'}"
                        style="width:100%;padding:10px;background:${this.loading ? '#ccc' : '#FF4D00'};color:white;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:${this.loading ? 'wait' : 'pointer'};transition:all 120ms">
                        ${this.loading ? 'Signing in...' : 'Sign In'}
                    </button>

                    <p style="text-align:center;font-size:11px;color:#4B5563;margin-top:12px">
                        Authenticated via Keycloak · JWT + RBAC
                    </p>
                </form>
            </div>
        </div>`;
    }
}
