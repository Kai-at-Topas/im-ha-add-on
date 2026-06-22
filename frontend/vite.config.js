// Vite build configuration for the HA Energy Dashboard frontend.
//
// Dual entry points:
//   ingress  (index.html)     — full-page HA Ingress app, served by the
//                               backend's static mount at /
//   card     (entry-card.js)  — Lovelace custom card; same component tree,
//                               different mount target
//
// base: './' — all asset URLs are relative so the bundle works under HA's
// path-prefixed Ingress URL (e.g. /api/hassio_ingress/<slug>/) without
// needing to know the prefix at build time.
//
// Dev server proxy: /api → http://localhost:9150 so `npm run dev` talks
// to the local FastAPI backend without CORS issues.
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  base: './',
  server: {
    proxy: {
      '/api': 'http://localhost:9150',
    },
  },
  build: {
    rollupOptions: {
      input: {
        ingress: resolve(__dirname, 'index.html'),
        card: resolve(__dirname, 'src/entry-card.js'),
      },
      output: {
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name].[ext]',
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
});
