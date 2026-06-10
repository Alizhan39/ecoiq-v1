import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

// EcoIQ Visual Intelligence — build configuration.
//
// BUILD-TIME ONLY. This config compiles the React island bundle and writes it
// straight into the Django static tree (../../static/dist). The committed output
// is served by WhiteNoise; Render never runs Node. Django's
// ManifestStaticFilesStorage adds the cache-busting hash at collectstatic time,
// so we emit STABLE, unhashed filenames here (ecoiq-islands.js / .css) that
// templates can reference with {% static 'dist/ecoiq-islands.js' %}.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: resolve(__dirname, '../../static/dist'),
    emptyOutDir: true,
    manifest: false,
    sourcemap: false,
    target: 'es2019',
    rollupOptions: {
      input: resolve(__dirname, 'src/main.tsx'),
      output: {
        format: 'es',
        entryFileNames: 'ecoiq-islands.js',
        chunkFileNames: 'ecoiq-islands-[name].js',
        assetFileNames: 'ecoiq-islands.[ext]',
      },
    },
  },
})
