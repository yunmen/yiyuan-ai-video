<script setup>
// 文案去味:长文去 AI 味改写工具(创作工具箱独立页)。
// 调用 useSkill.runRewrite → 后端 /content/rewrite(映射 worker text-rewrite 技能)→ 轮询 /content/result。
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSkill } from '@/composables/useSkill'

const router = useRouter()
const { loading, result, error, status, runRewrite } = useSkill()

// 原文(≤3000 字)
const source = ref('')
const MAX = 3000
const srcLen = computed(() => (source.value || '').length)
const overLimit = computed(() => srcLen.value > MAX)

// 改写档位 Mark I–IV(强度递增)
const LEVELS = [
  { value: 1, label: 'Mark I', desc: '轻度·仅微调表达' },
  { value: 2, label: 'Mark II', desc: '中度·重述句子' },
  { value: 3, label: 'Mark III', desc: '重度·重构段落' },
  { value: 4, label: 'Mark IV', desc: '深度·大幅口语化' },
]
const level = ref(2)

// 语气
const TONES = [
  { label: '自然', value: 'natural' },
  { label: '正式', value: 'formal' },
  { label: '亲切', value: 'friendly' },
  { label: '犀利', value: 'sharp' },
  { label: '幽默', value: 'humorous' },
]
const tone = ref('natural')

// 档位下拉选项(带强度说明,替代原四宫格卡片)
const levelOptions = computed(() =>
  LEVELS.map((lv) => ({ label: `${lv.label}(${lv.desc})`, value: lv.value }))
)
// 当前语气中文名(结果区脚注展示用)
const toneLabel = computed(() => {
  const hit = TONES.find((t) => t.value === tone.value)
  return hit ? hit.label : ''
})

// 产物(标准 ToolResult.content)
const rewritten = computed(() => (result.value && result.value.rewritten) || '')
const dstLen = computed(() => (result.value && result.value.dst_chars) || 0)
const fallback = computed(() => !!(result.value && result.value.fallback))
const note = computed(() => (result.value && result.value.note) || '')
const pending = computed(() => status.value === 'pending' || loading.value)

async function doRewrite() {
  if (!source.value.trim()) {
    window.$message?.warning('请先粘贴需要去 AI 味的原文')
    return
  }
  if (overLimit.value) {
    window.$message?.warning(`原文不能超过 ${MAX} 字`)
    return
  }
  const res = await runRewrite({
    text: source.value,
    level: level.value,
    tone: tone.value,
  })
  if (res.status === 'error') {
    window.$message?.error(error.value || '改写失败,请稍后重试')
  } else if (res.status === 'timeout' || res.status === 'not_found') {
    window.$message?.warning('改写超时,请稍后重试')
  } else if (rewritten.value) {
    window.$message?.success('去 AI 味完成')
  }
}

function clearAll() {
  source.value = ''
  result.value = null
}

async function copyResult() {
  if (!rewritten.value) return
  try {
    await navigator.clipboard.writeText(rewritten.value)
    window.$message?.success('已复制到剪贴板')
  } catch (e) {
    window.$message?.error('复制失败,请手动选择文本复制')
  }
}

// 移动端顶部栏返回:优先回退历史;直接访问(无历史)时回到创作页,避免直接退出应用
function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/studio')
}
</script>

