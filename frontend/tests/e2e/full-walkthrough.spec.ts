import { test, expect } from '@playwright/test';

test.describe('Full System Walkthrough', () => {
    test('navigate through all major features', async ({ page }) => {
        // 1. Dashboard / Home
        await page.goto('http://localhost:5173');
        await expect(page).toHaveTitle(/TradingView/);
        await page.waitForLoadState('networkidle');

        // 2. Options Analytics
        // Navigate using sidebar
        const optionsNavItem = page.getByRole('link', { name: 'Options' }).first();
        if (await optionsNavItem.isVisible()) {
            await optionsNavItem.click();
        } else {
            // Try getting by href if role is tricky or icon-based
            await page.locator('a[href="/options"]').click();
        }

        await expect(page.getByText('Options Analytics')).toBeVisible();
        await expect(page.getByText('Options Chain')).toBeVisible();

        // Interact with Options Chain (select an expiration if multiple exist, or just verify data)
        // Wait for chain data to load
        await page.waitForTimeout(1000);
        await expect(page.locator('.text-brand').first()).toBeVisible(); // Check for some highlighted text or price

        // Switch to Strategy Builder
        await page.getByRole('tab', { name: 'Strategy Builder' }).click();
        await expect(page.getByText('Payoff Diagram')).toBeVisible();

        // Select a Strategy Template (e.g. Long Call) to populate chart
        await page.getByRole('button', { name: 'Long Call' }).click();
        await page.waitForTimeout(500); // Visual pause

        // 3. Automation & Forecast
        await page.locator('a[href="/automation"]').click();
        await expect(page.getByText('Forecast Intelligence')).toBeVisible();

        // Verify Forecast Panel (Visual Chart)
        await expect(page.locator('canvas')).toBeVisible(); // ChartJS canvas
        await expect(page.getByText('Current Forecast')).toBeVisible();

        // Verify Market Closed Logic (since we know it is closed)
        if (await page.getByText('Market is currently closed').isVisible()) {
            await expect(page.getByRole('button', { name: 'Market Closed' })).toBeDisabled();
        } else {
            // If this runs during day, check enabled state
            // await expect(page.getByRole('button', { name: 'Arm Live Trading' })).toBeEnabled();
        }

        // Toggle some configs to show interactivity
        await page.getByText('Confidence').click();
        await page.waitForTimeout(500);
        await page.getByText('Filter Trades').click();
        await page.waitForTimeout(1000); // Allow video to capture state
    });
});
