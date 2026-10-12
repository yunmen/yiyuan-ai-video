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
const { runCopy, runImagePrompt, error: skillError, qualityWarn } = useSkill()
// 被「创作工作台」内嵌时(route 以 /studio 开头),隐藏本页独立大标题,避免与工作台 Hero 重复
const embedded = computed(() => route.path.startsWith('/studio'))
const { estText, refresh: estRefresh } = useTaskEstimate()
const { createAndNavigate, submitHint } = useTaskCreate()

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

// 步骤 1 附:AI 中文图片提示词(从口播生成,可直接用于文生图)
const imagePromptText = ref('')   // 生成的中文图片提示词(可多条,换行分隔)
const promptStyle = ref('')       // 风格描述(可选,直接作为前缀拼到每条提示词前)
const prompting = ref(false)

// —— 步骤 2:逐镜分镜图(每镜一张图;出片时每张独立成段再拼接)——
const storyboardImage = ref('')   // 单图直投(上传已有分镜图,不走逐镜)
const shotCount = ref(6)          // 分镜数:4/6/9(带货片 4-6 镜最划算,9 镜偏长)
const perShotSeconds = ref(5)     // 逐镜每段时长(秒),成片总时长 = 镜数 × 每段
const shots = ref([])             // [{ index, prompt, taskId, status, url }]
const imaging = ref(false)
const drawing = ref(false)        // 轮询中(分镜图后台生成)
const imageError = ref('')        // 轮询被拒(鉴权过期/无权限等)时的持久提示

let pollTimer = null

// —— 步骤 3:出片 ——
const templates = ref([])
const templateId = ref(null)
const submitting = ref(false)

const device = () => (window.innerWidth <= 768 ? 'mobile' : 'desktop')
const canWrite = computed(() => !!productName.value.trim() && !writing.value)
const canGenerateImage = computed(() => !!copyScript.value.trim() && !imaging.value && !drawing.value)
// 已就绪的分镜图(出片素材):逐镜模式要求至少 2 张才分段,否则用单图直投
const shotUrls = computed(() => shots.value.filter(s => s.url).map(s => s.url))
const canProduce = computed(
  () => (shotUrls.value.length >= 2 || !!storyboardImage.value) && !submitting.value,
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

// 从口播生成中文图片提示词:走统一技能流 image-generation(worker 的 image-generation 技能资产)。
// 风格描述(可选)会直接作为前缀拼到每条提示词前。结果可直接作为分镜图提示词。
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
      if (imagePromptText.value) window.$message?.success('已生成图片提示词,已自动作为下方分镜图提示词')
    } else if (status === 'error') {
      window.$message?.error(skillError.value || '图片提示词生成失败,请重试')
    }
  } catch (e) { /* 拦截器已提示 */ }
  finally { prompting.value = false }
}

// 上传单图直投:上传已有分镜图作为整图直投素材,走原链路出片(不走逐镜)
async function uploadStoryboard({ file, onFinish, onError, onProgress }) {
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    storyboardImage.value = url
    onFinish()
    window.$message?.success('已上传单图,可确认后出片')
  } catch (e) { onError() }
}

// 逐镜提示词:优先用 AI 生成的图片提示词(按空行拆分,一条一镜);
// 不足镜数时用最后一条 / 商品信息兜底。逐镜出片的质量取决于「每镜提示词是否各不相同」,
// 因此这里必须逐条给出,而不是把整段口播重复喂给每一镜。
function buildShotPrompts(n) {
  const base = [
    productName.value.trim() ? `商品:${productName.value.trim()}` : '',
    sellingPoints.value.trim() ? `卖点:${sellingPoints.value.trim()}` : '',
    copyScript.value.trim() ? `分镜内容:${copyScript.value.trim()}` : '',
  ].filter(Boolean).join(';')
  const style = promptStyle.value.trim()
  const ai = imagePromptText.value.split(/\n\s*\n/).map((s) => s.trim()).filter(Boolean)
  return Array.from({ length: n }, (_, i) => {
    const desc = ai[i] || ai[ai.length - 1] || base
    return [style, `第 ${i + 1} 镜`, desc].filter(Boolean).join(',')
  })
}

