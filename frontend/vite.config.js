import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// 开发期把 /api 代理到本地 FastAPI;生产由 FastAPI 挂载 dist,同源无需代理。
export default defineConfig({
  server: {
    host: true,          // 允许手机在同一 WiFi 下用局域网 IP 访问
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon-192.png', 'icon-512.png'],
      manifest: {
        name: 'zbrain · 第二脑',
        short_name: 'zbrain',
        description: '把碎片数字化,方便你用',
        theme_color: '#1c1c1e',
        background_color: '#f5f5f7',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
})
