import { state, toast, addWork, downloadBlob } from '../store/app'
import { TPLS } from '../data'

export const GEN_STEPS = ['解析模板', '替换素材', '生成视频', '渲染输出']

let timer = null

function tplColors() {
  const found = TPLS.find(t => t.n === state.tpl.n)
  return found ? found.g : ['#FA8C4D', '#DB331F']
}

/** 用 canvas 合成一张真实封面图（DataURL） */
export async function composeCover() {
  const W = 540, H = 960
  const cv = document.createElement('canvas')
  cv.width = W; cv.height = H
  const ctx = cv.getContext('2d')
  const [c1, c2] = tplColors()
  const grad = ctx.createLinearGradient(0, 0, W, H)
  grad.addColorStop(0, c1); grad.addColorStop(1, c2)
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, W, H)

  // 产品图（中央，竖版裁切）
  if (state.imgDataUrl) {
    try {
      const img = await loadImg(state.imgDataUrl)
      const r = Math.max(W / img.width, (H * 0.62) / img.height)
      const w = img.width * r, h = img.height * r
      ctx.save()
      roundRect(ctx, 40, 90, W - 80, H * 0.62, 24)
      ctx.clip()
      ctx.drawImage(img, (W - w) / 2, 90 + (H * 0.62 - h) / 2, w, h)
      ctx.restore()
    } catch { /* 图片加载失败则用纯色背景 */ }
  }

  // 底部信息卡
  ctx.fillStyle = 'rgba(0,0,0,.45)'
  roundRect(ctx, 24, H * 0.70, W - 48, 220, 20)
  ctx.fill()

  ctx.fillStyle = '#fff'
  ctx.font = 'bold 44px "Noto Sans SC", sans-serif'
  wrapText(ctx, state.title || '爆款视频', 48, H * 0.70 + 72, W - 96, 52)
  ctx.font = '28px "Noto Sans SC", sans-serif'
  ctx.fillStyle = '#FFE3D9'
  wrapText(ctx, state.subtitle || '', 48, H * 0.70 + 140, W - 96, 36)

  // 品牌角标
  ctx.fillStyle = '#FF4D1C'
  roundRect(ctx, W - 150, 32, 110, 44, 10)
  ctx.fill()
  ctx.fillStyle = '#fff'
  ctx.font = 'bold 24px "Noto Sans SC", sans-serif'
  ctx.fillText('一源AI', W - 132, 62)

  return cv.toDataURL('image/jpeg', 0.82)
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

function wrapText(ctx, text, x, y, maxW, lineH) {
  let line = '', yy = y
  for (const ch of text) {
    if (ctx.measureText(line + ch).width > maxW) {
      ctx.fillText(line, x, yy); line = ch; yy += lineH
      if (yy > y + lineH * 2) { ctx.fillText(line + '…', x, yy); return }
    } else line += ch
  }
  ctx.fillText(line, x, yy)
}

function loadImg(src) {
  return new Promise((res, rej) => {
    const i = new Image()
    i.onload = () => res(i)
    i.onerror = rej
    i.src = src
  })
}

/** 把封面序列帧录制成 WebM 视频 Blob（真实可播放/可下载文件） */
export async function renderVideo(coverDataUrl, seconds = 3) {
  const W = 540, H = 960
  const cv = document.createElement('canvas')
  cv.width = W; cv.height = H
  const ctx = cv.getContext('2d')

  const stream = cv.captureStream(30)
  const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9' : 'video/webm'
  const rec = new MediaRecorder(stream, { mimeType: mime })
  const chunks = []
  rec.ondataavailable = e => e.data.size && chunks.push(e.data)

  const done = new Promise(res => { rec.onstop = res })
  rec.start()

  const cover = await loadImg(coverDataUrl)
  const frames = seconds * 30
  // 轻微推镜动画
  for (let f = 0; f < frames; f++) {
    const z = 1 + (f / frames) * 0.06
    ctx.fillStyle = '#000'
    ctx.fillRect(0, 0, W, H)
    const w = W * z, h = H * z
    ctx.drawImage(cover, (W - w) / 2, (H - h) / 2, w, h)
    await new Promise(r => requestAnimationFrame(r))
  }
  rec.stop()
  await done
  return new Blob(chunks, { type: 'video/webm' })
}

/** 启动生成流程：进度状态机 + 真实产出 */
export async function startGeneration(onDone) {
  if (state.gen.running) return
  state.gen.running = true
  state.gen.p = 0
  state.gen.left = false

  const total = 4000 // 约 4 秒完成（前端本地模拟生成管线）
  const t0 = performance.now()
  let cover = null, videoBlob = null

  await new Promise(resolve => {
    timer = setInterval(async () => {
      const el = performance.now() - t0
      state.gen.p = Math.min(1, el / total)
      state.gen.stepIdx = Math.min(GEN_STEPS.length - 1, Math.floor(state.gen.p * GEN_STEPS.length))
      if (state.gen.p >= 0.5 && !cover) cover = await composeCover()
      if (state.gen.p >= 1) { clearInterval(timer); resolve() }
    }, 100)
  })

  try {
    videoBlob = await renderVideo(cover)
  } catch {
    // MediaRecorder 不可用降级：只产出封面图
    videoBlob = null
  }

  const now = new Date()
  const pad = n => String(n).padStart(2, '0')
  const id = 'w' + now.getTime()
  const work = {
    id,
    n: state.tpl.n,
    t: `${now.getMonth() + 1}月${now.getDate()}日 ${pad(now.getHours())}:${pad(now.getMinutes())} · 竖版`,
    cover: cover,
    videoSize: videoBlob ? videoBlob.size : 0,
    title: state.title,
    subtitle: state.subtitle
  }
  // 内存中暂存 Blob（页面刷新后不持久化大文件）
  WORK_BLOBS[id] = videoBlob
  addWork(work)
  state.gen.running = false
  state.gen.workId = id
  if (!state.gen.left) onDone(id)
}

const WORK_BLOBS = {}

export function downloadWork(work) {
  if (!work) return
  const blob = WORK_BLOBS[work.id]
  if (blob) { downloadBlob(blob, `${work.n || '一源视频'}.webm`); return }
  // 无 Blob（刷新后）：把持久化的封面图重新打包下载
  if (work.cover) {
    fetch(work.cover).then(r => r.blob()).then(b => downloadBlob(b, `${work.n || '一源视频'}-封面.jpg`))
    toast('已下载封面图（演示生成器）')
  } else {
    toast('作品数据不完整')
  }
}
