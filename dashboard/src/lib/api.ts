/**
 * Voyant Admin API Client
 *
 * Handles authentication, request/response, and error handling
 * for all /v1/admin/* endpoints.
 */

const API_BASE = (import.meta.env.VITE_API_URL as string) || '/v1';

export class ApiError extends Error {
    constructor(public status: number, message: string, public body?: unknown) {
        super(message);
    }
}

function getToken(): string | null {
    return localStorage.getItem('voyant_token');
}

export function setToken(token: string): void {
    localStorage.setItem('voyant_token', token);
}

export function clearToken(): void {
    localStorage.removeItem('voyant_token');
}

export function isAuthenticated(): boolean {
    return !!getToken();
}

let _refreshing: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
    if (_refreshing) return _refreshing;
    _refreshing = (async () => {
        const refreshToken = localStorage.getItem('voyant_refresh_token');
        if (!refreshToken) return false;
        try {
            const res = await fetch(`${API_BASE}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });
            if (res.ok) {
                const data = await res.json();
                setToken(data.access_token);
                if (data.refresh_token) {
                    localStorage.setItem('voyant_refresh_token', data.refresh_token);
                }
                return true;
            }
            return false;
        } catch { return false; }
        finally { _refreshing = null; }
    })();
    return _refreshing;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const opts: RequestInit = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    let res = await fetch(`${API_BASE}${path}`, opts);

    // Try token refresh on 401
    if (res.status === 401) {
        const refreshed = await tryRefreshToken();
        if (refreshed) {
            headers['Authorization'] = `Bearer ${getToken()}`;
            res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
        }
    }

    if (res.status === 401) {
        clearToken();
        localStorage.removeItem('voyant_refresh_token');
        localStorage.removeItem('voyant_user');
        window.location.href = '/admin/login';
        throw new ApiError(401, 'Unauthorized');
    }

    if (!res.ok) {
        const text = await res.text();
        let errBody: unknown;
        try { errBody = JSON.parse(text); } catch { errBody = text; }
        throw new ApiError(res.status, `API error ${res.status}: ${text}`, errBody);
    }

    return res.json() as Promise<T>;
}

// ── HTTP verbs ──────────────────────────────────────────────────────────────

export const api = {
    get: <T>(path: string) => request<T>('GET', path),
    post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
    put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
    del: <T>(path: string) => request<T>('DELETE', path),
};

// ── Type exports matching admin_panel/schemas.py ────────────────────────────

export interface DashboardStats {
    total_jobs: number;
    jobs_running: number;
    jobs_queued: number;
    jobs_failed: number;
    jobs_completed: number;
    total_sources: number;
    sources_active: number;
    total_artifacts: number;
    total_capsules: number;
    total_tenants: number;
    active_tenants: number;
    audit_events_24h: number;
    policy_violations_24h: number;
}

export interface ServiceHealth {
    name: string;
    status: string;
    details: string;
    circuit_breaker_state: string;
    last_check: string;
}

export interface SystemOverview {
    version: string;
    env: string;
    debug: boolean;
    uptime_seconds: number;
    services: ServiceHealth[];
    stats: DashboardStats;
}

export interface JobListItem {
    job_id: string;
    tenant_id: string;
    job_type: string;
    status: string;
    progress: number;
    source_id: string | null;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
}

export interface JobDetail extends JobListItem {
    soma_session_id: string | null;
    parameters: Record<string, unknown>;
    result_summary: Record<string, unknown> | null;
    artifacts: Array<{
        artifact_id: string;
        artifact_type: string;
        format: string;
        storage_path: string;
        size_bytes: number | null;
    }>;
}

export interface SourceListItem {
    source_id: string;
    tenant_id: string;
    name: string;
    source_type: string;
    status: string;
    created_at: string;
    datahub_urn: string | null;
}

export interface CapsuleListItem {
    id: string;
    name: string;
    version: string;
    status: string;
    capsule_type: string;
    tenant_id: string;
    install_count: number;
    execution_count: number;
    created_at: string;
}

export interface AuditLogItem {
    id: string;
    actor: string;
    action: string;
    resource_type: string;
    resource_id: string;
    outcome: string;
    details: Record<string, unknown>;
    ip_address: string | null;
    created_at: string;
}

export interface TenantInfo {
    tenant_id: string;
    realm: string;
    job_count: number;
    source_count: number;
    artifact_count: number;
    last_activity: string | null;
}
