import { createApp } from 'vue'
// Element Plus 按需引入：模板里的 el-* 组件由 unplugin-vue-components 自动引入(含各自样式)，
// 这里只引入需要以「全局方法 / 全局指令」方式使用的部分，并补齐它们的样式
// 注意：Element Plus 组件不再全局注册，代码里需要用组件时请显式 import，
//       不要写 resolveComponent('el-xxx') 之类的运行时解析(模板标签不受影响)
import { ElLoading, ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import 'element-plus/es/components/base/style/css' // CSS 变量与基础样式(--el-*)
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/es/components/notification/style/css'
import 'element-plus/es/components/loading/style/css'
import 'element-plus/theme-chalk/display.css'
import scui from './scui'
import i18n from './locales'
import router from './router'
import store from './store'
import App from './App.vue'

// 若页面是在发版前打开的,之后按需加载路由 chunk(含 CSS)会因文件已被新版本替换而失败,
// Vite 会派发可取消的 vite:preloadError 事件(不拦下就会抛未捕获错误,页面卡在报错状态)。
// 这里拦下并刷新一次,让用户直接拿到新版本;带时间戳兜底,避免极端情况反复刷新。
window.addEventListener('vite:preloadError', (event) => {
	event.preventDefault()
	const KEY = 'PRELOAD_ERROR_RELOAD_AT'
	const last = Number(sessionStorage.getItem(KEY) || 0)
	if (Date.now() - last < 10000) return
	sessionStorage.setItem(KEY, String(Date.now()))
	window.location.reload()
})

const app = createApp(App);

app.use(store);
app.use(router);
// 保持原有全局用法：this.$message / this.$notify / this.$msgbox($alert/$confirm/$prompt) / v-loading / this.$loading
app.use(ElMessage);
app.use(ElNotification);
app.use(ElMessageBox);
app.use(ElLoading);
app.use(i18n);
app.use(scui);

//挂载app
app.mount('#app');
