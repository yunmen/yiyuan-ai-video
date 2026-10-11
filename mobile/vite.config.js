import { defineConfig, loadEnv } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import { resolve } from 'path'

/** uni-app(H5) 构建配置：本地开发走 /api 代理，生产直接使用 VITE_APP_API_BASEURL。 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_DEV_BACKEND_TARGET || 'http://localhost:8801'

  return {
    plugins: [uni()],
    build: {
      outDir: 'dist',
      emptyOutDir: true
    },
    resolve: {
      alias: {
        '@': resolve(import.meta.dirname, 'src')
      }
    },
    server: {
      port: 5174,
      proxy: {
        '/api': {
          // 将 /api/* 代理到后端 /api/user/*，与 FastAPI 用户端前缀保持一致
          target: backendTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '/api/user')
        },
        '/shared': {
          // 开发时把共享资源转发给真正发布文件的 Backend
          target: backendTarget,
          changeOrigin: true
        }
      }
    },
    css: {
      preprocessorOptions: {
        scss: {
          // 让页面里可以直接使用 uni.scss 全局变量
          additionalData: '@import "@/uni.scss";'
        }
      }
    }
  }
})