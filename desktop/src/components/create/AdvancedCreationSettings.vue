<script setup>
// 高级创作设置面板(可复用):复刻模式 / 替换意图 / 复刻形态 / 主角表现 / 创意档位 / 开头钩子 / 专家模式。
// 选项全部来自后端 /gen-config(单一来源),前端不另存白名单副本,避免“前端能选、后端校验不过”的漂移。
// 通过 v-model 绑定一个 settings 对象:{ mode, intent, format, leadAct, creativeLevel, hookBoost, assetOverride }。
// 复刻相关控件由 showReplicate 控制(仅“视频复刻”链路使用);创意档位 / 钩子 / 专家模式为通用创作旋钮,
// 由 showGeneric 控制(九宫格、模板替换等也复用,让这些功能在所有生成入口一致呈现)。
import { computed, ref } from 'vue'
import { useGenConfig } from '@/composables/useGenConfig'

// 顶层「复刻方式」:名字即能力、不留歧义(原名"完全复刻"字面像"照抄",与下方"替换意图"冲突)。
// - 换元素复刻:保留原片结构,替换你指定的人/货/景(大多数用户第一需求);
// - 原样照搬:不替换任何元素,原样复制(对应后端 mode=full 的忠实复刻语义);
// - 爆款改写:按爆款逻辑重塑表演与节奏。
const REPLICATE_MODES = [
  { key: 'replace', label: '换元素复刻', desc: '保留原片结构,替换你指定的人 / 货 / 景' },
  { key: 'full', label: '原样照搬', desc: '不替换任何元素,原样复制视频,无需上传参考图' },
  { key: 'viral', label: '爆款改写', desc: '按爆款逻辑重塑表演与节奏' },
]
const ASSET_OVERRIDE_MAX = 500

const props = defineProps({
  // 是否展示“复刻专属”控件(复刻模式 / 替换意图 / 形态 / 主角表现)
  showReplicate: { type: Boolean, default: true },
  // 是否展示通用创作旋钮(创意档位 / 开头钩子 / 专家模式)
  showGeneric: { type: Boolean, default: true },
})
const settings = defineModel({ type: Object, required: true })

const cfg = useGenConfig()
// 平台用户多为不调参的小白:全部旋钮默认折叠,主链路只剩「上传素材 → 生成」。
// 专业用户展开后仍可精细控制(复刻模式/意图/形态/主角表现/档位/钩子/专家模式)。
const collapsed = ref(true)

// 已选意图的人话说明:未选则提示按上传素材类型自动替换
const intentHint = computed(() => {
  const picked = cfg.replicateIntents.filter((i) => settings.value.intent.includes(i.key))
  if (!picked.length) return '未手动选择替换意图:将按你上传素材标注的类型(产品/人物/场景)自动替换对应元素'
  return '已选「' + picked.map((i) => i.label).join('、') + '」——' + picked.map((i) => i.desc).join(';')
})
const formatHint = computed(() => {
  const picked = cfg.replicateFormats.find((f) => f.key === settings.value.format)
  return picked ? `已选「${picked.label}」——${picked.desc}` : '未指定形态:将完整沿用原片的结构与节奏'
})
const leadActHint = computed(() => {
  const picked = cfg.leadActs.find((a) => a.key === settings.value.leadAct)
  return picked ? `已选「${picked.label}」——${picked.desc}` : '未指定:新主角将完整复演原片人物的动作与反应(原片的情节与镜头都会保留)'
})
const creativeHint = computed(() => {
  const picked = cfg.creativeLevels.find((c) => c.key === settings.value.creativeLevel)
  return picked ? `已选「${picked.label}」——${picked.desc}` : '未指定:保留原片的镜头结构与节奏,只替换你指定的元素'
})
const hookHint = computed(() => {
  const picked = cfg.hookBoosts.find((h) => h.key === settings.value.hookBoost)
  return picked ? `已选「${picked.label}」——${picked.desc}` : '未指定:开头与其余镜头保持一致'
})

// 单选芯片:再点一次即取消(回到“跟随原片/不指定”)
function onModeChange(key) {
  settings.value.mode = key
  if (key === 'full') {
    // 原片克隆:忠实复刻,清空所有改写旋钮(即便后端列表已隐藏,值也要归位避免脏下发)
    settings.value.creativeLevel = 'faithful'
    settings.value.intent = []
    settings.value.format = ''
    settings.value.hookBoost = ''
    settings.value.assetOverride = ''
    settings.value.leadAct = ''
  } else if (key === 'replace') {
    // 完全复刻:保留原片结构与运镜(忠实档),主角表现留空=跟随原片;
    // 替换维度由用户上传图标注的 image_roles 决定,这里不强行清空 intent
    settings.value.creativeLevel = 'faithful'
    settings.value.format = ''
    settings.value.hookBoost = ''
    settings.value.assetOverride = ''
    settings.value.leadAct = ''
  } else if (key === 'viral') {
    // 爆款改写:预选爆款档,用户在改写幅度里仍可改;
    // 该模式参考图只作风格/运镜参考,绝不替换元素,因此清空替换意图与主角表现,避免脏值下发/误判
    settings.value.intent = []
    settings.value.leadAct = ''
    if (!settings.value.creativeLevel) settings.value.creativeLevel = 'viral'
  }
}
function toggleIntent(key) {
  settings.value.intent = settings.value.intent.includes(key)
    ? settings.value.intent.filter((k) => k !== key)
    : [...settings.value.intent, key]
}
function toggleFormat(key) { settings.value.format = settings.value.format === key ? '' : key }
function toggleLeadAct(key) { settings.value.leadAct = settings.value.leadAct === key ? '' : key }
function toggleCreative(key) { settings.value.creativeLevel = settings.value.creativeLevel === key ? '' : key }
function toggleHookBoost(key) { settings.value.hookBoost = settings.value.hookBoost === key ? '' : key }
</script>

