<script setup>
import { zhCN, dateZhCN, createDiscreteApi } from 'naive-ui'

const themeOverrides = {
  common: {
    primaryColor: '#FF4D1C',
    primaryColorHover: '#FF6A3D',
    primaryColorPressed: '#E83E0F',
    primaryColorSuppl: '#FF6A3D',
  }
}

// 暴露全局消息/对话框能力,供各页面(含上传页)直接使用
const discrete = createDiscreteApi(['message', 'dialog', 'notification'])
window.$dialog = discrete.dialog
window.$notification = discrete.notification

// 全局消息去重:同一类型+同一文案的提示 3 秒内只弹一次(与默认展示时长一致)。
// 用户在生成被拦截时往往连点按钮,原实现会把 4 条一模一样的警告堆叠刷屏。
const rawMessage = discrete.message
let lastTip = { type: '', text: '', at: 0 }
const messageMethods = ['create', 'info', 'success', 'warning', 'error', 'loading']
window.$message = Object.fromEntries(messageMethods.map(key => [
  key,
  (content, options) => {
    // 仅对字符串文案去重;渲染函数等内容无法稳定比较,原样放行
    if (typeof content === 'string') {
      const now = Date.now()
      if (content === lastTip.text && key === lastTip.type && now - lastTip.at < 3000) return
      lastTip = { type: key, text: content, at: now }
    }
    return rawMessage[key](content, options)
  },
]))
window.$message.destroyAll = rawMessage.destroyAll
</script>

<template>
  <n-config-provider :locale="zhCN" :date-locale="dateZhCN" :theme-overrides="themeOverrides">
    <n-message-provider>
      <router-view />
    </n-message-provider>
  </n-config-provider>
</template>
