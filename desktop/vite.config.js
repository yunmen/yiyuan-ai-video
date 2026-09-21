import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { NaiveUiResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  publicDir: 'public',
  plugins: [
    vue(),
    // naive-ui 按需引入:模板里的 <n-xxx> 自动注册,只打包用到的组件,避免整包进公共 chunk
    Components({
      resolvers: [NaiveUiResolver()],
      dts: false
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    open: true,
    proxy: {
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