<template>
  <div class="adv-settings">
    <!-- 复刻方式:顶层选择,默认常驻可见;用户第一眼就能选,不必进“更多设置” -->
    <template v-if="showReplicate">
      <div class="field mode-field">
        <div class="lbl">复刻方式</div>
        <div class="chips">
          <span
            v-for="m in REPLICATE_MODES"
            :key="m.key"
            :title="m.desc"
            :class="['chip', { on: settings.mode === m.key }]"
            @click="onModeChange(m.key)"
          >{{ m.label }}</span>
        </div>
        <div class="intent-hint">{{ (REPLICATE_MODES.find((m) => m.key === settings.mode) || {}).desc }}</div>
      </div>
      <!-- 替换意图:换元素复刻的核心动作,从“更多设置”提出来常驻展示,小白无需展开即可选 -->
      <div v-if="cfg.replicateIntents.length && settings.mode === 'replace'" class="field">
        <div class="lbl">替换意图</div>
        <div class="chips">
          <span
            v-for="it in cfg.replicateIntents"
            :key="it.key"
            :title="it.desc"
            :class="['chip', { on: settings.intent.includes(it.key) }]"
            @click="toggleIntent(it.key)"
          >{{ it.label }}</span>
        </div>
        <div class="intent-hint">{{ intentHint }}</div>
      </div>
    </template>
    <!-- 其余旋钮默认折叠:小白无需调参,专业用户展开后仍有完整控制 -->
    <div class="adv-head" @click="collapsed = !collapsed">
      <span class="lbl-inline">更多设置(可选)</span>
      <span class="caret">{{ collapsed ? '展开' : '收起' }}</span>
    </div>
    <div v-if="!collapsed" class="adv-body">
    <!-- 复刻专属控件 -->
    <template v-if="showReplicate">
      <!-- 主角表现(创意增强):仅“换人物”时出现 -->
      <div v-if="settings.intent.includes('person') && cfg.leadActs.length && settings.mode === 'replace'" class="field">
        <div class="lbl">主角怎么演</div>
        <div class="chips">
          <span
            v-for="la in cfg.leadActs"
            :key="la.key"
            :title="la.desc"
            :class="['chip', { on: settings.leadAct === la.key }]"
            @click="toggleLeadAct(la.key)"
          >{{ la.label }}</span>
        </div>
        <div class="intent-hint">{{ leadActHint }}</div>
      </div>

      <!-- 复刻目标形态:决定成片的内容结构;非换元素复刻时展示 -->
      <div v-if="cfg.replicateFormats.length && settings.mode !== 'full'" class="field">
        <div class="lbl">复刻成什么形态</div>
        <div class="chips">
          <span
            v-for="fm in cfg.replicateFormats"
            :key="fm.key"
            :title="fm.desc"
            :class="['chip', { on: settings.format === fm.key }]"
            @click="toggleFormat(fm.key)"
          >{{ fm.label }}</span>
        </div>
        <div class="intent-hint">{{ formatHint }}</div>
      </div>

      <!-- 创意档位:仅爆款改写模式展示 -->
      <div v-if="cfg.creativeLevels.length && settings.mode === 'viral'" class="field">
        <div class="lbl">改写幅度</div>
        <div class="chips">
          <span
            v-for="cl in cfg.creativeLevels"
            :key="cl.key"
            :title="cl.desc"
            :class="['chip', { on: settings.creativeLevel === cl.key }]"
            @click="toggleCreative(cl.key)"
          >{{ cl.label }}</span>
        </div>
        <div class="intent-hint">{{ creativeHint }}</div>
      </div>

      <!-- 开头钩子强化:仅爆款改写模式展示 -->
      <div v-if="cfg.hookBoosts.length && settings.mode === 'viral'" class="field">
        <div class="lbl">开头钩子</div>
        <div class="chips">
          <span
            v-for="hb in cfg.hookBoosts"
            :key="hb.key"
            :title="hb.desc"
            :class="['chip', { on: settings.hookBoost === hb.key }]"
            @click="toggleHookBoost(hb.key)"
          >{{ hb.label }}</span>
        </div>
        <div class="intent-hint">{{ hookHint }}</div>
      </div>

      <!-- 专家模式:追加一条只作用于本次任务的要求;非换元素复刻模式展示 -->
      <div class="field" v-if="settings.mode !== 'full'">
        <div class="expert-head" @click="settings.showExpert = !settings.showExpert">
          <span class="lbl-inline">专家模式(可选)</span>
          <span class="caret">{{ settings.showExpert ? '收起' : '展开' }}</span>
        </div>
        <div v-if="settings.showExpert" class="expert-body">
          <div class="sub">追加一条只作用于本次任务的要求(例如“全程不要出现英文字幕”)。它会排在档位要求之后,优先级更高;留空则只按上面的档位执行。</div>
          <n-input
            v-model:value="settings.assetOverride"
            type="textarea"
            :rows="3"
            :maxlength="ASSET_OVERRIDE_MAX"
            show-count
            placeholder="只作用于本次任务的要求(选填)"
          />
        </div>
      </div>
    </template>

    <!-- 通用创作旋钮(九宫格 / 模板替换等链路复用):复刻链路已由上方“复刻专属”块按模式展示,
         此处仅在非复刻链路(showReplicate=false)渲染,避免创意档位/钩子/专家模式重复出现 -->
    <template v-if="showGeneric && !showReplicate">
      <div v-if="cfg.creativeLevels.length" class="field">
        <div class="lbl">创意档位</div>
        <div class="chips">
          <span
            v-for="cl in cfg.creativeLevels"
            :key="cl.key"
            :title="cl.desc"
            :class="['chip', { on: settings.creativeLevel === cl.key }]"
            @click="toggleCreative(cl.key)"
          >{{ cl.label }}</span>
        </div>
        <div class="intent-hint">{{ creativeHint }}</div>
      </div>

      <div v-if="cfg.hookBoosts.length" class="field">
        <div class="lbl">开头钩子</div>
        <div class="chips">
          <span
            v-for="hb in cfg.hookBoosts"
            :key="hb.key"
            :title="hb.desc"
            :class="['chip', { on: settings.hookBoost === hb.key }]"
            @click="toggleHookBoost(hb.key)"
          >{{ hb.label }}</span>
        </div>
        <div class="intent-hint">{{ hookHint }}</div>
      </div>

      <div class="field">
        <div class="expert-head" @click="settings.showExpert = !settings.showExpert">
          <span class="lbl-inline">专家模式(可选)</span>
          <span class="caret">{{ settings.showExpert ? '收起' : '展开' }}</span>
        </div>
        <div v-if="settings.showExpert" class="expert-body">
          <div class="sub">追加一条只作用于本次任务的要求(例如“全程不要出现英文字幕”)。它会排在档位要求之后,优先级更高;留空则只按默认执行。</div>
          <n-input
            v-model:value="settings.assetOverride"
            type="textarea"
            :rows="3"
            :maxlength="ASSET_OVERRIDE_MAX"
            show-count
            placeholder="只作用于本次任务的要求(选填)"
          />
        </div>
      </div>
    </template>
    </div>
  </div>
