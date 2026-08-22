import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

/**
 * The build writes into the Django static tree.
 *
 * `static/spa/` — not `frontend/web/dist/` — because Django is the only thing
 * that serves this app in production. WhiteNoise already collects, compresses
 * and cache-headers everything under `static/`, so the SPA gets that machinery
 * for free instead of needing a second static host.
 *
 * The artefact is COMMITTED, deliberately. Render's build environment runs
 * Python only, and the repo's two existing Node layers (frontend/app islands,
 * frontend/remotion) are already build-time-only by design — Node is never a
 * runtime dependency. CI rebuilds and diffs the committed output, so a stale
 * artefact fails the build rather than shipping silently.
 */
export default defineConfig({
  plugins: [react()],
  base: '/static/spa/',
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    // Django serves the API in development. Proxying keeps the browser on one
    // origin, so session cookies and CSRF behave exactly as they will in
    // production — where /api/* is the same origin as the app.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8731', changeOrigin: false },
    },
  },
  build: {
    outDir: '../../static/spa',
    emptyOutDir: true,
    // Off in production. Sourcemaps would double the committed artefact and
    // publish the unminified source of a build nobody debugs from the browser.
    sourcemap: false,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    css: false,
  },
});
