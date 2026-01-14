
import { test, expect } from '@playwright/test';

test.describe('Forecast Tile Verification', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');

        // Navigate to Dashboard
        const dashboardNav = page.locator('[data-testid="nav-item-dashboard"]');
        await expect(dashboardNav).toBeVisible({ timeout: 5000 });
        await dashboardNav.click();
        await page.waitForTimeout(1000);
    });

    test('Forecast tile can be added and displays data', async ({ page }) => {
        // 1. Open Add Tile Dialog
        const addTileBtn = page.getByRole('button', { name: /Add.*Tile/i }).first();
        await expect(addTileBtn).toBeVisible({ timeout: 10000 });
        await addTileBtn.click();

        // 2. Select Forecast/Uncertainty Cone tile
        const forecastOption = page.getByRole('button', { name: /Uncertainty Cone/i });
        await expect(forecastOption).toBeVisible();
        await forecastOption.click();

        // 3. Verify tile appears
        const tileHeader = page.locator('span').filter({ hasText: 'Uncertainty Cone' });
        await expect(tileHeader).toBeVisible();

        // 4. Verify chart rendering (canvas exists)
        const canvas = page.locator('canvas').last(); // Might be multiple canvases, get the last added
        await expect(canvas).toBeVisible();

        // 5. Verify data stats are present (e.g., "Current Price", "Forecast Days")
        await expect(page.getByText('Current Price')).toBeVisible();
        await expect(page.getByText('Forecast Days')).toBeVisible();
        await expect(page.getByText('Hist. Volatility')).toBeVisible();

        // 6. Screenshot
        await page.waitForTimeout(1000); // Allow canvas animation to complete
        await page.screenshot({ path: 'screenshots/forecast-tile.png' });
    });
});