</template>

<style scoped>
.adv-settings { display: flex; flex-direction: column; }
/* 顶部“复刻方式”与下方“更多设置”折叠头之间留出分隔,避免两段控件挤在一起 */
.mode-field { margin-bottom: 16px; }
/* 折叠头:整行可点击,默认收起(小白不调参) */
.adv-head { display: flex; align-items: center; justify-content: space-between; cursor: pointer; margin-bottom: 8px; }
.adv-body { border: 1px dashed var(--line); border-radius: 8px; padding: 12px; }
.field { margin-bottom: 18px; }
.field:last-child { margin-bottom: 0; }
.lbl { font-size: 14px; font-weight: 500; margin-bottom: 8px; color: #1a1a1a; }
.intent-hint { font-size: 12px; color: var(--weak); margin-top: 8px; line-height: 1.5; }
.sub { font-size: 12px; color: var(--weak); margin-top: 8px; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { padding: 7px 16px; border-radius: 18px; background: var(--bg); font-size: 13px; color: var(--body-c); cursor: pointer; border: 1.5px solid transparent; user-select: none; }
.chip.on { background: var(--brand-bg); color: var(--brand); border-color: var(--brand); font-weight: 600; }
/* 小屏:芯片组改单行横向滑动,避免“复刻模式”等短选项被挤成两行,同时保持选项完整可见 */
@media (max-width: 768px) {
  .chips {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 2px;
    -webkit-overflow-scrolling: touch;
  }
  .chips::-webkit-scrollbar { display: none; }
  .chips { scrollbar-width: none; }
  .chip { flex: 0 0 auto; white-space: nowrap; padding: 7px 14px; }
}
/* 专家模式折叠头:整行可点击展开,默认收起 */
.expert-head { display: flex; align-items: center; justify-content: space-between; cursor: pointer; margin-bottom: 8px; }
.lbl-inline { font-size: 14px; font-weight: 500; color: #1a1a1a; }
.expert-head .caret { font-size: 12px; color: var(--brand); }
.expert-body { border: 1px dashed var(--line); border-radius: 8px; padding: 10px; }
</style>
