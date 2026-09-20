import { reactive, watch } from 'vue'

const LS = {
  get(key, fallback) {
    try {
      const v = localStorage.getItem(key)
      return v === null ? fallback : JSON.parse(v)
    } catch { return fallback }
  },
  set(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)) } catch { /* 存储满或隐私模式 */ }
  }
}

export const DEFAULT_MATERIAL = {
  title: '全城最鲜火锅 开业5折',
  subtitle: '招牌毛肚 8.8 元 进店就送',
  speak: '欢迎来本店，开业期间全场5折，毛肚只要8块8，错过等一年！'
}

export const state = reactive({
  cur: 'home',
  dir: '',
  stack: [],
  logged: LS.get('yy_logged', false),
  overlay: null, // 'login' | 'confirm' | null
  toastMsg: '',
  tpl: { n: '火锅店开业引流', d: '15秒 · 餐饮引流款' },
  hasImg: false,
  imgDataUrl: '',
  title: DEFAULT_MATERIAL.title,
  subtitle: DEFAULT_MATERIAL.subtitle,
  speak: DEFAULT_MATERIAL.speak,
  logoOn: false,
  works: LS.get('yy_works', []),
  credits: LS.get('yy_credits', 3),
  // 生成中状态机
  gen: { running: false, p: 0, stepIdx: 0, left: false, workId: null }
})

watch(() => state.logged, v => LS.set('yy_logged', v))
watch(() => state.works, v => LS.set('yy_works', v), { deep: true })
watch(() => state.credits, v => LS.set('yy_credits', v))

let toastTimer = null
export function toast(msg) {
  state.toastMsg = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { state.toastMsg = '' }, 1800)
}

export function go(id, back = false) {
  if (id === state.cur) return
  if (!back) state.stack.push(state.cur)
  state.dir = back ? 'slide-back' : 'slide-in'
  state.cur = id
}

export function goTab(id) {
  if (id === state.cur) return
  state.stack = []
  go(id)
}

export function pageBack(target) {
  if (target && target !== state.cur) {
    state.stack = []
    go(target, true)
  } else if (state.stack.length) {
    go(state.stack.pop(), true)
  }
}

export function pickTemplate(tpl) {
  state.tpl = { n: tpl.n, d: tpl.d }
  go('material')
}

export function resetMaterial() {
  state.hasImg = false
  state.imgDataUrl = ''
  state.title = DEFAULT_MATERIAL.title
  state.subtitle = DEFAULT_MATERIAL.subtitle
  state.speak = DEFAULT_MATERIAL.speak
  state.logoOn = false
}

export function addWork(work) {
  state.works.unshift(work)
}

export function removeWork(id) {
  const i = state.works.findIndex(w => w.id === id)
  if (i >= 0) state.works.splice(i, 1)
}

export function useCredit() {
  if (state.credits <= 0) return false
  state.credits--
  return true
}

/** 触发浏览器下载 */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

/** 分享：优先系统分享，降级复制链接 */
export async function shareLink(title, text) {
  const url = location.href
  if (navigator.share) {
    try {
      await navigator.share({ title, text, url })
      return
    } catch (e) {
      if (e && e.name === 'AbortError') return
    }
  }
  try {
    await navigator.clipboard.writeText(url)
    toast('链接已复制，去发给好友吧')
  } catch {
    toast('复制失败，请手动复制地址栏链接')
  }
}

export function restart() {
  state.stack = []
  state.logged = false
  state.overlay = null
  resetMaterial()
  state.tpl = { n: '火锅店开业引流', d: '15秒 · 餐饮引流款' }
  state.gen = { running: false, p: 0, stepIdx: 0, left: false, workId: null }
  state.dir = ''
  state.cur = 'home'
}