<template>
  <div class="ai-flavor">
    <!-- 移动端顶部返回栏(设计稿 header):返回箭头 + 居中标题;桌面端由 AppHeader 接管,此处隐藏 -->
    <header class="page-head">
      <button class="ph-back" type="button" aria-label="返回" @click="goBack">
        <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <h1 class="ph-title">文案去味</h1>
      <span class="ph-right"></span>
    </header>

    <main class="af-main">
      <!-- 副标题说明 -->
      <p class="af-sub">一键去除 AI 味，让文案更自然更像人写的</p>

      <div class="af-grid">
        <!-- 左列:输入区 / 选择风格 / 去味强度 / 去味按钮 -->
        <section class="af-col">
          <!-- 输入区:原文文本域 + 字数统计 -->
          <div class="af-card">
            <div class="af-card-head">
              <span class="af-card-label">输入文案</span>
              <span class="af-count" :class="{ on: overLimit }">{{ srcLen }} / {{ MAX }} 字</span>
            </div>
            <n-input
              v-model:value="source"
              type="textarea"
              placeholder="粘贴你要去味的 AI 文案…"
              :autosize="{ minRows: 8, maxRows: 16 }"
              class="af-input"
            />
            <div class="af-input-foot">
              <n-button text size="small" @click="clearAll">清空</n-button>
            </div>
          </div>

          <!-- 选择风格(语气调性) -->
          <div class="af-block">
            <h3 class="af-block-title">选择风格</h3>
            <div class="af-chips">
              <button
                v-for="t in TONES"
                :key="t.value"
                type="button"
                class="chip"
                :class="{ on: tone === t.value }"
                @click="tone = t.value"
              >{{ t.label }}</button>
            </div>
          </div>

          <!-- 去味强度(改写档位,强度递增) -->
          <div class="af-block">
            <h3 class="af-block-title">去味强度</h3>
            <div class="af-intensity">
              <button
                v-for="lv in LEVELS"
                :key="lv.value"
                type="button"
                class="intensity-btn"
                :class="{ on: level === lv.value }"
                @click="level = lv.value"
              >
                <span class="intensity-dot"></span>
                <span class="intensity-label">{{ lv.label }}</span>
                <span class="intensity-desc">{{ lv.desc }}</span>
              </button>
            </div>
          </div>

          <!-- 主操作:一键去味 -->
          <button
            type="button"
            class="btn btn-primary af-run"
            :disabled="!source.trim() || overLimit || pending"
            @click="doRewrite"
          >
            <svg v-if="pending" class="af-ico af-spin" viewBox="0 0 24 24" width="20" height="20"
              fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            <svg v-else class="af-ico" viewBox="0 0 24 24" width="20" height="20"
              fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M15 4V2" /><path d="M15 16v-2" /><path d="M8 9h2" /><path d="M20 9h2" />
              <path d="M17.8 11.8 19 13" /><path d="M15 9h0" /><path d="M17.8 6.2 19 5" />
              <path d="M3 21l9-9" /><path d="M12.2 6.2 11 5" />
            </svg>
            <span>{{ pending ? '去味中…' : '一键去味' }}</span>
          </button>
        </section>

        <!-- 右列:去味结果(桌面端与左列并排;移动端位于按钮下方) -->
        <section class="af-card af-result-card">
          <div class="af-card-head">
            <span class="af-card-label">去味结果</span>
            <div class="af-result-ops">
              <button v-if="rewritten" type="button" class="af-op af-op-copy" @click="copyResult">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor"
                  stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
                <span>复制</span>
              </button>
              <button
                v-if="rewritten"
                type="button"
                class="af-op af-op-regen"
                :disabled="pending"
                @click="doRewrite"
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor"
                  stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M23 4v6h-6" /><path d="M1 20v-6h6" />
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10" />
                  <path d="M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                </svg>
                <span>重新生成</span>
              </button>
            </div>
          </div>
          <div class="af-result">
            <n-empty v-if="!rewritten && !pending" description="改写好的文案会出现在这里" class="af-empty">
              <template #extra>
                <span class="af-empty-hint">粘贴原文,点击「一键去味」即可。</span>
              </template>
            </n-empty>
            <n-spin v-else-if="pending && !rewritten" size="large" class="af-empty" />
            <template v-else>
              <div class="af-result-text">{{ rewritten }}</div>
              <div v-if="fallback" class="af-note">⚠ {{ note || '已做基础去套话处理(非智能改写)' }}</div>
            </template>
          </div>
          <div class="af-result-foot">
            <span v-if="rewritten">{{ toneLabel }}改写 · {{ dstLen }} 字</span>
            <span v-else class="af-foot-placeholder">等待改写…</span>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.ai-flavor {
  min-height: 100%;
  background: var(--bg);
}
/* 内容容器:移动端贴边单列,桌面端居中并放宽到 page-max */
.af-main {
  max-width: var(--page-max);
  margin: 0 auto;
  /* 底部预留底部导航(60px)+ 安全区高度,避免内容被遮挡 */
  padding: var(--s-5) var(--s-4) calc(var(--nav-h) + var(--s-6) + env(safe-area-inset-bottom));
}
.af-sub {
  margin: 0 0 var(--s-5);
  font-size: 14px;
  color: var(--body-c);
  line-height: 1.6;
}

/* 布局:移动端单列,桌面端左输入 / 右结果两列 */
.af-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--s-4);
}
.af-col {
  display: flex;
  flex-direction: column;
  gap: var(--s-4);
  min-width: 0;
}

