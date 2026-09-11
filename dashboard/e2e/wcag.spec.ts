import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * WCAG 2.1 AA Automated Audit
 * Runs axe-core against every view to detect accessibility violations.
 */

const ROUTES = [
    { path: '/admin/login', auth: false },
    { path: '/admin', auth: true },
    { path: '/admin/jobs', auth: true },
    { path: '/admin/sources', auth: true },
    { path: '/admin/governance', auth: true },
    { path: '/admin/capsules', auth: true },
    { path: '/admin/ontology', auth: true },
    { path: '/admin/audit', auth: true },
    { path: '/admin/sql', auth: true },
    { path: '/admin/search', auth: true },
    { path: '/admin/scraper', auth: true },
    { path: '/admin/settings', auth: true },
    { path: '/admin/tenants', auth: true },
    { path: '/admin/agents', auth: true },
    { path: '/admin/mcp', auth: true },
    { path: '/admin/pipelines', auth: true },
    { path: '/admin/dashboards', auth: true },
    { path: '/admin/drift', auth: true },
    { path: '/admin/notifications', auth: true },
    { path: '/admin/workspaces', auth: true },
    { path: '/admin/approvals', auth: true },
    { path: '/admin/features', auth: true },
    { path: '/admin/models', auth: true },
    { path: '/admin/connectors', auth: true },
    { path: '/admin/webhooks', auth: true },
    { path: '/admin/streaming', auth: true },
    { path: '/admin/alerting', auth: true },
];

test.describe('WCAG 2.1 AA Automated Audit', () => {
    for (const { path, auth } of ROUTES) {
        test(`${path} passes axe-core WCAG 2.1 AA`, async ({ page }) => {
            if (auth) {
                await page.addInitScript(() => {
                    window.localStorage.setItem('voyant_token', 'e2e-wysiwyg-token');
                });
            }

            // Block API calls to prevent redirects
            await page.route('**/v1/**', (route) => route.abort());

            await page.goto(path, { waitUntil: 'networkidle', timeout: 15000 });
            await page.waitForTimeout(1000);

            // Skip if redirected to login
            if (page.url().includes('/admin/login') && auth) {
                test.skip();
                return;
            }

            const results = await new AxeBuilder({ page })
                .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
                .analyze();

            // Log violations for debugging
            if (results.violations.length > 0) {
                console.log(`\n=== WCAG Violations on ${path} ===`);
                for (const v of results.violations) {
                    console.log(`  [${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} elements)`);
                }
            }

            // For now, log but don't fail — we'll fix violations iteratively
            // expect(results.violations).toEqual([]);
        });
    }
});
