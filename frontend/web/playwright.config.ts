import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: 0,
  use: { baseURL: 'http://127.0.0.1:4173', viewport: { width: 375, height: 812 },
    trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
  webServer: { command: 'python3 e2e/server.py', url: 'http://127.0.0.1:4173/labs/interactive/',
    reuseExistingServer: false },
});
