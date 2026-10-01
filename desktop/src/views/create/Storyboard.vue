<script setup>
// 九宫格强 Hook(链路 02/03):商品信息 → 强 Hook 脚本 → 九宫格分镜图 → 出片。
// 与「视频复刻」互补:复刻需要对标视频,九宫格链路仅凭商品信息即可从零生成。
// 全程复用既有原子接口:文案(common/copy/generate)、图片(task/imageCreate)、视频(task/create)。
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import { uploadFile } from '@/api/model/common'
import { useSkill } from '@/composables/useSkill'
import { useUserStore } from '@/store/modules/user'
import { useTaskEstimate } from '@/composables/useTaskEstimate'
import { useTaskCreate } from '@/composables/useTaskCreate'
import AdvancedCreationSettings from '@/components/create/AdvancedCreationSettings.vue'

const route = useRoute()
const userStore = useUserStore()
// 统一技能入口:AI 文案 / 图提示词走 /skill/* 标准流(与视频复刻同源),
// 渲染仍由下方 task.create / task.imageCreate 承接(终态交接)。
const { runCopy, runImagePrompt, error: skillError } = useSkill()
// 被「创作工作台」内嵌时(route 以 /studio 开头),隐藏本页独立大标题,避免与工作台 Hero 重复
const embedded = computed(() => route.path.startsWith('/studio'))
const { estText, refresh: estRefresh } = useTaskEstimate()
const { createAndNavigate } = useTaskCreate()

// 高级创作设置(创意档位 / 开头钩子 / 专家模式):与视频复刻同源的组件,
// 仅展示通用创作旋钮(showReplicate=false),让九宫格链路也能套用这些增强。
const adv = reactive({
  mode: 'full',
  intent: [],
  format: '',
  leadAct: '',
  creativeLevel: '',
  hookBoost: '',
  assetOverride: '',
  showExpert: false,
})

// —— 步骤 1:商品信息与脚本 ——
const productName = ref('')
const sellingPoints = ref('')
const copyTitle = ref('')
const copySubtitle = ref('')
const copyScript = ref('')
const writing = ref(false)

// 步骤 1 附:AI 英文图片提示词(从口播生成,可直接用于文生图)
const imagePromptText = ref('')   // 生成的英文图片提示词(可多条,换行分隔)
const promptStyle = ref('')       // 风格描述(可选,转英文前缀拼到每条提示词前)
const prompting = ref(false)

// —— 步骤 2:九宫格分镜图 ——
const storyboardImage = ref('')   // 分镜图地址(生成或上传)
const imageTaskId = ref(null)
const imaging = ref(false)
const drawing = ref(false)        // 轮询中(分镜图后台生成):提交按钮复位后仍显示"绘制中",避免界面空白
const imageError = ref('')        // 轮询被拒(鉴权过期/无权限等)时的持久提示,避免后台空转且界面无反馈
let pollTimer = null

// —— 步骤 3:出片 ——
const templates = ref([])
const templateId = ref(null)
const submitting = ref(false)

const device = () => (window.innerWidth <= 768 ? 'mobile' : 'desktop')
const canWrite = computed(() => !!productName.value.trim() && !writing.value)
const canGenerateImage = computed(() => !!copyScript.value.trim() && !imaging.value && !drawing.value)
const canProduce = computed(
  () => !!storyboardImage.value && !!templateId.value && !submitting.value,
)

function requireLogin() {
  if (userStore.isLoggedIn) return true
  window.$message?.warning('请先登录后再创作')
  userStore.openLogin()
  return false
}

