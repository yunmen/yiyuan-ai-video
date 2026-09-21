import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import './style/style.css'
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

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)


app.mount('#app')
