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
window.$message = discrete.message
window.$dialog = discrete.dialog
window.$notification = discrete.notification
</script>

<template>
  <n-config-provider :locale="zhCN" :date-locale="dateZhCN" :theme-overrides="themeOverrides">
    <n-message-provider>
      <router-view />
    </n-message-provider>
  </n-config-provider>
</template>