// 生成逐镜分镜图:每镜一张(竖版 9:16),出片时每张独立成段再拼接。
// 为什么不再生成一张 3x3 拼图:拼图喂给视频模型时,模型面对 9 格静态画面只能整格微动,
// 分镜语义全丢;而切格再逐格生成又因单格像素过低(整图约 1/9)必然糊。
async function generateShots() {
  if (!canGenerateImage.value) return
  if (!requireLogin()) return
  imaging.value = true
  imageError.value = ''
  shots.value = []
  try {
    const prompts = buildShotPrompts(Number(shotCount.value))
    // 并发提交(上限 3):一次打满网关容易触发限流,排队提交更稳
    const queue = prompts.map((prompt, index) => ({ prompt, index }))
    const worker = async () => {
      while (queue.length) {
        const item = queue.shift()
        const shot = { index: item.index, prompt: item.prompt, taskId: null, status: 'pending', url: '' }
        shots.value.push(shot)
        try {
          const res = await api.task.imageCreate.post({
            prompt: item.prompt, ratio: '9:16', num_images: 1, device: device(),
          })
          if (res.code === 1 && res.data?.id) shot.taskId = res.data.id
          else shot.status = 'failed'
        } catch (e) { shot.status = 'failed' }
      }
    }
    await Promise.all(Array.from({ length: Math.min(3, prompts.length) }, worker))
    if (!shots.value.some((s) => s.taskId)) {
      window.$message?.error('分镜图提交失败,请重试')
      return
    }
    window.$message?.success(`已提交 ${shots.value.filter((s) => s.taskId).length} 个分镜图任务,正在绘制…`)
    startPolling()
  } catch (e) { /* 拦截器已提示 */ }
  finally { imaging.value = false }
}

function startPolling() {
  stopPolling()
  drawing.value = true
  pollTimer = setInterval(fetchShots, 2500)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  drawing.value = false
}

// 轮询各分镜图任务:成功取 result_video;全部结束(成功或失败)即停止轮询
async function fetchShots() {
  const pending = shots.value.filter((s) => s.taskId && s.status === 'pending')
  for (const shot of pending) {
    try {
      const res = await api.task.detail.post({ id: Number(shot.taskId) })
      if (res.code !== 1 || !res.data) {
        // 被拒(未登录/鉴权过期/任务不存在):再重试也不会恢复,停该格并持久提示
        shot.status = 'failed'
        imageError.value = res.message || res.msg || '无法获取分镜图进度,请刷新或重新登录后重试'
        continue
      }
      const detail = res.data
      if (detail.status === 'success') {
        shot.url = detail.result_video || ''
        shot.status = shot.url ? 'success' : 'failed'
      } else if (detail.status === 'failed') {
        shot.status = 'failed'
        shot.error = detail.fail_reason || '分镜图生成失败'
      }
    } catch (e) { /* 拦截器已提示 */ }
  }
  if (!shots.value.some((s) => s.status === 'pending')) {
    stopPolling()
    refreshEstimate()
    const ok = shotUrls.value.length
    if (ok >= 2) window.$message?.success(`${ok} 张分镜图已就绪,可确认后出片`)
    else window.$message?.warning(`仅 ${ok} 张分镜图成功,至少需要 2 张才能逐镜出片`)
  }
}

async function loadTemplates() {
  try {
    const res = await api.template.list.post({ pageNum: 1, pageSize: 50 })
    if (res.code === 1) {
      templates.value = res.data || []
      // 模板可选:不自动选中第一个,默认"不使用模板"(规格走系统默认)
    }
  } catch (e) { /* 拦截器已提示 */ }
}

async function refreshEstimate() {
  // 逐镜出片:总时长 = 镜数 × 每段(与后端建单计费同源);单图直投按模板/默认时长
  const n = shotUrls.value.length || Number(shotCount.value)
  if (n >= 2) {
    await estRefresh('video', {
      shot_count: n, per_shot_seconds: Number(perShotSeconds.value),
    })
    return
  }
  // 模板可选:未选模板时不带 template_id,按系统默认时长预估
  await estRefresh('video', { template_id: templateId.value || undefined, duration: templateId.value ? 0 : 5 })
}

