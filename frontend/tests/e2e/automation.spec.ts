/**
 * E2E Tests for Automation (Autopilot) View
 */

import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';

test.describe('Automation View', () => {
    test.beforeEach(async ({ page, request }) => {
        // Reset automation state before each test
        await request.post(`${API_BASE}/automation/reset`);
        await request.post(`${API_BASE}/automation/disarm`);

        await page.goto('/');
        // Navigate to Automation view via left nav item
        await page.getByRole('button', { name: /automation/i }).click();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500); // Wait for component to fetch status
    });

    test('Automation view loads with correct initial state', async ({ page }) => {
        // Check header is visible
        await expect(page.locator('h1:has-text("Automation")')).toBeVisible();

        // Check DISARMED badge is visible (default state)
        await expect(page.locator('text=DISARMED')).toBeVisible();

        // Take screenshot
        await page.screenshot({ path: 'screenshots/automation-initial.png' });
    });

    test('Paper trading can be started and stopped', async ({ page }) => {
        // Click Start Paper Trading button
        const startButton = page.locator('button:has-text("Start Paper Trading")');
        await expect(startButton).toBeVisible();
        await startButton.click();

        // Wait for status to update
        await page.waitForTimeout(1000);

        // Should now show PAPER ARMED
        await expect(page.locator('text=PAPER ARMED')).toBeVisible();

        // Verify Active Strategy is displayed
        await expect(page.getByText('Active Strategy: Simple-MA-v1')).toBeVisible();

        // Take screenshot of armed state
        await page.screenshot({ path: 'screenshots/automation-paper-armed.png' });

        // Stop button should now say "Stop Paper Trading"
        const stopButton = page.locator('button:has-text("Stop Paper Trading")');
        await expect(stopButton).toBeVisible();
        await stopButton.click();

        // Wait for status to update
        await page.waitForTimeout(1000);

        // Should show DISARMED again
        await expect(page.locator('text=DISARMED')).toBeVisible();
    });

    test('Live trading requires two-step confirmation', async ({ page }) => {
        // First click should show confirmation prompt
        const armLiveButton = page.locator('button:has-text("Arm Live Trading")');
        await expect(armLiveButton).toBeVisible();
        await expect(armLiveButton).toBeEnabled();
        await armLiveButton.click();

        // Wait for UI update to "CONFIRM LIVE TRADING"
        // The text changes on the SAME button.
        await expect(page.locator('button:has-text("CONFIRM LIVE TRADING")')).toBeVisible({ timeout: 5000 });

        // Take screenshot of confirmation state
        await page.screenshot({ path: 'screenshots/automation-live-confirm.png' });
    });

    test('Kill switch disables automation', async ({ page }) => {
        // First, arm paper trading
        await page.click('button:has-text("Start Paper Trading")');
        await page.waitForTimeout(1000);

        // Verify armed
        await expect(page.locator('text=PAPER ARMED')).toBeVisible();

        // Click kill switch
        await page.click('button:has-text("Kill All Automation")');
        await page.waitForTimeout(1000);

        // Should show kill switch warning
        await expect(page.locator('text=Kill Switch Triggered')).toBeVisible();

        // Take screenshot
        await page.screenshot({ path: 'screenshots/automation-kill-switch.png' });
    });

    test('Budget controls are displayed', async ({ page }) => {
        // Check budget controls section exists
        await expect(page.locator('text=Budget & Risk Controls')).toBeVisible();

        // Check for budget input fields
        await expect(page.locator('text=Max Total Notional')).toBeVisible();
        await expect(page.locator('text=Max Daily Spend')).toBeVisible();
        await expect(page.locator('text=Max Per Trade')).toBeVisible();

        // Take full screenshot
        await page.screenshot({ path: 'screenshots/automation-budget.png', fullPage: true });
    });
});
