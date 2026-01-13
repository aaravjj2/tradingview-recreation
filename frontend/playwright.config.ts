import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4173';

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
        screenshot: 'only-on-failure',
        chromiumSandbox: false,
        launchOptions: {
            args: [
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ],
        },
    },
    webServer: {
        command: 'npm run preview',
        url: 'http://localhost:4173',
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
