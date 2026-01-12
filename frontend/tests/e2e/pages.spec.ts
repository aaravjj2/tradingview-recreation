import { test, expect } from '@playwright/test';

test.describe('Page Navigation and Rendering', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('index.html');
        await page.waitForLoadState('networkidle');
    });

    test('Monitor page renders chart', async ({ page }) => {
        // Navigate to Monitor if not already there
        const monitorNav = page.locator('button, a').filter({ hasText: 'Monitor' }).first();
        if (await monitorNav.isVisible({ timeout: 2000 }).catch(() => false)) {
            await monitorNav.click();
        }

        // Chart canvas should be present
        const chartCanvas = page.locator('canvas').first();
        await expect(chartCanvas).toBeVisible({ timeout: 5000 });

        await expect(page).toHaveScreenshot('page-monitor.png', { animations: 'disabled' });
    });

    test('Replay page renders controls', async ({ page }) => {
        const replayNav = page.locator('button, a').filter({ hasText: 'Replay' }).first();
        if (await replayNav.isVisible({ timeout: 2000 }).catch(() => false)) {
            await replayNav.click();
            await page.waitForTimeout(300);

            // Replay badge should be visible
            const replayBadge = page.locator('text=/REPLAY/i').first();
            await expect(replayBadge).toBeVisible({ timeout: 3000 });

            await expect(page).toHaveScreenshot('page-replay.png', { animations: 'disabled' });
        }
    });

    test('Strategies page renders list', async ({ page }) => {
        const strategiesNav = page.locator('button, a').filter({ hasText: 'Strategies' }).first();
        if (await strategiesNav.isVisible({ timeout: 2000 }).catch(() => false)) {
            await strategiesNav.click();
            await page.waitForTimeout(300);

            // Strategies heading or list should be visible
            const strategiesContent = page.locator('text=/Strategies|Strategy/i').first();
            await expect(strategiesContent).toBeVisible({ timeout: 3000 });

            await expect(page).toHaveScreenshot('page-strategies.png', { animations: 'disabled' });
        }
    });

    test('Alerts page renders', async ({ page }) => {
        const alertsNav = page.locator('button, a').filter({ hasText: 'Alerts' }).first();
        if (await alertsNav.isVisible({ timeout: 2000 }).catch(() => false)) {
            await alertsNav.click();
            await page.waitForTimeout(300);

            const alertsContent = page.locator('text=/Alerts|Alert/i').first();
            await expect(alertsContent).toBeVisible({ timeout: 3000 });

            await expect(page).toHaveScreenshot('page-alerts.png', { animations: 'disabled' });
        }
    });

    test('Portfolio page renders positions', async ({ page }) => {
        const portfolioNav = page.locator('button, a').filter({ hasText: 'Portfolio' }).first();
        if (await portfolioNav.isVisible({ timeout: 2000 }).catch(() => false)) {
            await portfolioNav.click();
            await page.waitForTimeout(300);

            // Portfolio should show value or positions
            const portfolioContent = page.locator('text=/Portfolio|Positions|Value/i').first();
            await expect(portfolioContent).toBeVisible({ timeout: 3000 });

            await expect(page).toHaveScreenshot('page-portfolio.png', { animations: 'disabled' });
        }
    });

    test('Reports page renders', async ({ page }) => {
        const reportsNav = page.locator('button, a').filter({ hasText: 'Reports' }).first();
        if (await reportsNav.isVisible({ timeout: 2000 }).catch(() => false)) {
            await reportsNav.click();
            await page.waitForTimeout(300);

            const reportsContent = page.locator('text=/Reports|Report|Generate/i').first();
            await expect(reportsContent).toBeVisible({ timeout: 3000 });

            await expect(page).toHaveScreenshot('page-reports.png', { animations: 'disabled' });
        }
    });

    test('Settings page renders API keys section', async ({ page }) => {
        const settingsNav = page.locator('button, a').filter({ hasText: 'Settings' }).first();
        if (await settingsNav.isVisible({ timeout: 2000 }).catch(() => false)) {
            await settingsNav.click();
            await page.waitForTimeout(300);

            const settingsContent = page.locator('text=/Settings|API|Keys/i').first();
            await expect(settingsContent).toBeVisible({ timeout: 3000 });

            await expect(page).toHaveScreenshot('page-settings.png', { animations: 'disabled' });
        }
    });
});
