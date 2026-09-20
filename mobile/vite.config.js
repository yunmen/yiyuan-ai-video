import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'


// https://vitejs.dev/config/
export default defineConfig(( ) => {
  return {
    plugins: [
      uni()
    ],
    publicDir: 'public',
    transpileDependencies: ["@dcloudio/uni-ui"],
    css: {
      preprocessorOptions: {
        scss: {
          silenceDeprecations: ['legacy-js-api']
        }
      }
    },
    server: {
      port: 5173,
      open: true,
      proxy: {
        '/api/user': {
          target: 'http://localhost:8801',
          changeOrigin: true,
          ws: true // 启用WebSocket代理
        },
      },
    },
  }
})
