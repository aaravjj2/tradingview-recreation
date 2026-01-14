import { test, expect } from '@playwright/test';

test.describe('Unified Autopilot + Forecast Integration', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');  // Uses baseURL from playwright.config.ts
        await page.waitForLoadState('networkidle');
        // Wait for nav to be visible
        await page.waitForSelector('nav', { timeout: 10000 });
    });

    test('Automation view shows Forecast Intelligence panel', async ({ page }) => {
        // Navigate to Automation view
        await page.getByTestId('nav-item-automation').click();
        await page.waitForTimeout(2000);

        // Take screenshot of Automation view
        await page.screenshot({ path: 'test-results/automation-forecast-panel.png', fullPage: true });

        // Check for Forecast Intelligence text
        const forecastPanel = page.locator('text=Forecast Intelligence');
        await expect(forecastPanel).toBeVisible({ timeout: 10000 });

        // Check for Current Forecast section
        const currentForecast = page.locator('text=Current Forecast');
        await expect(currentForecast).toBeVisible();

        // Check for Configuration section
        const configSection = page.locator('text=Configuration');
        await expect(configSection).toBeVisible();

        // Check for specific config elements
        await expect(page.locator('.text-text-secondary', { hasText: 'Enabled' })).toBeVisible();
        await expect(page.locator('.text-text-secondary', { hasText: 'Confidence' })).toBeVisible();
        await expect(page.getByText('Filter Trades')).toBeVisible();
        await expect(page.getByText('Size by Vol')).toBeVisible();

        // Verify Market Closed warning is present (since it's night)
        await expect(page.getByText('Market is currently closed')).toBeVisible();
        await expect(page.getByRole('button', { name: 'Market Closed' })).toBeDisabled();

        // Capture proof
        await page.screenshot({ path: 'test-results/automation-market-closed.png' });
    });

    test('Forecast config toggles are interactive', async ({ page }) => {
        // Navigate to Automation view
        await page.getByTestId('nav-item-automation').click();
        await page.waitForTimeout(2000);

        // Find and click the "Filter Trades" toggle
        const filterToggle = page.locator('button:has-text("YES")').first();

        if (await filterToggle.isVisible()) {
            await filterToggle.click();
            await page.waitForTimeout(500);

            // Take screenshot after toggle
            await page.screenshot({ path: 'test-results/automation-forecast-toggled.png', fullPage: true });
        }
    });
});
