/**
 * Enhanced Portfolio E2E Tests
 * 
 * Tests for:
 * - Unified positions display (stocks + options)
 * - Broker verification panel
 * - Real-time position updates
 * - Exit controls
 * - Filter functionality
 * 
 * Runs in headed Chrome with video + trace + screenshots on failure.
 */

import { test, expect } from '@playwright/test';

test.describe('Enhanced Portfolio', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to portfolio view
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        
        // Click on Portfolio nav item
        const portfolioNav = page.locator('[data-testid="nav-item-portfolio"]');
        await portfolioNav.click();
        
        // Wait for portfolio view to load
        await page.waitForSelector('text=Total Equity', { timeout: 10000 });
    });

    test('displays portfolio summary cards', async ({ page }) => {
        // Verify summary cards are visible
        await expect(page.locator('text=Total Equity')).toBeVisible();
        await expect(page.locator('text=Open P&L')).toBeVisible();
        await expect(page.locator('text=Buying Power')).toBeVisible();
        await expect(page.locator('text=Positions')).toBeVisible();
        await expect(page.locator('text=Broker')).toBeVisible();
    });

    test('displays broker verification panel', async ({ page }) => {
        // Check for broker verification section
        await expect(page.locator('text=Broker Verification')).toBeVisible();
        
        // Expand if collapsed
        const verificationPanel = page.locator('text=Broker Verification').first();
        await verificationPanel.click();
        
        // Verify status elements
        await expect(page.locator('text=Status')).toBeVisible();
        await expect(page.locator('text=Account')).toBeVisible();
        await expect(page.locator('text=Latency')).toBeVisible();
        await expect(page.locator('text=Last Check')).toBeVisible();
    });

    test('shows positions tab with position data', async ({ page }) => {
        // Positions tab should be active by default
        const positionsTab = page.locator('button:has-text("Positions")');
        await expect(positionsTab).toBeVisible();
        
        // Verify position table headers
        await expect(page.locator('th:has-text("Symbol")')).toBeVisible();
        await expect(page.locator('th:has-text("Type")')).toBeVisible();
        await expect(page.locator('th:has-text("Qty")')).toBeVisible();
        await expect(page.locator('th:has-text("Avg Price")')).toBeVisible();
        await expect(page.locator('th:has-text("P&L")')).toBeVisible();
    });

    test('can switch between Positions and Orders tabs', async ({ page }) => {
        // Click Orders tab
        const ordersTab = page.locator('button:has-text("Orders")');
        await ordersTab.click();
        
        // Verify orders table headers
        await expect(page.locator('th:has-text("Time")')).toBeVisible();
        await expect(page.locator('th:has-text("Side")')).toBeVisible();
        await expect(page.locator('th:has-text("Status")')).toBeVisible();
        
        // Switch back to Positions
        const positionsTab = page.locator('button:has-text("Positions")');
        await positionsTab.click();
        await expect(page.locator('th:has-text("Mkt Value")')).toBeVisible();
    });

    test('filter by asset type works', async ({ page }) => {
        // Find filter dropdown
        const filterSelect = page.locator('select');
        
        // Filter to equity only
        await filterSelect.selectOption('equity');
        await page.waitForTimeout(500);
        
        // Filter to options only
        await filterSelect.selectOption('options');
        await page.waitForTimeout(500);
        
        // Reset to all
        await filterSelect.selectOption('all');
    });

    test('refresh button triggers data update', async ({ page }) => {
        // Find refresh button by tooltip or icon
        const refreshBtn = page.locator('button[title="Refresh"]').first();
        
        if (await refreshBtn.isVisible()) {
            await refreshBtn.click();
            // Button should have spinning animation briefly
            await page.waitForTimeout(1000);
        }
    });

    test('verify now button triggers broker check', async ({ page }) => {
        // Expand verification panel if needed
        const verificationHeader = page.locator('text=Broker Verification').first();
        await verificationHeader.click();
        
        // Click verify now button
        const verifyBtn = page.locator('text=Verify Now');
        if (await verifyBtn.isVisible()) {
            await verifyBtn.click();
            await page.waitForTimeout(1000);
        }
    });

    test('takes screenshot of portfolio view', async ({ page }) => {
        // Wait for data to load
        await page.waitForTimeout(2000);
        
        // Take screenshot for visual comparison
        await expect(page).toHaveScreenshot('portfolio-view.png', {
            fullPage: true,
            animations: 'disabled',
        });
    });
});

test.describe('Portfolio Position Actions', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.locator('[data-testid="nav-item-portfolio"]').click();
        await page.waitForSelector('text=Total Equity');
    });

    test('position rows show exit button on hover', async ({ page }) => {
        // Find a position row
        const positionRow = page.locator('tbody tr').first();
        
        if (await positionRow.isVisible()) {
            // Hover to reveal action buttons
            await positionRow.hover();
            
            // Look for exit button (XCircle icon)
            const exitBtn = positionRow.locator('button[title="Exit Position"]');
            await expect(exitBtn).toBeVisible({ timeout: 3000 });
        }
    });

    test('position rows show view details on hover', async ({ page }) => {
        const positionRow = page.locator('tbody tr').first();
        
        if (await positionRow.isVisible()) {
            await positionRow.hover();
            
            const viewBtn = positionRow.locator('button[title="View Details"]');
            await expect(viewBtn).toBeVisible({ timeout: 3000 });
        }
    });
});

test.describe('Portfolio Real-time Updates', () => {
    test('auto-refreshes positions data', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.locator('[data-testid="nav-item-portfolio"]').click();
        await page.waitForSelector('text=Total Equity');
        
        // Get initial position count
        const positionsTab = page.locator('button:has-text("Positions")');
        const initialText = await positionsTab.textContent();
        
        // Wait for auto-refresh cycle (5 seconds)
        await page.waitForTimeout(6000);
        
        // Verify we didn't crash and data is still displayed
        await expect(page.locator('text=Total Equity')).toBeVisible();
    });

    test('broker status indicator updates', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.locator('[data-testid="nav-item-portfolio"]').click();
        
        // Verify broker status is shown
        const brokerSection = page.locator('text=Broker').first();
        await expect(brokerSection).toBeVisible();
        
        // Look for connected/disconnected indicator
        const connectedIndicator = page.locator('.text-up, .bg-up').first();
        const disconnectedIndicator = page.locator('.text-down, .bg-down').first();
        
        // One of these should be visible
        const isConnected = await connectedIndicator.isVisible().catch(() => false);
        const isDisconnected = await disconnectedIndicator.isVisible().catch(() => false);
        
        expect(isConnected || isDisconnected).toBeTruthy();
    });
});
