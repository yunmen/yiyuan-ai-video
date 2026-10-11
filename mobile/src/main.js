import { createSSRApp } from 'vue'
import { createPinia } from 'pinia'
import i18n from './locales/index'
import App from './App.vue'

export function createApp() {
  const app = createSSRApp(App)
  const pinia = createPinia()
  app.use(pinia)
  app.use(i18n)
  return { app }
}