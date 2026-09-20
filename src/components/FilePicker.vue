<script setup>
// 通用文件选择器：点击图片/视频触发真实文件选择，读取为 DataURL
import { ref } from 'vue'

const props = defineProps({
  accept: { type: String, required: true }, // e.g. 'image/*' | 'video/mp4,video/webm'
  maxSizeMB: { type: Number, default: 20 }
})
const emit = defineEmits(['picked', 'error'])

const input = ref(null)

function open() { input.value?.click() }

function onChange(e) {
  const file = e.target.files && e.target.files[0]
  e.target.value = '' // 允许重复选择同一文件
  if (!file) return
  if (file.size > props.maxSizeMB * 1024 * 1024) {
    emit('error', `文件超过 ${props.maxSizeMB}MB，请压缩后再试`)
    return
  }
  const reader = new FileReader()
  reader.onload = () => emit('picked', { file, dataUrl: reader.result })
  reader.onerror = () => emit('error', '文件读取失败，请重试')
  reader.readAsDataURL(file)
}

defineExpose({ open })
</script>

<template>
  <input ref="input" type="file" :accept="accept" style="display:none" @change="onChange">
</template>
