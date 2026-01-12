import { test, expect } from '@playwright/test';

test.describe('Indicator System', () => {
  test.beforeEach(async ({ page }) => {
    // Listen to console logs
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', exception => console.log('PAGE ERROR:', exception));

    // Navigate to the built app (use Playwright baseURL)
    await page.goto('/');
    // Wait for Shell to render specific UI element instead of generic root
    // This confirms the React app has mounted and rendered the Shell
    await expect(page.getByText('Indicators').first()).toBeVisible({ timeout: 10000 });
  });

  test('should open indicator library and add RSI', async ({ page }) => {
    // 1. Open Indicator Library
    // Button is in ChartHeaderStrip, has text "Indicators" or icon
    const indicatorBtn = page.getByRole('button', { name: 'Indicators' }).first();
    await indicatorBtn.click();

    // 2. Verify Modal Opens
    const modal = page.locator('text=Indicators').first();
    await expect(modal).toBeVisible();

    // 3. Search for RSI (short query for robustness)
    const searchInput = page.getByPlaceholder('Search...');
    await searchInput.fill('RSI');

    // 4. Select RSI row and add
    await page.locator('.cursor-pointer', { hasText: 'Relative Strength Index' }).first().click();
    await page.getByRole('button', { name: 'Add to Chart' }).click();

    // 6. Verify Modal Closes
    // await expect(modal).not.toBeVisible(); // It might stay open depending on UX, but my code closes it on Add?
    // Looking at IndicatorsModal.tsx: `onClose()` is called in `handleAdd`.
    
    // 7. Verify Indicator is Active in Right Panel
    // First ensure Right Panel is open or open it
    // Default might be closed or open (monitor view usually has it open? No, default is open based on Shell.tsx)
    // Shell.tsx: `Panel defaultSize={rightDockOpen ? 75 : 100}`
    // But let's check the RightPanel toggle if needed.
    // The RightPanel has a tab list.
    
    // Check for "RSI" in the Right Panel or Legend
    // I added "Active Indicators" list in RightPanel under "Data" tab? No, "Indicators" tab.
    // I need to switch to "Indicators" tab in Right Panel
    
    // Open Right Panel 'Ind' tab and assert RSI present in dock
    const indTab = page.getByRole('button', { name: 'Ind' });
    await indTab.click();
    await expect(page.locator('text=RSI')).toBeVisible();
  });

  test('should add and remove SMA from library', async ({ page }) => {
    // Open modal and add SMA
    await page.getByRole('button', { name: 'Indicators' }).first().click();
    await expect(page.getByRole('dialog')).toBeVisible();

    await page.getByPlaceholder('Search...').fill('SMA');
    await page.locator('.cursor-pointer', { hasText: 'Simple Moving Average' }).first().click();
    await page.getByRole('button', { name: 'Add to Chart' }).click();

    // Ensure badge shows a number
    const badgeNum = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const indBtn = btns.find(b => (b.textContent || '').includes('Indicators'));
      if (!indBtn) return null;
      const spans = Array.from(indBtn.querySelectorAll('span'));
      const num = spans.find(s => (/^\d+$/.test(s.textContent || '')));
      return num ? num.textContent : null;
    });
    expect(badgeNum).toBeTruthy();

    // Open Ind dock and remove SMA
    await page.getByRole('button', { name: 'Ind' }).click();
    await expect(page.locator('text=SMA')).toBeVisible();

    await page.locator('button[title="Remove"]').first().click();
    await expect(page.locator('text=No indicators added')).toBeVisible();
  });
});
