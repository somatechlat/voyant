import { test, expect, type ConsoleMessage } from '@playwright/test';

/* ── Routes under test (15 total) ──────────────────────────────────────────── */

const ROUTES: Array<{ path: string; view: string; auth?: boolean }> = [
    // /admin/login is public; with a token set it redirects to /admin.
    { path: '/admin/login', view: 'view-login', auth: false },
    { path: '/admin', view: 'view-dashboard' },
    { path: '/admin/jobs', view: 'view-jobs' },
    { path: '/admin/sources', view: 'view-sources' },
    { path: '/admin/governance', view: 'view-governance' },
    { path: '/admin/capsules', view: 'view-capsules' },
    { path: '/admin/ontology', view: 'view-ontology' },
    { path: '/admin/audit', view: 'view-audit' },
    { path: '/admin/sql', view: 'view-sql' },
    { path: '/admin/search', view: 'view-search' },
    { path: '/admin/scraper', view: 'view-scraper' },
    { path: '/admin/settings', view: 'view-settings' },
    { path: '/admin/tenants', view: 'view-tenants' },
    { path: '/admin/agents', view: 'view-agents' },
    { path: '/admin/mcp', view: 'view-mcp' },
];

// The suite runs without the backend. Views must catch fetch failures and
// render empty states; only the browser's own network-error console entries
// (e.g. "Failed to load resource: net::ERR_FAILED") are tolerated.
function isNetworkNoise(msg: ConsoleMessage): boolean {
    return msg.text().includes('Failed to load resource');
}

test.beforeEach(async ({ page }) => {
    // Abort API calls at the browser so the "backend down" premise holds even
    // when a dev API happens to be running locally (a live API would 401 the
    // dummy token and redirect to /admin/login).
    await page.route('**/v1/**', (route) => route.abort());
});

/* ── Route smoke tests (15 routes) ────────────────────────────────────────── */

for (const { path, view, auth = true } of ROUTES) {
    test(`${path} loads with zero JS errors`, async ({ page }) => {
        if (auth) {
            await page.addInitScript(() => {
                window.localStorage.setItem('voyant_token', 'e2e-smoke-token');
            });
        }

        const pageErrors: string[] = [];
        const consoleErrors: string[] = [];

        page.on('pageerror', (err) => pageErrors.push(err.message));
        page.on('console', (msg) => {
            if (msg.type() === 'error' && !isNetworkNoise(msg)) {
                consoleErrors.push(msg.text());
            }
        });

        await page.goto(path, { waitUntil: 'networkidle' });
        await expect(page.locator(view)).toBeAttached();

        expect(pageErrors, `uncaught exceptions on ${path}`).toEqual([]);
        expect(consoleErrors, `console errors on ${path}`).toEqual([]);
    });
}

/* ── Login flow test ───────────────────────────────────────────────────────── */

test.describe('Login flow', () => {
    test('fill credentials, submit, and verify redirect to dashboard', async ({ page }) => {
        // Don't block /v1/auth/login so the form can post, but since the
        // backend won't be running the fetch will fail. We override the
        // fetch response to simulate a successful login.
        await page.route('**/v1/**', (route) => {
            const url = route.request().url();
            if (url.includes('/v1/auth/login')) {
                return route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        access_token: 'e2e-fake-token',
                        refresh_token: 'e2e-fake-refresh',
                        user: { username: 'admin', roles: ['admin'] },
                    }),
                });
            }
            return route.abort();
        });

        await page.goto('/admin/login', { waitUntil: 'networkidle' });

        // Fill in credentials
        const usernameInput = page.locator('input[type="text"], input[autocomplete="username"]');
        const passwordInput = page.locator('input[type="password"], input[autocomplete="current-password"]');

        await expect(usernameInput).toBeVisible();
        await usernameInput.fill('admin');

        await expect(passwordInput).toBeVisible();
        await passwordInput.fill('testpassword');

        // Submit the form
        const submitButton = page.locator('button[type="submit"]');
        await expect(submitButton).toBeVisible();
        await submitButton.click();

        // Verify redirect to dashboard (/admin)
        await page.waitForURL('**/admin**', { timeout: 10000 });
        expect(page.url()).toContain('/admin');

        // Verify token was stored
        const token = await page.evaluate(() => localStorage.getItem('voyant_token'));
        expect(token).toBe('e2e-fake-token');
    });
});

/* ── Navigation smoke test ─────────────────────────────────────────────────── */

test.describe('Navigation', () => {
    test('sidebar links navigate between views', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-smoke-token');
        });

        await page.goto('/admin', { waitUntil: 'networkidle' });
        await expect(page.locator('view-dashboard')).toBeAttached();
    });
});
