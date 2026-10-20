<template>
  <textarea ref="field" :value="modelValue" :name="name" :maxlength="maxlength" :disabled="disabled" :focus="focus" :placeholder="placeholder" :placeholder-class="placeholderClass" :placeholder-style="placeholderStyle" :confirm-type="confirmType" :aria-label="ariaLabel" @input="handleInput" @confirm="handleConfirm" />
</template>

<script setup>
import { APP_FIELD_PROPS, useAppField } from '@/composables/useAppField'

/** 单个原生多行输入框保持单根节点，保留页面字号、尺寸与圆角。 */
defineOptions({ options: { virtualHost: true } })
const props = defineProps(APP_FIELD_PROPS)
const emit = defineEmits(['update:modelValue', 'input', 'confirm'])
// 与单行输入共用值同步和无障碍处理，不重复实现业务校验。
const { field, handleInput, handleConfirm } = useAppField(props, emit)
</script>
