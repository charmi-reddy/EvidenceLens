import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 100_000,
  expect: { timeout: 12_000 },
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    browserName: 'chromium',
    headless: true,
    viewport: { width: 1365, height: 950 },
  },
});
