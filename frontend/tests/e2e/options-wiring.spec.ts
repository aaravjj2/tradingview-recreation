import { test, expect } from '@playwright/test';

test.describe('Options Wiring', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to root
        await page.goto('/');
        // Wait for app to load
        await expect(page.locator('nav')).toBeVisible({ timeout: 10000 });
    });

    test('Option Chain Tile displays data', async ({ page }) => {
        // Navigate to Dashboard via LeftNav
        await page.getByTestId('nav-item-dashboard').click();

        // Wait for dashboard or add tile button
        const addTileButton = page.getByRole('button', { name: /Add Tile/i });
        if (await addTileButton.isVisible()) {
            await addTileButton.click();
            await page.getByText('Option Chain', { exact: true }).click();
            await page.getByRole('button', { name: 'Add Option Chain' }).click();
        }

        // Wait for loading to disappear
        await expect(page.getByText('Loading options...')).not.toBeVisible({ timeout: 15000 });

        // Check for strike prices (should be numeric)
        const strikes = page.locator('.font-bold.tabular-nums');
        await expect(strikes.first()).toBeVisible({ timeout: 10000 });
        const strikeText = await strikes.first().innerText();
        expect(parseFloat(strikeText)).toBeGreaterThan(0);

        // Check for bid/ask values
        const bids = page.locator('.font-mono.text-green-500');
        await expect(bids.first()).toBeVisible();
        const bidText = await bids.first().innerText();
        expect(bidText).not.toBe('-');

        await page.screenshot({ path: 'frontend/screenshots/options-wire-check.png' });
    });

    test('Options Analytics View displays chain', async ({ page }) => {
        // Navigate to Options view via LeftNav
        await page.getByTestId('nav-item-options').click();
        await expect(page.getByText('Options Analytics', { exact: false })).toBeVisible({ timeout: 15000 });

        // Wait for chain to load
        await expect(page.getByText('Loading options chain...')).not.toBeVisible({ timeout: 15000 });

        // Verify some data rows
        const rows = page.locator('tbody tr');
        await expect(rows.first()).toBeVisible();

        // Take screenshot
        await page.screenshot({ path: 'frontend/screenshots/options-view-check.png' });
    });
});