// 生成强 Hook 带货脚本:走统一技能流 text-generation(worker 模型网关调用),
// 商品名作标题、卖点作分类,产出大标题/副标题/口播。结果形态与旧 /copy/* 一致。
async function writeScript() {
  if (!canWrite.value) return
  writing.value = true
  try {
    const { status, data } = await runCopy({
      template_title: productName.value.trim(),
      category: sellingPoints.value.trim(),
      with_demand: false,
    })
    if (status === 'done' && data?.content) {
      const c = data.content
      copyTitle.value = c.title || copyTitle.value
      copySubtitle.value = c.subtitle || copySubtitle.value
      copyScript.value = c.script || copyScript.value
      window.$message?.success('已生成带货脚本,可修改后生成分镜图')
    } else if (status === 'error') {
      window.$message?.error(skillError.value || '带货脚本生成失败,请重试')
    }
  } catch (e) { /* 拦截器已提示 */ }
  finally { writing.value = false }
}

// 从口播生成英文图片提示词:走统一技能流 image-generation(worker 的 image-generation 技能资产)。
// 风格描述(可选)会经 style_conversion 转英文前缀拼到每条提示词前。结果可直接作为分镜图提示词。
async function writeImagePrompt() {
  if (!copyScript.value.trim() || prompting.value) return
  prompting.value = true
  try {
    const { status, data } = await runImagePrompt({
      narrations: [copyScript.value.trim()],
      style: promptStyle.value.trim() || undefined,
    })
    if (status === 'done' && data?.content) {
      const list = Array.isArray(data.content) ? data.content : []
      imagePromptText.value = list.join('\n\n')
      if (imagePromptText.value) window.$message?.success('已生成英文图片提示词,已自动作为下方分镜图提示词')
    } else if (status === 'error') {
      window.$message?.error(skillError.value || '图片提示词生成失败,请重试')
    }
  } catch (e) { /* 拦截器已提示 */ }
  finally { prompting.value = false }
}

// 上传已有九宫格图(链路 03:九宫格直投)
async function uploadStoryboard({ file, onFinish, onError, onProgress }) {
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    storyboardImage.value = url
    onFinish()
    window.$message?.success('分镜图已上传,可直接出片')
  } catch (e) { onError() }
}

// 生成九宫格分镜图:把商品信息与脚本拼成九宫格分镜板提示词,走图片生成任务
async function generateImage() {
  if (!canGenerateImage.value) return
  if (!requireLogin()) return
  imaging.value = true
  storyboardImage.value = ''
  try {
    // 若已用 AI 生成英文图片提示词,优先用它作为分镜图提示词(直接喂文生图);
    // 否则按商品信息 + 口播手拼九宫格分镜板提示词(原逻辑)
    const prompt = imagePromptText.value.trim() || [
      '3x3 九宫格分镜板,电商带货短视频,统一色调与主体一致性,每格一个镜头',
      `商品:${productName.value.trim()}`,
      sellingPoints.value.trim() ? `卖点:${sellingPoints.value.trim()}` : '',
      copyScript.value.trim() ? `分镜内容:${copyScript.value.trim()}` : '',
    ].filter(Boolean).join(';')
    const res = await api.task.imageCreate.post({
      prompt,
      ratio: '1:1',
      num_images: 1,
      device: device(),
    })
    if (res.code === 1 && res.data?.id) {
      imageTaskId.value = res.data.id
      imageError.value = ''   // 新一轮生成前清空上一轮错误提示
      window.$message?.success('已提交分镜图生成,正在绘制…')
      startPolling()
    }
  } catch (e) { /* 拦截器已提示 */ }
  finally { imaging.value = false }
}

function startPolling() {
  stopPolling()
  drawing.value = true
  pollTimer = setInterval(fetchImage, 2000)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  drawing.value = false
}

