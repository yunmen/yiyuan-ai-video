import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  publicDir: 'public',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    open: true,
    proxy: {
      // 管理端/回调接口:不走 /api/user 前缀,原样转发
      // 注意: target 用 127.0.0.1 而非 localhost,避免 Node 优先解析 IPv6 ::1 导致 ECONNREFUSED
      '/api/admin': {
        target: 'http://127.0.0.1:8801/api',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/api/callback': {
        target: 'http://127.0.0.1:8801/api',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/api': {
        target: 'http://127.0.0.1:8801/api/user',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/static': {
        target: 'http://127.0.0.1:8801',
        changeOrigin: true
      },
    },
  },
})
