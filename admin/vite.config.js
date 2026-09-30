import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

export default defineConfig({
	// 管理后台部署在 /admin/ 子路径下(Caddy 按该前缀路由)
	base: '/admin/',
	plugins: [
		vue(),
		// Element Plus 组件按需引入：模板里的 el-* 会自动 import 对应组件及其样式
		Components({
			// 本地组件已由 src/scui.js 全局注册，无需扫描目录，这里只做 Element Plus 解析
			dirs: [],
			dts: false,
			resolvers: [ElementPlusResolver()]
		})
	],
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
				target: 'http://127.0.0.1:8802',
				ws: true,
				changeOrigin: true
			}
		}
	},
	build: {
		outDir: 'dist',
		sourcemap: false,
		// 仍会超过 500KB 的分包(tinymce/xgplayer/echarts 等)都是懒加载路由依赖，不影响首屏
		chunkSizeWarningLimit: 1300,
		rolldownOptions: {
			// unplugin-vue-components 需要逐个解析每个 .vue 里的 el-* 标签，在「插件耗时」中占比很高，
			// Rolldown 会因此提示 PLUGIN_TIMINGS。实测整体构建耗时与改造前一致(约 12.3s)，
			// 该提示在本项目不可执行(按需引入本身就需要这个插件)，故关闭这条检查。
			checks: {
				pluginTimings: false
			},
			// @vueuse/core 是 element-plus 的传递依赖，其 dist 里几处 /* #__PURE__ */ 注解位置不符合
			// Rolldown 的要求，会输出 INVALID_ANNOTATION 警告。该警告只影响这个第三方文件的
			// tree-shaking 效果，不影响产物正确性，且无法在源码侧修复，这里过滤掉避免刷屏。
			onLog(level, log, defaultHandler) {
				const at = `${log.id || ''} ${log.message || ''}`
				if (log.code === 'INVALID_ANNOTATION' && at.includes('@vueuse/core')) return
				defaultHandler(level, log)
			},
			output: {
				// Vite 8 使用 Rolldown，手写分包改用 codeSplitting.groups(取代旧的 manualChunks)
				codeSplitting: {
					groups: [
						// 顺序无关，priority 高者优先匹配；正则里统一用 [\\/] 以兼容 Windows
						{ name: 'elicons', test: /node_modules[\\/]@element-plus[\\/]icons-vue[\\/]/, priority: 50 },
						{ name: 'element-plus', test: /node_modules[\\/]element-plus[\\/]/, priority: 40 },
						{ name: 'tinymce', test: /node_modules[\\/](@tinymce|tinymce)[\\/]/, priority: 40 },
						{ name: 'echarts', test: /node_modules[\\/](echarts|zrender)[\\/]/, priority: 40 },
						{ name: 'xgplayer', test: /node_modules[\\/]xgplayer/, priority: 40 },
						{ name: 'codemirror', test: /node_modules[\\/]@?codemirror[\\/]/, priority: 40 },
						{ name: 'vue-vendor', test: /node_modules[\\/](vue|vue-router|vue-i18n|pinia|@vue)[\\/]/, priority: 30 },
						{ name: 'modules', test: /node_modules[\\/]/, priority: 0 }
					]
				}
			}
		}
	}
})