// 轮询图片任务:成功即取 result_video(媒体地址),失败则停止并提示
async function fetchImage() {
  if (!imageTaskId.value) return
  try {
    const res = await api.task.detail.post({ id: Number(imageTaskId.value) })
    if (res.code !== 1 || !res.data) {
      // 轮询被拒(未登录/鉴权过期/无权限/任务不存在):无需再重试也不会恢复,
      // 停止轮询并持久提示,否则后台每 2s 打一次被拒请求且界面无任何反馈
      // (提交按钮已在 finally 复位,不处理就会既无转圈也无结果,像"卡死")
      stopPolling()
      imageError.value = res.message || res.msg || '无法获取分镜图进度,请刷新或重新登录后重试'
      return
    }
    const detail = res.data
    if (detail.status === 'success') {
      stopPolling()
      imageError.value = ''
      storyboardImage.value = detail.result_video || ''
      if (storyboardImage.value) window.$message?.success('分镜图已生成,可确认后出片')
      else window.$message?.warning('分镜图生成完成但无结果,请重试')
    } else if (detail.status === 'failed') {
      stopPolling()
      imageError.value = detail.fail_reason || '分镜图生成失败,请稍后重试'
      window.$message?.error(imageError.value)
    }
  } catch (e) { /* 拦截器已提示 */ }
}

async function loadTemplates() {
  try {
    const res = await api.template.list.post({ pageNum: 1, pageSize: 50 })
    if (res.code === 1) {
      templates.value = res.data || []
      if (!templateId.value && templates.value.length) templateId.value = templates.value[0].id
    }
  } catch (e) { /* 拦截器已提示 */ }
}

async function refreshEstimate() {
  if (!templateId.value) return
  await estRefresh('video', { template_id: templateId.value, duration: 0 })
}

// 出片:以九宫格分镜图为素材,脚本作为备注下发给 worker
async function produce() {
  if (!canProduce.value) return
  if (!requireLogin()) return
  submitting.value = true
  try {
    const remark = [copyTitle.value, copySubtitle.value, copyScript.value]
      .filter(Boolean).join('\n')
    await createAndNavigate(
      () => api.task.create.post({
        template_id: Number(templateId.value),
        materials: [storyboardImage.value],
        remark: remark || undefined,
        // 通用创作增强:创意档位 / 开头钩子 / 专家模式(与视频复刻同源,后端按白名单校验)
        creative_level: adv.creativeLevel || undefined,
        hook_boost: adv.hookBoost || undefined,
        asset_override: adv.assetOverride.trim() || undefined,
        device: device(),
      }),
      { message: '已提交出片,正在生成' },
    )
  } catch (e) { /* 拦截器已提示 */ }
  finally { submitting.value = false }
}

onMounted(() => { loadTemplates() })
onBeforeUnmount(() => { stopPolling() })
</script>

