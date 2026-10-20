<template>
  <input ref="field" :value="modelValue" :type="type" :name="name" :password="password" :maxlength="maxlength" :disabled="disabled" :focus="focus" :placeholder="placeholder" :placeholder-class="placeholderClass" :placeholder-style="placeholderStyle" :confirm-type="confirmType" :autocomplete="autocomplete" :aria-label="ariaLabel" @input="handleInput" @confirm="handleConfirm" />
</template>

<script setup>
import { APP_FIELD_PROPS, useAppField } from '@/composables/useAppField'

/** 单个原生输入框保持单根节点，小程序虚拟宿主将页面样式透传到该节点。 */
defineOptions({ options: { virtualHost: true } })
const props = defineProps(APP_FIELD_PROPS)
const emit = defineEmits(['update:modelValue', 'input', 'confirm'])
// 输入同步、事件透传与 H5 名称处理共用同一实现。
const { field, handleInput, handleConfirm } = useAppField(props, emit)
</script>
