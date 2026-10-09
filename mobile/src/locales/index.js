import { createI18n } from 'vue-i18n'

/** 当前默认中文。 */
const messages = {
  'zh-CN': {
    common: {
      appName: '一源',
      confirm: '确定',
      cancel: '取消',
      loading: '加载中…',
      empty: '暂无数据',
      retry: '重试',
    },
  },
}

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages,
  silentTranslationWarn: true,
})

export default i18n