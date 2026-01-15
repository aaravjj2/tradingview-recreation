import { test, expect } from '@playwright/test';

test('AIPanel shows WebSocket Status connected', async ({ page }) => {
    // Go to app root
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Navigate to Dashboard where AIPanel is rendered
    await page.getByTestId('nav-item-dashboard').click();
    await page.waitForTimeout(500);

    // Ensure the AIPanel is visible
    const aiPanel = page.getByTestId('ai-panel');
    await expect(aiPanel).toBeVisible({ timeout: 10000 });

    // Click Alerts tab inside the Autopilot view
    await page.getByText('Alerts').click();
    await page.waitForTimeout(500);

    // Verify the WebSocket Status label is present
    await expect(aiPanel.getByText('WebSocket Status')).toBeVisible();

    // Verify the status text becomes 'connected' (case-insensitive)
    await expect(page.locator('text=/connected/i')).toBeVisible({ timeout: 5000 });

    // Take a screenshot for manual verification
    await page.screenshot({ path: 'test-results/snapshots/websocket-status-connected.png', fullPage: false });
});