/* 卡片:与设计稿一致的圆角白卡 */
.af-card {
  background: var(--bg-card);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--s-4);
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.af-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-2);
  margin-bottom: var(--s-3);
}
.af-card-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}
.af-count {
  font-size: 12px;
  font-weight: 500;
  color: var(--weak);
}
.af-count.on { color: var(--danger); }

/* 输入文本域:去边框、透明底色,直接落在卡片上 */
.af-input :deep(.n-input) {
  background-color: transparent;
  padding: 0;
}
.af-input :deep(.n-input-wrapper) { padding: 0; }
.af-input :deep(.n-input__textarea-el) {
  padding: 0;
  font-size: 14px;
  line-height: 1.8;
  color: var(--ink);
  background: transparent;
}
.af-input :deep(.n-input__border),
.af-input :deep(.n-input__state-border) { display: none; }
.af-input-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--s-2);
}

/* 分区块标题(风格 / 强度) */
.af-block { min-width: 0; }
.af-block-title {
  margin: 0 0 var(--s-3);
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}
.af-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s-2);
}
/* 风格芯片直接落在页面底色上:改用白底 + 描边,保证可见并与设计稿一致 */
.af-chips .chip {
  background: var(--bg-card);
  border-color: var(--line);
}
.af-chips .chip.on {
  background: var(--brand-bg);
  border-color: var(--brand);
  color: var(--brand);
}

/* 去味强度:可点选按钮组(移动端 2 列,桌面端 4 列) */
.af-intensity {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--s-3);
}
.intensity-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--s-1);
  padding: var(--s-3) var(--s-2);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  border: 1px solid var(--line);
  color: var(--body-c);
  cursor: pointer;
  text-align: center;
  transition: all var(--transition-fast);
}
.intensity-btn.on {
  border-color: var(--brand);
  background: var(--brand-bg);
}
.intensity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-medium);
  transition: background var(--transition-fast);
}
.intensity-btn.on .intensity-dot { background: var(--grad-brand); }
.intensity-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-3);
}
.intensity-btn.on .intensity-label { color: var(--brand); }
.intensity-desc {
  font-size: 11px;
  color: var(--weak);
}
.intensity-btn.on .intensity-desc { color: var(--brand-400); }

/* 主按钮:全宽品牌渐变,与设计稿一致(h-14) */
.af-run {
  width: 100%;
  height: 56px;
  font-size: 16px;
  border-radius: var(--radius-pill);
}
.af-ico { flex: none; }
.af-spin { animation: af-rotate 1s linear infinite; }
@keyframes af-rotate {
  to { transform: rotate(360deg); }
}

/* 结果区 */
.af-result-card { min-height: 0; }
.af-result-ops {
  display: flex;
  align-items: center;
  gap: var(--s-2);
}
.af-op {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border: none;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.af-op-copy {
  color: var(--brand);
  background: var(--brand-bg);
}
.af-op-copy:hover { background: var(--brand-xl); }
.af-op-regen {
  color: var(--body-c);
  background: var(--line-2);
}
.af-op-regen:hover { background: var(--line); }
.af-op-regen:disabled {
  opacity: .6;
  cursor: not-allowed;
}
.af-result {
  flex: 1;
  min-height: 240px;
  display: flex;
  flex-direction: column;
}
.af-empty { margin: auto; }
.af-empty-hint {
  font-size: 13px;
  color: var(--body-c);
}
.af-result-text {
  white-space: pre-wrap;
  line-height: 1.8;
  color: var(--ink);
  font-size: 14px;
  flex: 1;
}
.af-note {
  margin-top: var(--s-3);
  font-size: 12px;
  color: var(--warning);
  line-height: 1.5;
}
/* 结果区脚注:语气/字数说明 */
.af-result-foot {
  margin-top: var(--s-3);
  padding-top: var(--s-3);
  border-top: 1px solid var(--line);
  font-size: 12px;
  color: var(--weak);
  display: flex;
  justify-content: space-between;
}
.af-foot-placeholder { opacity: .6; }

/* 桌面端:两列布局,页内顶部栏让位给全局 AppHeader,底部无需再让开导航 */
@media (min-width: 768px) {
  .page-head { display: none; }
  .af-main {
    padding: var(--s-7) var(--s-6) var(--s-9);
  }
  .af-grid {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--s-5);
    align-items: start;
  }
  .af-intensity { grid-template-columns: repeat(4, 1fr); }
}
</style>
