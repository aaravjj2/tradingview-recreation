import { test, expect } from '@playwright/test';

const SYMBOLS = ['AAPL', 'TSLA', 'MSFT'];

test('options provider is live (not mock) for key symbols', async ({ request }) => {
  for (const sym of SYMBOLS) {
    const res = await request.get(`http://localhost:8000/api/v1/options/chain/${sym}`);
    expect(res.ok(), `HTTP 200 for ${sym}`).toBeTruthy();

    const data = await res.json();

    // Provider should not be the mock adapter
    expect(data.provider, `provider for ${sym}`).not.toBe('mock');

    // Data should be available when using live providers
    expect(data.unavailable, `unavailable flag for ${sym}`).toBeNull();
    expect(data.total_contracts, `total_contracts for ${sym}`).toBeGreaterThan(0);
  }
});
