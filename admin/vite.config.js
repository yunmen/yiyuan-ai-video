import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
	// 管理后台部署在 /admin/ 子路径下(Caddy 按该前缀路由)
	base: '/admin/',
	plugins: [vue()],
	resolve: {
		alias: {
			'@': resolve(__dirname, 'src'),
			'vue-i18n': 'vue-i18n/dist/vue-i18n.cjs.js'
		}
	},
	server: {
		port: 2800,
		open: false,
		proxy: {
			'/api': {
				target: 'http://127.0.0.1:8801',
				ws: true,
				changeOrigin: true
			}
		}
	},
	build: {
		outDir: 'dist',
		sourcemap: false,
		rollupOptions: {
				output: {
					manualChunks(id) {
						if (id.includes('node_modules')) {
							if (id.includes('@element-plus/icons-vue')) return 'elicons'
							if (id.includes('tinymce')) return 'tinymce'
							if (id.includes('echarts')) return 'echarts'
							if (id.includes('xgplayer')) return 'xgplayer'
							if (id.includes('codemirror')) return 'codemirror'
							if (id.includes('element-plus')) return 'element-plus'
							if (id.includes('vue') || id.includes('vue-router') || id.includes('vuex') || id.includes('vue-i18n')) return 'vue-vendor'
							return 'modules'
						}
					}
				}
		}
	}
})
