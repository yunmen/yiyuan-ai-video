// 音色试听单例播放器:全局共享一个 Audio 实例,保证同时只有一段样音在播放。
import { ref } from 'vue'

const audio = typeof Audio !== 'undefined' ? new Audio() : null
const playingUrl = ref('')
// 播放失败原因(如样音文件缺失、浏览器拦截自动播放),供 UI 提示;空串表示无错误
const error = ref('')

if (audio) {
  audio.addEventListener('ended', () => { playingUrl.value = '' })
  audio.addEventListener('error', () => {
    playingUrl.value = ''
    error.value = '样音加载失败,请稍后重试或改用「试听配音」合成真实音频'
  })
}

export function useVoiceAudition() {
  /**
   * 播放/暂停一段样音。
   * 失败必须让用户看见:此前 `play().catch(() => {})` 静默吞掉异常,用户点 ▶ 毫无反应,
   * 只能推断"功能坏了"。这里统一记录 error,页面据此提示。
   * @param {string} url 样音地址
   */
  function play(url) {
    if (!url) {
      error.value = '该音色暂无试听样音'
      return
    }
    if (!audio) {
      error.value = '当前浏览器不支持音频播放'
      return
    }
    // 再次点击同一段:暂停并复位
    if (playingUrl.value === url) {
      audio.pause()
      audio.currentTime = 0
      playingUrl.value = ''
      return
    }
    error.value = ''
    audio.src = url
    audio.play().catch(() => {
      playingUrl.value = ''
      error.value = '样音播放被浏览器拦截,请再点一次或改用「试听配音」'
    })
    playingUrl.value = url
  }
  /** 停止播放并清除错误提示 */
  function stop() {
    if (audio) {
      audio.pause()
      audio.currentTime = 0
    }
    playingUrl.value = ''
    error.value = ''
  }
  return { playingUrl, error, play, stop }
}
