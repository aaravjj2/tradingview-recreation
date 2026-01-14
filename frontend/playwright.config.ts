import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5100';

export default defineConfig({
    testDir: './tests/e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: [
        ['list'],
        ['html', { open: 'never' }],
    ],
    use: {
        baseURL,
        trace: 'on-first-retry',
        screenshot: 'on',  // Always take screenshots
        video: 'on',  // Record video for all tests
        chromiumSandbox: false,
        headless: false,  // NON-HEADLESS mode for visual verification
        launchOptions: {
            args: [
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ],
            slowMo: 100,  // Slow down for visual inspection
        },
    },
    webServer: {
        command: 'npm run dev',
        url: 'http://localhost:5100',
        reuseExistingServer: !process.env.CI,
        timeout: 60000,
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
    // Snapshot settings
    snapshotDir: './tests/e2e/__snapshots__',
    expect: {
        toHaveScreenshot: {
            maxDiffPixelRatio: 0.05,
        },
    },
    // Timeout settings
    timeout: 30000,
});
