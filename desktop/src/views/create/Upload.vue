<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import QRCode from 'qrcode'
import api from '@/api'
import { takeRefFrames } from '@/utils/video'

const router = useRouter()
const route = useRoute()

const template = ref(null)
const loading = ref(true)
const submitting = ref(false)
const confirmVisible = ref(false)

// 定价(来自后端业务配置,可在管理端修改)
const price = ref('9.90')

// 收银台
const payVisible = ref(false)
const payOrder = ref(null)          // { order_no, amount, gateway, code_url, mock }
const qrDataUrl = ref('')
const paying = ref(false)
let pollTimer = null

// 素材表单(按原型:产品图 / 大标题 / 副标题 / 口播文案 / Logo)
const productUrl = ref('')
const title = ref('')
const subtitle = ref('')
const script = ref('')
const logoUrl = ref('')
const logoOn = ref(false)

// 「上传参考做」抽出的参考画面:多于 1 张时作为多图参考素材,走参考生视频(r2v)
const refFrames = ref([])

// 实际提交的素材:参考画面优先,否则用单张产品图
// (1 张 → 图生视频 i2v;多张 → 参考生视频 r2v,由后端按素材数量自动选择)
const productImages = computed(() =>
  refFrames.value.length ? refFrames.value : (productUrl.value ? [productUrl.value] : [])
)

const canGenerate = computed(() => productImages.value.length > 0 && !!title.value.trim())