// 出片:逐镜分镜图 → 每张独立成段 → 拼接(单图时按原链路直投)
async function produce() {
  if (!canProduce.value) return
  if (!requireLogin()) return
  submitting.value = true
  try {
    // 必须带字段前缀并用 ';' 拼接:worker 的 parse_remark 按 "大标题/副标题/口播文案" 别名
    // 解析结构化文案(REMARK_FIELD_MAP),纯换行拼接会被整体归入 extra,口播文案拿不到
    // → 出片提示词缺主体信息、配音与字幕也无内容可用(与 Upload.vue 保持同一约定)
    const remarkParts = []
    if (copyTitle.value.trim()) remarkParts.push(`大标题:${copyTitle.value.trim()}`)
    if (copySubtitle.value.trim()) remarkParts.push(`副标题:${copySubtitle.value.trim()}`)
    if (copyScript.value.trim()) remarkParts.push(`口播文案:${copyScript.value.trim()}`)
    const remark = remarkParts.join(';')
    // 逐镜出片(≥2 张分镜图):每张图独立生成一段再拼接,成片 = 镜数 × 每段时长。
    // 单图时保持原链路(整图直投),老用法不受影响。
    const urls = shotUrls.value.slice(0, 9)
    const perShot = urls.length >= 2
    const ready = perShot ? shots.value.filter((s) => s.url).slice(0, 9) : []
    await createAndNavigate(
      () => api.task.create.post({
        template_id: templateId.value ? Number(templateId.value) : undefined,
        materials: perShot ? urls : [storyboardImage.value],
        shot_mode: perShot ? 'per_shot' : undefined,
        shot_prompts: perShot ? ready.map((s) => s.prompt) : undefined,
        per_shot_seconds: perShot ? Number(perShotSeconds.value) : undefined,
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
        <p>只需商品信息,自动生成强 Hook 脚本与九宫格分镜图,拆成 9 张分镜各自出片并运镜合成一条视频(无需对标视频)</p>
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
        <n-alert v-if="qualityWarn" type="warning" :title="'内容质量提示'" style="margin-top:8px">{{ qualityWarn }}</n-alert>
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
            <div class="lbl">AI 中文图片提示词(已自动作为下方分镜图提示词,也可复制保存)</div>
            <n-input v-model:value="imagePromptText" type="textarea" :rows="4" readonly placeholder="生成的中文图片提示词" />
          </div>
        </div>
      </section>

      <!-- 步骤 2:逐镜分镜图 -->
      <section class="card">
        <div class="step"><b>2</b> 逐镜分镜图</div>
        <div class="actions">
          <div class="lbl" style="margin:0">分镜数</div>
          <n-select
            v-model:value="shotCount"
            :options="[4, 6, 9].map(n => ({ label: `${n} 镜`, value: n }))"
            style="width:120px"
          />
          <n-button type="primary" :disabled="!canGenerateImage" :loading="imaging" @click="generateShots">
            {{ shots.length ? '重新生成分镜图' : '生成逐镜分镜图' }}
          </n-button>
          <n-upload accept="image/*" :show-file-list="false" :custom-request="uploadStoryboard">
            <n-button secondary>上传单图直投</n-button>
          </n-upload>
        </div>
        <div v-if="shots.length" class="shot-grid">
          <div v-for="s in shots" :key="s.index" class="shot">
            <template v-if="s.url">
              <img :src="s.url" :alt="`第 ${s.index + 1} 镜`" />
              <span class="idx">{{ s.index + 1 }}</span>
            </template>
            <div v-else class="ph">
              <n-spin v-if="s.status === 'pending'" size="small" />
              <span v-else-if="s.status === 'failed'" class="fail">失败</span>
              <span v-else class="idx">{{ s.index + 1 }}</span>
            </div>
          </div>
        </div>
        <div v-else-if="imaging || drawing" class="hint">
          <n-spin size="small" /><span>正在提交分镜图任务…</span>
        </div>
        <div v-else-if="storyboardImage" class="preview">
          <img :src="storyboardImage" alt="单图直投分镜图" />
        </div>
        <div v-else-if="imageError" class="sub" style="color:var(--brand);font-weight:600">
          {{ imageError }}（可点击上方按钮重试）
        </div>
        <div class="sub">
          每张分镜图会**独立生成一段视频**再拼接成片（逐镜出片）：镜头语义清晰、每格全分辨率，
          优于「整张九宫格拼图直接生成」。镜数越多成片越长、消耗越高。
        </div>
        <div class="sub">
          当前视频供应商不接受真人照片作为成片素材。若分镜图含真人照片，系统会移除该图并仅按文字描述生成非本人角色；如需真人口播，可使用
          <router-link to="/digital">平台数字人形象</router-link>（不是本人克隆），也可改用插画/虚拟形象。
        </div>
      </section>

      <!-- 步骤 3:出片 -->
      <section v-if="shotUrls.length || storyboardImage" class="card">
        <div class="step"><b>3</b> 出片</div>
        <div v-if="shotUrls.length >= 2" class="field">
          <div class="lbl">每段时长</div>
          <n-select
            v-model:value="perShotSeconds"
            :options="[3, 5, 10].map(n => ({ label: `${n} 秒/镜（共约 ${shotUrls.length * n} 秒）`, value: n }))"
            style="max-width:280px"
            @update:value="refreshEstimate"
          />
        </div>
        <div class="field">
          <div class="lbl">选择模板(可选)</div>
          <n-select
            v-model:value="templateId"
            :options="templates.map(t => ({ label: t.title, value: t.id }))"
            placeholder="不使用模板,按系统默认规格出片"
            clearable
            @update:value="refreshEstimate"
          />
        </div>
        <AdvancedCreationSettings v-model="adv" :show-replicate="false" />
        <div class="actions">
          <div class="est">{{ estText }}</div>
          <n-button type="primary" :disabled="!canProduce" :loading="submitting" @click="produce">
            {{ submitting ? submitHint : '生成视频' }}
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
.hero h1 { font-size: 22px; font-weight: 700; margin: 0 0 8px; color: var(--ink); }
.hero p { font-size: 13px; color: var(--weak); margin: 0; }
.card { background: #fff; border-radius: var(--radius); padding: 20px; margin-bottom: 16px; }
.step { font-size: 15px; font-weight: 600; color: var(--ink); margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.step b { display: inline-flex; width: 22px; height: 22px; border-radius: 50%; background: var(--brand); color: #fff; align-items: center; justify-content: center; font-size: 13px; }
.field { margin-bottom: 16px; }
.script { border-top: 1px dashed var(--line); padding-top: 16px; }
.lbl { font-size: 14px; font-weight: 500; margin-bottom: 8px; color: var(--ink); }
.req { color: var(--danger); font-style: normal; }
.sub { font-size: 12px; color: var(--weak); margin-top: 10px; }
.actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.est { font-size: 13px; color: var(--body-c); margin-left: auto; }
.hint { display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--body-c); margin-top: 14px; }
.preview { margin-top: 14px; }
.preview img { max-width: 260px; width: 100%; border-radius: var(--radius-sm); border: 1px solid var(--line); display: block; }
/* 逐镜分镜图网格 */
.shot-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 14px; }
.shot { position: relative; aspect-ratio: 9 / 16; border-radius: var(--radius-sm); overflow: hidden; background: var(--bg); border: 1px solid var(--line); }
.shot img { width: 100%; height: 100%; object-fit: cover; display: block; }
.shot .ph { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f5f7; }
.shot .idx { position: absolute; left: 6px; top: 6px; min-width: 20px; height: 20px; padding: 0 6px; border-radius: 10px; background: rgba(0,0,0,.55); color: #fff; font-size: 12px; display: flex; align-items: center; justify-content: center; }
.shot .fail { font-size: 12px; color: var(--danger); }
</style>
