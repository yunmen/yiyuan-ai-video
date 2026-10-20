import { nextTick, onMounted, onUpdated, ref } from 'vue'

/** 显式列出各端原生表单属性，小程序编译不支持原生节点的对象 v-bind。 */
export const APP_FIELD_PROPS = {
  modelValue: { type: [String, Number], default: '' },
  type: { type: String, default: 'text' },
  name: { type: String, default: '' },
  password: Boolean,
  maxlength: { type: [String, Number], default: 140 },
  disabled: Boolean,
  focus: Boolean,
  placeholder: { type: String, default: '' },
  placeholderClass: { type: String, default: '' },
  placeholderStyle: { type: String, default: '' },
  confirmType: { type: String, default: 'done' },
  autocomplete: { type: String, default: 'off' },
  ariaLabel: { type: String, default: '' },
}

/** 原生表单共用值同步和 H5 可访问名称；不接管焦点、软键盘或输入校验。 */
export function useAppField(props, emit) {
  // 组件引用仅用于 H5 名称同步，小程序编译后不包含浏览器节点访问。
  const field = ref(null)

  /** 将 uni 原生输入值同步给页面，同时保留原有 @input 校验。 */
  function handleInput(event) {
    emit('update:modelValue', event.detail.value)
    emit('input', event)
  }

  /** 保留页面原有的软键盘确认操作，例如提交已粘贴的视频链接。 */
  function handleConfirm(event) { emit('confirm', event) }

  /** 当前 uni H5 将名称留在包装层，因此同步到真实输入节点，显隐切换后也更新。 */
  async function syncAccessibleName() {
    // #ifdef H5
    await nextTick()
    const root = field.value?.$el || field.value
    const input = root?.querySelector?.('input, textarea')
    // 旧表单缺少名称时复用已有中文提示。
    const label = props.ariaLabel || props.placeholder
    if (input && label) input.setAttribute('aria-label', String(label))
    // #endif
  }

  onMounted(syncAccessibleName)
  onUpdated(syncAccessibleName)
  return { field, handleInput, handleConfirm }
}
