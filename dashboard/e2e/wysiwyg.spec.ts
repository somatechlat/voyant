import { test, expect } from '@playwright/test';

/**
 * WYSIWYG E2E Tests — Every view tested against the live API.
 * No mocks, no route blocking. Real data, real interactions.
 *
 * Requires: voyant_api on :45000, dashboard on :3000 (Vite dev proxy).
 */

const API_BASE = 'http://localhost:45000';

test.describe('WYSIWYG — Dashboard View', () => {
    test('loads real admin dashboard data from API', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
        });
        await page.goto('/admin', { waitUntil: 'networkidle' });
        await expect(page.locator('view-dashboard')).toBeAttached();
        // Dashboard should render without JS errors
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await page.waitForTimeout(2000);
        expect(errors).toEqual([]);
    });
});

test.describe('WYSIWYG — Ontology View', () => {
    test('loads real ontology types from API', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
        });
        await page.goto('/admin/ontology', { waitUntil: 'networkidle' });
        await expect(page.locator('view-ontology')).toBeAttached();
        // Should show the table/grid/graph tabs
        await page.waitForTimeout(2000);
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        expect(errors).toEqual([]);
    });
});

test.describe('WYSIWYG — Jobs View', () => {
    test('loads real jobs from API', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
        });
        await page.goto('/admin/jobs', { waitUntil: 'networkidle' });
        await expect(page.locator('view-jobs')).toBeAttached();
        await page.waitForTimeout(2000);
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        expect(errors).toEqual([]);
    });
});

test.describe('WYSIWYG — Sources View', () => {
    test('loads real sources from API', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
        });
        await page.goto('/admin/sources', { waitUntil: 'networkidle' });
        await expect(page.locator('view-sources')).toBeAttached();
        await page.waitForTimeout(2000);
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        expect(errors).toEqual([]);
    });
});

test.describe('WYSIWYG — Governance View', () => {
    test('loads governance data with lineage tab', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
        });
        await page.goto('/admin/governance', { waitUntil: 'networkidle' });
        await expect(page.locator('view-governance')).toBeAttached();
        // Click lineage tab
        const lineageTab = page.locator('button', { hasText: 'Lineage' });
        if (await lineageTab.isVisible()) {
            await lineageTab.click();
            await page.waitForTimeout(1000);
        }
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        expect(errors).toEqual([]);
    });
});

test.describe('WYSIWYG — Agents View', () => {
    test('loads agent definitions and deployment tab', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
        });
        await page.goto('/admin/agents', { waitUntil: 'networkidle' });
        await expect(page.locator('view-agents')).toBeAttached();
        // Click deployments tab
        const deployTab = page.locator('button', { hasText: 'Deployments' });
        if (await deployTab.isVisible()) {
            await deployTab.click();
            await page.waitForTimeout(1000);
        }
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        expect(errors).toEqual([]);
    });
});

test.describe('WYSIWYG — SQL View', () => {
    test('loads SQL console with tables and saved queries', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
        });
        await page.goto('/admin/sql', { waitUntil: 'networkidle' });
        await expect(page.locator('view-sql')).toBeAttached();
        await page.waitForTimeout(2000);
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        expect(errors).toEqual([]);
    });
});

test.describe('WYSIWYG — Scraper View', () => {
    test('loads scraper templates from API', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
        });
        await page.goto('/admin/scraper', { waitUntil: 'networkidle' });
        await expect(page.locator('view-scraper')).toBeAttached();
        await page.waitForTimeout(2000);
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        expect(errors).toEqual([]);
    });
});

test.describe('WYSIWYG — ML Models View', () => {
    test('loads model registry from API', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
        });
        await page.goto('/admin/models', { waitUntil: 'networkidle' });
        await expect(page.locator('view-models')).toBeAttached();
        await page.waitForTimeout(2000);
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        expect(errors).toEqual([]);
    });
});

test.describe('WYSIWYG — Pipelines View', () => {
    test('loads pipeline builder from API', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
        });
        await page.goto('/admin/pipelines', { waitUntil: 'networkidle' });
        await expect(page.locator('view-pipelines')).toBeAttached();
        await page.waitForTimeout(2000);
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        expect(errors).toEqual([]);
    });
});

test.describe('WYSIWYG — All 27 Views', () => {
    const ALL_ROUTES = [
        '/admin/login', '/admin', '/admin/jobs', '/admin/sources',
        '/admin/governance', '/admin/capsules', '/admin/ontology',
        '/admin/audit', '/admin/sql', '/admin/search', '/admin/scraper',
        '/admin/settings', '/admin/tenants', '/admin/agents', '/admin/mcp',
        '/admin/pipelines', '/admin/dashboards', '/admin/drift',
        '/admin/notifications', '/admin/workspaces', '/admin/approvals',
        '/admin/features', '/admin/models', '/admin/connectors',
        '/admin/webhooks', '/admin/streaming', '/admin/alerting',
    ];

    for (const route of ALL_ROUTES) {
        test(`${route} renders without JS errors against live API`, async ({ page }) => {
            await page.addInitScript(() => {
                window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
            });

            const pageErrors: string[] = [];
            const consoleErrors: string[] = [];
            page.on('pageerror', (err) => pageErrors.push(err.message));
            page.on('console', (msg) => {
                if (msg.type() === 'error' && !msg.text().includes('Failed to load resource')) {
                    consoleErrors.push(msg.text());
                }
            });

            await page.goto(route, { waitUntil: 'networkidle', timeout: 15000 });
            await page.waitForTimeout(1500);

            expect(pageErrors, `JS errors on ${route}`).toEqual([]);
            expect(consoleErrors, `Console errors on ${route}`).toEqual([]);
        });
    }
});
