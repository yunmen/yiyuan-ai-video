import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import vm from 'node:vm'

/** 隔离执行真实页面脚本，以可控 API 和定时器验证请求参数与终态。 */
function page(name, exports, api, overrides = {}) {
  const source = readFileSync(new URL(`../src/pages/${name}/index.vue`, import.meta.url), 'utf8')
  const script = source.match(/<script setup>([\s\S]*?)<\/script>/)[1]
    .replace(/import\s+[\s\S]*?\s+from\s+['"][^'"]+['"]/g, '')
    .replace(/\/\/ #ifndef H5[\s\S]*?\/\/ #endif/g, '')
  const timers = new Map()
  let timerId = 0
  const notices = []
  const unload = []
  const store = { isLoggedIn: true, setCreditTotal() {} }
  const context = vm.createContext({
    api, console, Map, Set, Date,
    QRCode: { toDataURL: async (url) => `data:image/png;${url}` },
    ref: (value) => ({ value }),
    computed: (getter) => ({ get value() { return getter() } }),
    onLoad() {}, onHide() {}, onShow() {}, onMounted() {}, onPullDownRefresh() {},
    onUnload: (callback) => unload.push(callback),
    useUserStore: () => store,
    useGenConfig: () => ({}),
    uni: { showToast: (options) => notices.push(options.title) },
    workStatus: (status) => ({ key: status === 'success' ? 'completed' : status }),
    workFailReason: () => '生成失败',
    isWorkTask: (item) => item.type !== 'deconstruct',
    setTimeout: (callback) => { timers.set(++timerId, callback); return timerId },
    clearTimeout: (id) => timers.delete(id),
    setInterval: (callback) => { timers.set(++timerId, callback); return timerId },
    clearInterval: (id) => timers.delete(id),
    showAppActionSheet: (options) => { context.actions = options },
    ...overrides,
  })
  vm.runInContext(`${script}\nglobalThis.page = { ${exports} }`, context)
  return { ...context.page, timers, notices, unload, context }
}

test('动作复刻只提交人物场景且不序列化营销文案，带货仍保留', () => {
  const source = readFileSync(new URL('../src/pages/studio/index.vue', import.meta.url), 'utf8')
  const script = source.slice(source.indexOf('function activeReplaceImages()'), source.indexOf('/** 构造图片九宫格'))
  const remake = { refVideo: { url: 'ref.mp4' }, replicateMode: 'action', replaceImages: [
    { url: 'scene.jpg', role: 'scene', elementId: 's' }, { url: 'product.jpg', role: 'product', elementId: 'p' },
  ], elements: [{ id: 's', kind: 'scene' }, { id: 'p', kind: 'product' }], slotBindings: {}, shots: [], goal: '', intent: ['product'], creative: 'normal', hookBoost: 'strong', format: 'ad' }
  const context = vm.createContext({ remake, isAction: { value: true }, templateId: { value: null }, preparedCopy: { title: '商品标题', subtitle: '', script: '带货口播' }, elementImages: (el) => remake.replaceImages.filter((img) => img.elementId === el.id) })
  vm.runInContext(`${script}\nglobalThis.build = buildRemakePayload`, context)
  const action = context.build()
  assert.equal(action.replicate_mode, 'action')
  assert.deepEqual(Array.from(action.materials), ['ref.mp4', 'scene.jpg'])
  assert.deepEqual(Array.from(action.intent), ['scene'])
  assert.equal(action.material_groups.length, 1)
  assert.equal(action.remark, undefined)
  assert.equal(action.hook_boost, undefined)
  context.isAction.value = false
  remake.replicateMode = 'commerce'
  const commerce = context.build()
  assert.equal(commerce.materials.length, 3)
  assert.match(commerce.remark, /带货口播/)
})

test('动作模式在产品文案接口入口直接返回', async () => {
  const source = readFileSync(new URL('../src/pages/studio/index.vue', import.meta.url), 'utf8')
  const script = source.slice(source.indexOf('async function prepareRemakeCopy()'), source.indexOf('/** 用户主动修改'))
  const context = vm.createContext({ requireLogin: () => true, isAction: { value: true } })
  vm.runInContext(`${script}\nglobalThis.prepare = prepareRemakeCopy`, context)
  await context.prepare()
})

/** 提供任务详情页最小 API，默认模拟已完成的视频任务。 */
function detailApi(overrides = {}) {
  return {
    storyboard: {
      shotUpdate: { post: async () => ({ code: 1 }) },
      list: { post: async () => ({ code: 1, data: { shots: [] } }) },
    },
    task: {
      detail: { post: async () => ({ code: 1, data: { status: 'success' } }) },
      regenerateSegment: { post: async () => ({ code: 1 }) },
    },
    ...overrides,
  }
}

/** 设置可编辑且允许重跑的视频任务。 */
function detailPage(api) {
  const result = page('task-detail', 'detail, taskId, regenerating, regenerateShot, pollDetail, startPolling', api)
  result.taskId.value = 8
  result.detail.value = { type: 'video', status: 'success', usage: { subtitle_timing: [{}] } }
  return result
}

test('画面重跑不修改台词，成功终态停止轮询', async () => {
  const api = detailApi()
  const payloads = []
  api.task.regenerateSegment.post = async (payload) => { payloads.push(payload); return { code: 1 } }
  const result = detailPage(api)
  await result.regenerateShot({ index: 0, prompt: '镜头推进' })
  assert.equal(payloads[0].new_text, '')
  assert.equal(result.regenerating.value, true)
  await result.pollDetail()
  assert.equal(result.regenerating.value, false)
  assert.equal(result.timers.size, 0)
  assert.ok(result.notices.includes('局部重跑完成'))
})

test('提示词保存失败不提交重跑，并释放锁', async () => {
  const api = detailApi()
  let calls = 0
  api.storyboard.shotUpdate.post = async () => ({ code: 0, message: '保存失败' })
  api.task.regenerateSegment.post = async () => { calls += 1 }
  const result = detailPage(api)
  await result.regenerateShot({ index: 0, prompt: '画面描述' })
  assert.equal(calls, 0)
  assert.equal(result.regenerating.value, false)
})

test('保存提示词请求在途时阻止重复重跑', async () => {
  const api = detailApi()
  let finish
  let calls = 0
  api.storyboard.shotUpdate.post = () => { calls += 1; return new Promise((resolve) => { finish = resolve }) }
  const result = detailPage(api)
  const pending = result.regenerateShot({ index: 0 })
  await result.regenerateShot({ index: 0 })
  assert.equal(calls, 1)
  finish({ code: 1 })
  await pending
})

test('重跑失败或网络异常均结束等待', async () => {
  for (const status of ['failed', 'network']) {
    const api = detailApi()
    api.task.detail.post = async () => {
      if (status === 'network') throw new Error('网络中断')
      return { code: 1, data: { status } }
    }
    const result = detailPage(api)
    result.startPolling()
    await result.pollDetail()
    assert.equal(result.regenerating.value, false)
    assert.equal(result.timers.size, 0)
  }
})

test('作品分页以原始总数计数，内部任务占满首页仍可继续加载', async () => {
  const calls = []
  const api = { task: { list: { post: async (payload) => {
    calls.push(payload.pageNum)
    return { code: 1, total: 31, data: payload.pageNum === 1
      ? Array.from({ length: 30 }, (_, id) => ({ id, type: 'deconstruct' }))
      : [{ id: 31, type: 'video' }] }
  } } } }
  const result = page('works', 'loadWorks, loadMore, works, visibleWorks, hasMore', api)
  await result.loadWorks()
  assert.equal(result.visibleWorks.value.length, 0)
  assert.equal(result.hasMore.value, true)
  await result.loadMore()
  assert.equal(result.visibleWorks.value[0].id, 31)
  assert.equal(result.hasMore.value, false)
  assert.deepEqual(calls, [1, 2])
})

test('仅可续跑失败任务显示续跑入口，并调用 resume 而非 regenerate', async () => {
  let resumed = 0
  const api = { task: {
    resume: { post: async () => { resumed += 1; return { code: 1 } } },
    list: { post: async () => ({ code: 1, total: 0, data: [] }) },
  } }
  const result = page('works', 'openActions, resumeWork', api)
  result.openActions({ id: 1, status: 'failed', resumable: true })
  assert.ok(result.context.actions.itemList.includes('继续生成（不重复扣额度）'))
  await result.resumeWork({ id: 1 })
  assert.equal(resumed, 1)
  result.openActions({ id: 2, status: 'failed', resumable: false })
  assert.ok(!result.context.actions.itemList.some((label) => label.startsWith('继续生成')))
})

test('非模拟充值必须展示后端支付地址对应二维码，停止等待后释放锁', async () => {
  const api = { payment: { orderRecharge: { post: async () => ({
    code: 1, data: { order_no: 'TEST-ORDER', mock: false, code_url: 'weixin://test-payment' },
  }) } } }
  const result = page('recharge', 'handleRecharge, packages, selectedId, paymentQr, paying, cancelPayment', api)
  result.packages.value = [{ id: 1 }]
  result.selectedId.value = 1
  const pending = result.handleRecharge()
  await new Promise((resolve) => setImmediate(resolve))
  assert.equal(result.paymentQr.value, 'data:image/png;weixin://test-payment')
  assert.equal(result.paying.value, true)
  result.cancelPayment()
  await pending
  assert.equal(result.paying.value, false)
})

test('支付取消结束等待 Promise 且移除定时器', async () => {
  const result = page('recharge', 'waitForPayment, cancelPayment', {})
  const pending = result.waitForPayment('TEST-ORDER')
  result.cancelPayment()
  assert.equal(await pending, false)
  assert.equal(result.timers.size, 0)
})

test('素材库选择模式仅列视频，回传后返回；普通模式保持预览', () => {
  let load
  let returned = 0
  const events = []
  const filter = { value: 'all' }
  const result = page('materials', 'preview, selectionMode', {}, {
    reactive: (value) => value,
    onLoad: (callback) => { load = callback },
    getCurrentInstance: () => ({ proxy: { getOpenerEventChannel: () => ({ emit: (...args) => events.push(args) }) } }),
    useAccountList: () => ({ filter }),
    uni: { navigateBack: () => { returned += 1 } },
  })
  load({ mode: 'select', kind: 'video' })
  assert.equal(filter.value, 'video')
  result.preview({ kind: 'image', url: '/image.png' })
  assert.equal(returned, 0)
  const item = { id: 1, kind: 'video', url: '/video.mp4', filename: '已上传视频' }
  result.preview(item)
  assert.equal(returned, 1)
  assert.equal(events[0][0], 'materialSelected')
  assert.equal(events[0][1], item)
  result.selectionMode.value = false
  result.preview(item)
  assert.equal(events.length, 1)
})

test('图片选择由用户标记用途，保存失败可重试且不调用AI', async () => {
  let load
  let returned = 0
  let fail = true
  const events = [], requests = []
  const filter = { value: 'all' }
  const result = page('materials', 'preview, saveRole, roleMaterial, roleError', {
    common: { materialRole: { post: async (payload) => {
      requests.push(payload)
      return fail ? { code: 0, message: '保存失败' } : { code: 1, data: payload }
    } } },
  }, {
    reactive: (value) => value,
    onLoad: (callback) => { load = callback },
    getCurrentInstance: () => ({ proxy: { getOpenerEventChannel: () => ({ emit: (...args) => events.push(args) }) } }),
    useAccountList: () => ({ filter }),
    uni: { navigateBack: () => { returned += 1 } },
  })
  load({ mode: 'select', kind: 'image', role: 'person' })
  assert.equal(filter.value, 'image')
  result.preview({ kind: 'video', url: '/video.mp4' })
  assert.equal(returned, 0)
  const item = { kind: 'image', url: '/person.jpg', role: 'scene' }
  result.preview(item)
  assert.equal(result.roleMaterial.value, item)
  await result.saveRole('scene')
  assert.equal(requests.length, 0)
  await result.saveRole('person')
  assert.equal(returned, 0)
  assert.equal(result.roleError.value, '保存失败')
  fail = false
  await result.saveRole('person')
  assert.equal(returned, 1)
  assert.equal(events[0][0], 'materialSelected')
  assert.equal(events[0][1].role, 'person')
  assert.equal(requests[1].url, item.url)
})

test('素材库上传成功刷新列表，取消、超限与失败释放上传锁', async () => {
  let refreshes = 0
  let uploads = 0
  let mode = 'success'
  const filter = { value: 'all' }
  let markFails = true
  const api = { common: { materialType: { post: async ({ kind }) => {
    if (markFails) return { code: 0, message: '标识保存失败' }
    assert.equal(kind, 'video')
    return { code: 1 }
  } } } }
  const result = page('materials', 'uploadMaterial, markMaterial, pendingMaterial, markError, uploading, uploadError, uploadMessage, selectionMode', api, {
    reactive: (value) => value,
    getCurrentInstance: () => ({}),
    useAccountList: () => ({ filter, refresh: async () => { refreshes += 1 } }),
    requireLogin: () => true,
    MAX_UPLOAD_MB: 50,
    chooseMaterialFile: async (videoOnly) => {
      assert.equal(videoOnly, true)
      if (mode === 'cancel') throw new Error('CANCEL')
      return { path: '/local.mp4', name: '视频.mp4', size: mode === 'large' ? 51 * 1024 * 1024 : 10 }
    },
    uploadMedia: async (path, options) => {
      uploads += 1
      assert.equal(path, '/local.mp4')
      assert.equal(options.filename, '视频.mp4')
      if (mode === 'fail') throw new Error('网络异常')
      options.onProgress(100)
      return { url: '/uploaded.mp4', kind: mode === 'auto' ? 'video' : null, needs_confirmation: mode !== 'auto' }
    },
  })
  result.selectionMode.value = true
  await result.uploadMaterial()
  assert.equal(refreshes, 1)
  assert.equal(result.pendingMaterial.value.url, '/uploaded.mp4')
  await result.uploadMaterial()
  assert.equal(uploads, 1)
  await result.markMaterial('video')
  assert.equal(result.markError.value, '标识保存失败')
  assert.ok(result.pendingMaterial.value)
  markFails = false
  await result.markMaterial('video')
  assert.equal(result.pendingMaterial.value, null)
  assert.match(result.uploadMessage.value, /标识已保存/)
  for (const next of ['cancel', 'large', 'fail']) {
    mode = next
    await result.uploadMaterial('video')
    assert.equal(result.uploading.value, false)
    if (next === 'cancel') assert.equal(result.uploadError.value, '')
    if (next === 'large') assert.match(result.uploadError.value, /50MB/)
    if (next === 'fail') assert.equal(result.uploadError.value, '网络异常')
  }
  assert.equal(refreshes, 2)
  assert.equal(uploads, 2)
  mode = 'auto'
  await result.uploadMaterial()
  assert.equal(result.pendingMaterial.value, null)
  assert.match(result.uploadMessage.value, /自动识别为视频/)
  assert.equal(refreshes, 3)
})

test('真实支付到账终态结束等待，页面卸载也能结束等待', async () => {
  const api = { payment: { orderStatus: { post: async () => ({ code: 1, data: { status: 3 } }) } } }
  const result = page('recharge', 'waitForPayment', api)
  const pending = result.waitForPayment('TEST-ORDER')
  const [id, callback] = [...result.timers][0]
  result.timers.delete(id)
  await callback()
  assert.equal(await pending, true)
  const cancelled = result.waitForPayment('TEST-OTHER')
  result.unload.forEach((callback) => callback())
  assert.equal(await cancelled, false)
})
