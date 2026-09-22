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
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Vite >= 8.0.16 起构建级选项名为 rolldownOptions(旧名 rollupOptions 仍兼容), 与 admin 保持一致
    rolldownOptions: {
      // unplugin-vue-components 要逐个解析每个 .vue 里的 <n-xxx>,在「插件耗时」中占比很高,
      // Rolldown 会因此提示 PLUGIN_TIMINGS;按需引入本身就需要该插件,整体构建耗时正常,故关闭这条检查
      checks: {
        pluginTimings: false
      },
      output: {
        // Vite 8 底层是 Rolldown, 手动分包用 codeSplitting.groups(取代旧的 manualChunks)
        codeSplitting: {
          groups: [
            // 框架运行时: 版本稳定, 单独分包, 应用代码变更不会让它失效
            { name: 'vue-vendor', test: /node_modules[\\/](@vue|vue|vue-router|pinia)[\\/]/, priority: 50 },
            // 首屏静态依赖链上的第三方库(naive-ui 的离散 API、axios 及其内部依赖)合并为一个 vendor 块。
            // 只匹配 $initial(静态依赖链), 懒加载路由用到的 naive-ui 组件仍保持按需独立分包
            { name: 'initial-vendor', test: /node_modules[\\/]/, tags: ['$initial'], priority: 10 }
          ]
        }
      }
    }
  }
})
