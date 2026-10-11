// n-select 的 render-label:在下拉项右侧渲染「试听」按钮(▶/⏸),点击播放对应样音。
// 按钮 click 用 stopPropagation,避免触发选项选中(试听不影响当前已选音色)。
import { h } from 'vue'
import { useVoiceAudition } from '@/composables/useVoiceAudition'

// 试听失败提示挂在 window 上(与项目既有 window.$message 暴露方式一致):
// render-label 在下拉菜单的渲染函数里执行,拿不到页面 setup 作用域,故用全局提示。
function notifyError(msg) {
  if (msg && window.$message?.error) window.$message.error(msg)
}

export function useVoiceLabelRenderer() {
  const { playingUrl, error, play } = useVoiceAudition()
  return (option) => {
    // label 兜底:选中态/异常路径下 option.label 可能缺失,此时用 voice_type 反查中文名,
    // 绝不让用户看到一长串英文 ID
    const text = option?.label || option?.value || ''
    const children = [h('span', { class: 'vopt-label' }, text)]
    if (option?.preview) {
      children.push(
        h(
          'button',
          {
            class: 'vopt-play',
            type: 'button',
            title: '试听样音',
            onClick: (e) => {
              e.stopPropagation()
              const prev = error.value
              play(option.preview)
              // 播放失败时给出可见反馈(此前完全静默,用户以为按钮坏了)
              if (error.value && error.value !== prev) notifyError(error.value)
            },
          },
          playingUrl.value === option.preview ? '⏸' : '▶'
        )
      )
    }
    return h('span', { class: 'vopt' }, children)
  }
}