<template>
  <div class="storyboard-page">
    <div class="wrap">
      <div class="hero" v-if="!embedded">
        <h1>九宫格出片</h1>
        <p>只需商品信息,自动生成强 Hook 脚本与九宫格分镜图,一键出片(无需对标视频)</p>
      </div>

      <!-- 步骤 1:商品信息 + 脚本 -->
      <section class="card">
        <div class="step"><b>1</b> 商品信息与脚本</div>
        <div class="field">
          <div class="lbl">商品名称 <i class="req">*</i></div>
          <n-input v-model:value="productName" placeholder="例如:便携榨汁杯" />
        </div>
        <div class="field">
          <div class="lbl">卖点 / 行业(选填)</div>
          <n-input v-model:value="sellingPoints" placeholder="例如:一键出汁、USB 充电、随身携带" />
        </div>
        <div class="actions">
          <n-button type="primary" secondary :disabled="!canWrite" :loading="writing" @click="writeScript">
            生成带货脚本
          </n-button>
        </div>
        <div v-if="copyScript || copyTitle" class="field script">
          <div class="lbl">大标题</div>
          <n-input v-model:value="copyTitle" placeholder="大标题" />
          <div class="lbl" style="margin-top:10px">副标题</div>
          <n-input v-model:value="copySubtitle" placeholder="副标题" />
          <div class="lbl" style="margin-top:10px">口播 / 分镜脚本</div>
          <n-input v-model:value="copyScript" type="textarea" :rows="4" placeholder="口播 / 分镜脚本" />
          <div class="actions" style="margin-top:12px">
            <n-input v-model:value="promptStyle" placeholder="风格描述(选填,如:电影感 / 赛博朋克 / 清新日系)" style="max-width:300px" />
            <n-button type="primary" secondary :disabled="!copyScript.trim()" :loading="prompting" @click="writeImagePrompt">
              AI 生成图片提示词
            </n-button>
          </div>
          <div v-if="imagePromptText" class="field" style="margin-top:12px">
            <div class="lbl">AI 英文图片提示词(已自动作为下方分镜图提示词,也可复制保存)</div>
            <n-input v-model:value="imagePromptText" type="textarea" :rows="4" readonly placeholder="生成的英文图片提示词" />
          </div>
        </div>
      </section>

      <!-- 步骤 2:分镜图 -->
      <section class="card">
        <div class="step"><b>2</b> 九宫格分镜图</div>
        <div class="actions">
          <n-button type="primary" :disabled="!canGenerateImage" :loading="imaging" @click="generateImage">
            {{ storyboardImage ? '重新生成分镜图' : '生成九宫格分镜图' }}
          </n-button>
          <n-upload accept="image/*" :show-file-list="false" :custom-request="uploadStoryboard">
            <n-button secondary>上传已有分镜图</n-button>
          </n-upload>
        </div>
        <div v-if="imaging || drawing" class="hint">
          <n-spin size="small" /><span>正在绘制九宫格分镜图…</span>
        </div>
        <div v-else-if="storyboardImage" class="preview">
          <img :src="storyboardImage" alt="九宫格分镜图" />
        </div>
        <div v-else-if="imageError" class="sub" style="color:#ff4d1c;font-weight:600">
          {{ imageError }}（可点击上方按钮重试）
        </div>
        <div class="sub">生成的 9 格分镜将作为出片参考;也可直接上传你已有的九宫格图直投出片</div>
        <div class="sub">
          当前视频供应商不接受真人照片作为成片素材。若分镜图含真人照片，系统会移除该图并仅按文字描述生成非本人角色；如需真人口播，可使用
          <router-link to="/digital">平台数字人形象</router-link>（不是本人克隆），也可改用插画/虚拟形象。
        </div>
      </section>

      <!-- 步骤 3:出片 -->
      <section v-if="storyboardImage" class="card">
        <div class="step"><b>3</b> 出片</div>
        <div class="field">
          <div class="lbl">选择模板</div>
          <n-select
            v-model:value="templateId"
            :options="templates.map(t => ({ label: t.title, value: t.id }))"
            placeholder="选择生成模板"
            @update:value="refreshEstimate"
          />
        </div>
        <AdvancedCreationSettings v-model="adv" :show-replicate="false" />
        <div class="actions">
          <div class="est">{{ estText }}</div>
          <n-button type="primary" :disabled="!canProduce" :loading="submitting" @click="produce">
            生成视频
          </n-button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.storyboard-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding: 24px 16px 48px; }
.wrap { max-width: 720px; margin: 0 auto; }
.hero { text-align: center; margin-bottom: 20px; }
.hero h1 { font-size: 22px; font-weight: 700; margin: 0 0 8px; color: #1a1a1a; }
.hero p { font-size: 13px; color: var(--weak); margin: 0; }
.card { background: #fff; border-radius: var(--radius); padding: 20px; margin-bottom: 16px; }
.step { font-size: 15px; font-weight: 600; color: #1a1a1a; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.step b { display: inline-flex; width: 22px; height: 22px; border-radius: 50%; background: var(--brand); color: #fff; align-items: center; justify-content: center; font-size: 13px; }
.field { margin-bottom: 16px; }
.script { border-top: 1px dashed var(--line); padding-top: 16px; }
.lbl { font-size: 14px; font-weight: 500; margin-bottom: 8px; color: #1a1a1a; }
.req { color: #d03050; font-style: normal; }
.sub { font-size: 12px; color: var(--weak); margin-top: 10px; }
.actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.est { font-size: 13px; color: var(--body-c); margin-left: auto; }
.hint { display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--body-c); margin-top: 14px; }
.preview { margin-top: 14px; }
.preview img { max-width: 260px; width: 100%; border-radius: 10px; border: 1px solid var(--line); display: block; }
</style>