async function loadDetail() {
  loading.value = true
  try {
    const res = await api.template.detail.post({ id: Number(route.params.id) })
    if (res.code === 1) {
      template.value = res.data
      // 预填后台为模板配置的默认文案(用户可自行修改)
      const dt = res.data.default_text || {}
      title.value = dt.title || res.data.title || ''
      subtitle.value = dt.subtitle || ''
      script.value = dt.script || ''
    }
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
}

function beforeUpload(data, type) {
  const imgExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
  const ext = (data.file.name || '').split('.').pop().toLowerCase()
  if (!imgExts.includes(ext)) {
    window.$message?.error('仅支持图片格式')
    return false
  }
  if (data.file.file.size > 50 * 1024 * 1024) {
    window.$message?.error('文件大小不能超过50MB')
    return false
  }
  return true
}

function makeUploader(setter, tip) {
  return async function customRequest({ file, onFinish, onError, onProgress }) {
    try {
      const formData = new FormData()
      formData.append('file', file.file)
      const res = await api.common.upload.file.post(formData, {
        onUploadProgress: (e) => {
          if (e.total) onProgress({ percent: Math.round((e.loaded * 100) / e.total) })
        }
      })
      if (res.code === 1) {
        setter(res.data.url)
        onFinish()
        window.$message?.success(tip)
      } else onError()
    } catch (e) { onError() }
  }
}
// 手动上传产品图视为主动替换素材,清掉参考视频抽出的画面,避免两者混淆
const uploadProduct = makeUploader(v => { productUrl.value = v; refFrames.value = [] }, '产品图已上传')
const uploadLogo = makeUploader(v => { logoUrl.value = v }, 'Logo 已上传')

// AI 一键写文案:有草稿则润色,无草稿则按模板主题从零创作
const aiWriting = ref(false)
async function aiWriteCopy() {
  aiWriting.value = true
  try {
    const res = await api.common.copyGenerate.post({
      template_title: template.value?.title || '',
      category: template.value?.category || '',
      title: title.value.trim() || undefined,
      subtitle: subtitle.value.trim() || undefined,
      script: script.value.trim() || undefined,
    })
    if (res.code === 1 && res.data) {
      if (res.data.title) title.value = res.data.title
      if (res.data.subtitle) subtitle.value = res.data.subtitle
      if (res.data.script) script.value = res.data.script
      window.$message?.success(res.data.fallback ? 'AI 暂不可用,已填充推荐文案,可手动微调' : 'AI 文案已生成,可手动微调')
    }
  } catch (e) { /* 拦截器已提示 */ }
  aiWriting.value = false
}

function resetForm() {
  const dt = template.value?.default_text || {}
  productUrl.value = ''
  refFrames.value = []
  title.value = dt.title || template.value?.title || ''
  subtitle.value = dt.subtitle || ''
  script.value = dt.script || ''
  logoUrl.value = ''
  logoOn.value = false
  window.$message?.success('已恢复模板默认内容')
}

function openConfirm() {
  if (!canGenerate.value) return
  confirmVisible.value = true
}

async function doGenerate() {
  confirmVisible.value = false
  submitting.value = true
  try {
    const materials = [...productImages.value]
    if (logoOn.value && logoUrl.value) materials.push(logoUrl.value)
    const remarkParts = []
    if (title.value.trim()) remarkParts.push(`大标题:${title.value.trim()}`)
    if (subtitle.value.trim()) remarkParts.push(`副标题:${subtitle.value.trim()}`)
    if (script.value.trim()) remarkParts.push(`口播文案:${script.value.trim()}`)
    // 先创建支付订单,支付成功后由后端自动创建生成任务
    const res = await api.payment.orderCreate.post({
      template_id: Number(route.params.id),
      materials,
      remark: remarkParts.join(';') || undefined,
      device: window.innerWidth <= 768 ? 'mobile' : 'desktop'
    })
    if (res.code === 1 && res.data) {
      payOrder.value = res.data
      payVisible.value = true
      if (res.data.code_url && !res.data.mock) {
        qrDataUrl.value = await QRCode.toDataURL(res.data.code_url, { width: 220, margin: 1 })
      }
      startPolling(res.data.order_no)
    }
  } catch (e) { /* 拦截器已提示 */ }
  submitting.value = false
}

// 轮询订单状态,交付成功(3)后跳生成页
function startPolling(orderNo) {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const res = await api.payment.orderStatus.post({ order_no: orderNo })
      if (res.code === 1 && res.data) {
        if (res.data.status === 3 && res.data.task_id) {
          stopPolling()
          payVisible.value = false
          window.$message?.success('支付成功,开始生成')
          router.replace(`/generate/${res.data.task_id}`)
        } else if (res.data.status === 4) {
          stopPolling()
          payVisible.value = false
          window.$message?.warning('订单已超时取消,请重新下单')
        }
      }
    } catch (e) { /* 轮询失败静默重试 */ }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// 开发环境模拟支付
async function mockPay() {
  if (!payOrder.value) return
  paying.value = true
  try {
    const res = await api.payment.mockConfirm.post({ order_no: payOrder.value.order_no })
    if (res.code !== 1) paying.value = false
  } catch (e) { paying.value = false }
}

function closePay() {
  stopPolling()
  payVisible.value = false
}

async function loadPrice() {
  try {
    const res = await api.payment.genConfig.post()
    if (res.code === 1 && res.data?.['gen.video_price']) price.value = res.data['gen.video_price']
  } catch (e) { /* 用默认定价 */ }
}

// 「上传参考做」抽出的参考画面:一次性使用,进入本页即作为素材预填
function applyRefFrames() {
  const frames = takeRefFrames()
  if (!frames.length) return
  refFrames.value = frames
  window.$message?.success(`已使用参考视频的 ${frames.length} 张画面，可直接生成或重新上传`)
}

function clearRefFrames() {
  refFrames.value = []
  window.$message?.success('已清除参考画面')
}

onMounted(() => { loadDetail(); loadPrice(); applyRefFrames() })
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="material-page">
    <n-spin :show="loading">
      <div v-if="template" class="wrap mcols">
        <!-- 左:模板预览 -->
        <div class="preview card">
          <div class="pv" :style="template.cover ? { backgroundImage: `url(${template.cover})` } : {}">
            <video
              v-if="template.video_url"
              :src="template.video_url"
              :poster="template.cover"
              controls
              playsinline
              class="pv-video"
            ></video>
            <template v-else>
              <div class="play">
                <svg width="24" height="24" viewBox="0 0 24 24"><path d="M9 6L18 12L9 18V6Z" fill="#fff"/></svg>
              </div>
            </template>
            <div class="dur">0:{{ String(template.duration || 15).padStart(2, '0') }}</div>
          </div>
          <div class="pmeta">
            <b>{{ template.title }}</b>
            <span>{{ template.duration || 15 }}秒 · {{ template.category }}</span>
          </div>
        </div>

        <!-- 右:素材表单 -->
        <div class="form">
          <div class="item">
            <div class="row">
              <div style="display:flex; gap:12px; align-items:center">
                <div class="thumb">
                  <img v-if="productUrl" :src="productUrl" alt="产品图" />
                  <svg v-else width="30" height="30" viewBox="0 0 30 30"><path d="M15 11V19M15 11L11.5 14.5M15 11L18.5 14.5" fill="none" stroke="#B0B3B8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 21H21" fill="none" stroke="#B0B3B8" stroke-width="1.8" stroke-linecap="round"/></svg>
                </div>
                <div>
                  <div class="lbl">你的产品图</div>
                  <div class="sub">拍照或相册选一张</div>
                </div>
              </div>
              <n-upload
                accept="image/*"
                :max="1"
                :show-file-list="false"
                :custom-request="uploadProduct"
                :before-upload="beforeUpload"
              >
                <div class="up" :class="{ gray: productUrl }">{{ productUrl ? '已上传' : '上传' }}</div>
              </n-upload>
            </div>
          </div>

          <!-- 参考画面(「上传参考做」自动填充,多张时走参考生视频 r2v) -->
          <div v-if="refFrames.length" class="item">
            <div class="row">
              <div class="lbl">参考画面（{{ refFrames.length }} 张）</div>
              <button class="ai-btn" @click="clearRefFrames">清除</button>
            </div>
            <div class="frame-list">
              <img v-for="(f, i) in refFrames" :key="i" :src="f" :alt="`参考画面 ${i + 1}`" />
            </div>
            <div class="sub">将用这些画面作为参考生成，效果更接近原视频</div>
          </div>

          <div class="item">
            <div class="row">
              <div class="lbl">视频大标题</div>
              <div style="display:flex; align-items:center; gap:10px">
                <button class="ai-btn" :disabled="aiWriting" @click="aiWriteCopy">
                  {{ aiWriting ? 'AI 创作中...' : (title || subtitle || script ? '智能思考' : 'AI 一键写文案') }}
                </button>
                <div class="counter">{{ title.length }}/20</div>
              </div>
            </div>
            <div class="inp"><input v-model="title" maxlength="20" placeholder="例如:全城最鲜火锅 开业5折(不会写?点右上角 AI)"></div>
          </div>

          <div class="item">
            <div class="row"><div class="lbl">副标题 / 卖点</div><div class="counter">{{ subtitle.length }}/30</div></div>
            <div class="inp"><input v-model="subtitle" maxlength="30" placeholder="例如:招牌毛肚 8.8 元 进店就送"></div>
          </div>

          <div class="item">
            <div class="row"><div class="lbl">想让视频说什么(选填)</div><div class="counter">{{ script.length }}/50</div></div>
            <div class="inp ta"><textarea v-model="script" maxlength="50" placeholder="例如:欢迎来本店,开业期间全场5折,错过等一年!"></textarea></div>
            <div class="sub" style="margin-top:8px">不填就用模板原配</div>
          </div>

          <div class="item">
            <div class="lbl" style="margin-bottom:12px">你的 Logo(选填)</div>
            <div class="row">
              <n-upload
                accept="image/*"
                :max="1"
                :show-file-list="false"
                :custom-request="uploadLogo"
                :before-upload="beforeUpload"
              >
                <div class="up gray">{{ logoUrl ? 'Logo 已上传' : '上传 Logo' }}</div>
              </n-upload>
              <n-switch v-model:value="logoOn" />
            </div>
          </div>
        </div>
      </div>
    </n-spin>

    <!-- 底部生成栏 -->
    <div class="footer">
      <div class="footer-in">
        <div>
          <div style="font-size:13px; font-weight:500">预计生成约 2 分钟</div>
          <div class="sub">单次生成 ¥{{ price }}</div>
        </div>
        <button class="gen-btn" :disabled="!canGenerate || submitting" @click="openConfirm">
          {{ submitting ? '提交中...' : '生成视频' }}
        </button>
      </div>
    </div>

    <!-- 生成确认 -->
    <n-modal v-model:show="confirmVisible" :mask-closable="true">
      <div class="confirm">
        <h3>确认开始生成？</h3>
        <p class="sub" style="text-align:center; line-height:1.7">将用你填写的素材替换模板内容，<br>生成大约需要 2 分钟。</p>
        <div class="confirm-btns">
          <div class="btn-outline" @click="confirmVisible = false">再看看</div>
          <div class="btn-primary" @click="doGenerate">去支付 ¥{{ price }}</div>
        </div>
      </div>
    </n-modal>

    <!-- 收银台 -->
    <n-modal :show="payVisible" :mask-closable="false" :closable="false">
      <div class="pay">
        <h3>微信支付</h3>
        <div class="pay-amount">¥{{ payOrder?.amount || price }}</div>
        <p class="sub" style="text-align:center">{{ payOrder?.mock ? '开发环境模拟支付' : '请使用微信扫码完成支付' }}</p>
        <img v-if="qrDataUrl" :src="qrDataUrl" class="pay-qr" alt="支付二维码" />
        <button v-if="payOrder?.mock" class="pay-mock-btn" :disabled="paying" @click="mockPay">
          {{ paying ? '支付中...' : '模拟支付(仅开发环境)' }}
        </button>
        <div class="pay-close" @click="closePay">取消支付</div>
      </div>
    </n-modal>
  </div>
</template>

<style scoped>
.material-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding-bottom: 96px; }
.wrap { max-width: var(--page-max); margin: 0 auto; }
.card { background: #fff; border-radius: var(--radius); box-shadow: var(--shadow-sm); }
.sub { font-size: 11px; color: var(--weak); margin-top: 4px; }

/* 预览 */
.preview { padding: 20px; margin: 16px 20px 0; }
.pv {
  height: 240px;
  border-radius: 12px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(90deg, #FA8C4D, #DB331F);
  background-size: cover;
  background-position: center;
  overflow: hidden;
}
.pv-video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; background: #000; }
.play {
  width: 56px; height: 56px; border-radius: 50%;
  background: rgba(0, 0, 0, 0.3);
  display: flex; align-items: center; justify-content: center;
}
.dur {
  position: absolute; right: 10px; bottom: 10px;
  background: rgba(0, 0, 0, 0.5); color: #fff;
  font-size: 11px; padding: 4px 8px; border-radius: 6px;
}
.pmeta { display: flex; justify-content: space-between; align-items: baseline; margin-top: 12px; }
.pmeta b { font-size: 15px; }
.pmeta span { font-size: 12px; color: var(--weak); }

/* 表单 */
.form { padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.item { background: #fff; border-radius: 12px; padding: 16px; }
.row { display: flex; align-items: center; justify-content: space-between; }
.thumb {
  width: 56px; height: 56px; border-radius: 8px;
  background: #F0F1F3; border: 1.5px solid #D8DADE;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden; flex: 0 0 56px;
}
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.lbl { font-size: 14px; font-weight: 500; }
.up {
  height: 36px; padding: 0 14px; border-radius: 18px;
  background: var(--brand-bg); color: var(--brand);
  font-size: 13px; font-weight: 500;
  display: flex; align-items: center; cursor: pointer; flex: 0 0 auto;
}
.up.gray { background: var(--bg); color: var(--body-c); }
.inp {
  height: 46px; border-radius: 10px; background: var(--bg);
  display: flex; align-items: center; padding: 0 12px; margin-top: 10px;
}
.inp input, .inp textarea {
  width: 100%; border: none; outline: none; background: transparent;
  font-size: 14px; font-family: inherit; color: var(--ink);
}
.inp.ta { height: 88px; align-items: flex-start; padding-top: 12px; }
.inp textarea { height: 64px; resize: none; line-height: 22px; }
.counter { font-size: 11px; color: var(--weak); }
.ai-btn {
  height: 26px; padding: 0 12px; border-radius: 13px; border: none;
  background: linear-gradient(90deg, #FF6A3D, var(--brand)); color: #fff;
  font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.ai-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* 底部生成栏 */
.footer {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 90;
  background: #fff; border-top: 1px solid var(--line);
}
.footer-in {
  max-width: var(--page-max); margin: 0 auto;
  height: 76px;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; gap: 12px;
}
.gen-btn {
  width: 176px; height: 48px; border-radius: 24px; border: none;
  background: var(--brand); color: #fff; font-size: 16px; font-weight: 700;
  cursor: pointer; font-family: inherit;
}
.gen-btn:disabled { background: #DCDFE4; cursor: not-allowed; }

/* 确认弹层 */
.confirm {
  width: 311px; background: #fff; border-radius: 16px; padding: 24px;
  display: flex; flex-direction: column; gap: 16px;
}
.confirm h3 { margin: 0; text-align: center; font-size: 18px; }
.confirm-btns { display: flex; gap: 10px; }
.btn-outline, .btn-primary {
  flex: 1; height: 48px; border-radius: 24px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; cursor: pointer;
}
.btn-outline { background: #fff; color: var(--brand); border: 1.5px solid var(--brand); font-weight: 500; }
.btn-primary { background: var(--brand); color: #fff; font-weight: 700; }

/* 收银台 */
.pay {
  width: 311px; background: #fff; border-radius: 16px; padding: 24px;
  display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.pay h3 { margin: 0; font-size: 18px; }
.pay-amount { font-size: 28px; font-weight: 700; color: var(--brand); }
.pay-qr { width: 220px; height: 220px; border-radius: 8px; border: 1px solid var(--line); }
.pay-mock-btn {
  width: 100%; height: 46px; border-radius: 23px; border: none;
  background: var(--brand); color: #fff; font-size: 15px; font-weight: 700;
  cursor: pointer; font-family: inherit;
}
.pay-mock-btn:disabled { background: #DCDFE4; cursor: not-allowed; }
.pay-close { font-size: 13px; color: var(--weak); cursor: pointer; margin-top: 4px; }

/* 桌面端双列 */
@media (min-width: 768px) {
  .mcols {
    display: grid;
    grid-template-columns: 420px 1fr;
    gap: 20px;
    padding: 24px;
    align-items: start;
  }
  .preview { margin: 0; position: sticky; top: calc(var(--header-h) + 16px); padding: 20px; }
  .pv { height: 320px; }
  .form { padding: 0; gap: 16px; }
  .item { padding: 20px; }
}
/* 参考视频抽出的画面列表 */
.frame-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.frame-list img {
  width: 76px;
  height: 76px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid #EEE;
  background: #F7F8FA;
}
</style>
