import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  base: '/',
  worker: { format: 'es' },
  plugins: [react(), VitePWA({
    strategies: 'injectManifest', srcDir: 'src', filename: 'sw.ts',
    registerType: 'autoUpdate', injectRegister: 'auto',
    includeManifestIcons: false,
    manifest: { name: 'TourVoice Quận 4', short_name: 'TourVoice', start_url: '/client',
      display: 'standalone', theme_color: '#173e33', background_color: '#f5f4ec',
      icons: [{ src: '/assets/tourvoice-mark.png', sizes: '512x512', type: 'image/png' }] },
    injectManifest: { globPatterns: ['**/*.{js,mjs,css,html,png,svg,ttf,woff2}', 'assets/q4-map.json'], maximumFileSizeToCacheInBytes: 3000000 },
  })],
  build: { rollupOptions: { output: { manualChunks: { react: ['react', 'react-dom', 'react-router-dom'], map: ['leaflet'] } } } },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/storage': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
