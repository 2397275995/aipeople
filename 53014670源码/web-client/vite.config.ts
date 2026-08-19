import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 120000,
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 120000,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/live-stream': {
        target: 'http://vms.cn-huadong-1.xf-yun.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/live-stream/, ''),
        timeout: 120000,
      },
      '/vmss': {
        target: 'http://vms.cn-huadong-1.xf-yun.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/vmss/, ''),
        timeout: 120000,
      },
      '/avatar-stream': {
        target: 'http://vms.cn-huadong-1.xf-yun.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/avatar-stream/, ''),
        timeout: 120000,
      },
      '/flv-stream': {
        target: 'https://srs-stream.cn-huadong-1.xf-yun.com:18085',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/flv-stream/, ''),
        timeout: 120000,
        secure: false,
      },
    },
  },
})
