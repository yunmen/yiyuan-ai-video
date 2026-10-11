<template>
  <view class="app-page flavor">
    <AppNavBar title="文案去味" />

    <view class="flavor__body">
      <!-- 副标题：一句话说明这个工具解决什么问题 -->
      <text class="flavor__sub">把生硬的 AI 腔，改成有温度的自然表达</text>

      <view class="flavor__paper-note">
        <view class="flavor__paper-mark" />
        <text>今日改稿 · 保留你的原意，只调整表达</text>
      </view>

      <view class="flavor__card flavor__card--input">
        <view class="flavor__card-head">
          <view class="flavor__heading">
            <text class="flavor__eyebrow">起草纸</text>
            <text class="flavor__card-title">贴入原稿</text>
          </view>
          <text class="flavor__counter">{{ inputText.length }} / 2000</text>
        </view>
        <textarea
          v-model="inputText"
          class="flavor__textarea"
          :maxlength="2000"
          :placeholder="inputPlaceholder"
          :focus="inputFocused"
          placeholder-style="color:#9C9488"
        />
      </view>

      <view class="flavor__section">
        <view class="flavor__section-head">
          <view>
            <text class="flavor__eyebrow">落笔方式</text>
            <text class="flavor__label">选择风格</text>
          </view>
          <text class="flavor__hint">先定语气，再动笔</text>
        </view>
        <view class="flavor__chips">
          <view
            v-for="item in STYLE_OPTIONS"
            :key="item.key"
            class="app-chip flavor__chip"
            :class="{ 'flavor__chip--active': style === item.key }"
            role="button"
            :aria-label="item.label"
            @click="style = item.key"
          >
            <text>{{ item.label }}</text>
          </view>
        </view>
      </view>

      <view class="flavor__section flavor__section--last">
        <view class="flavor__section-head">
          <view>
            <text class="flavor__eyebrow">墨色浓淡</text>
            <text class="flavor__label">去味强度</text>
          </view>
          <text class="flavor__hint">控制改动的幅度</text>
        </view>
        <view class="flavor__levels">
          <view
            v-for="item in LEVEL_OPTIONS"
            :key="item.key"
            class="flavor__level"
            :class="{ 'flavor__level--active': level === item.key }"
            role="button"
            :aria-label="item.label"
            @click="level = item.key"
          >
            <view class="flavor__level-dot" />
            <text class="flavor__level-name">{{ item.label }}</text>
            <text class="flavor__level-desc">{{ item.desc }}</text>
          </view>
        </view>
      </view>

      <view
        class="app-btn-brand flavor__submit"
        :class="{ 'flavor__submit--loading': running }"
        role="button"
        :aria-label="running ? '去味中' : '一键去味'"
        @click="runRewrite"
      >
        <AppIcon
          :name="running ? 'loader' : 'wand'"
          :size="20"
          color="#FFFFFF"
          :stroke-width="2.5"
          :class="running ? 'app-spin' : ''"
        />
        <text>{{ running ? '去味中...' : '一键去味' }}</text>
      </view>

      <view v-if="showResult" class="flavor__card flavor__card--result">
        <view class="flavor__result-head">
          <view class="flavor__heading">
            <text class="flavor__eyebrow">改稿纸</text>
            <text class="flavor__card-title">去味结果</text>
          </view>
          <view class="flavor__result-actions">
            <view class="flavor__pill flavor__pill--brand" role="button" aria-label="复制" @click="handleCopy">
              <AppIcon :name="copied ? 'check' : 'copy'" :size="14" color="#B23A2E" :stroke-width="2.5" />
              <text>{{ copied ? '已复制' : '复制' }}</text>
            </view>
            <view class="flavor__pill" role="button" aria-label="重新生成" @click="runRewrite">
              <AppIcon name="refresh-cw" :size="14" color="#3A342C" :stroke-width="2.5" />
              <text>重新生成</text>
            </view>
          </view>
        </view>
        <view class="flavor__result-body">
          <!-- 结果只读展示：uni 的 textarea 只透传官方属性，readonly 到不了原生节点，故用 disabled 保证不可编辑 -->
          <textarea
            v-model="outputText"
            class="flavor__textarea flavor__textarea--out"
            :disabled="true"
          />
        </view>
      </view>
    </view>

    <!-- 设计稿此处为全局底部导航，创作高亮 -->
    <AppTabBar active="create" />
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onUnload } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import AppTabBar from '@/components/AppTabBar.vue'
import api from '@/api'

/**
 * 文案去味（对应设计稿《文案去味》）。
 *
 * 真实链路是异步的：/v1/content/rewrite 只返回 task_id，必须轮询 /v1/content/result 取产物。
 * 内容接口按 IP 限流但不校验登录，所以本页不做登录门禁，直接可用。
 */

/** 风格 → 后端 tone；key 即接口取值 */
const STYLE_OPTIONS = [
  { key: 'natural', label: '自然口语' },
  { key: 'formal', label: '专业正式' },
  { key: 'humorous', label: '活泼有趣' },
  { key: 'sharp', label: '简洁干练' },
]

/** 强度 → 后端 level：后端只接受 1..4，深度取 4 表示「全面重写」 */
const LEVEL_OPTIONS = [
  { key: 1, label: '轻度', desc: '微调优化' },
  { key: 2, label: '中度', desc: '自然改写' },
  { key: 4, label: '深度', desc: '全面重写' },
]

/** 设计稿默认文案，空输入时替换为提示语 */
const DEFAULT_PLACEHOLDER = '粘贴你要去味的 AI 文案...'

// 轮询间隔与总时长上限：2s 一次，最多约 2 分钟
const POLL_INTERVAL = 2000
const POLL_TIMEOUT = 120000

const inputText = ref('')
const outputText = ref('')
const inputPlaceholder = ref(DEFAULT_PLACEHOLDER)
const inputFocused = ref(false)
const style = ref('natural')
const level = ref(2)
const running = ref(false)
const showResult = ref(false)
const copied = ref(false)

let pollTimer = null
let copyTimer = null

function toast(title) {
  uni.showToast({ title, icon: 'none' })
}

/** 空输入时聚焦输入框；先置 false 再置 true，保证已聚焦状态下也能重新唤起光标 */
function focusInput() {
  inputFocused.value = false
  setTimeout(() => {
    inputFocused.value = true
  }, 50)
}

/**
 * 轮询去味产物：done 返回正文，not_found 或超时返回空串（由调用方统一提示失败）。
 */
function pollResult(taskId) {
  return new Promise((resolve) => {
    const startedAt = Date.now()
    pollTimer = setInterval(async () => {
      if (Date.now() - startedAt > POLL_TIMEOUT) {
        clearInterval(pollTimer)
        pollTimer = null
        resolve('')
        return
      }
      try {
        const res = await api.content.result.post(
          { task_id: taskId },
          { suppressGlobalError: true, suppressGlobalAuthError: true }
        )
        const data = res && res.code === 1 ? res.data : null
        if (!data) return
        if (data.status === 'done') {
          clearInterval(pollTimer)
          pollTimer = null
          // rewrite 产物 content 为对象 {rewritten,...}，兼容直接字符串形态
          resolve((data.result?.content?.rewritten ?? data.result?.content ?? '').trim())
        } else if (data.status === 'not_found') {
          clearInterval(pollTimer)
          pollTimer = null
          resolve('')
        }
      } catch (err) {
        // 单次轮询失败不终止流程，等待下一次重试
        console.error('轮询去味结果失败，将继续重试', err)
      }
    }, POLL_INTERVAL)
  })
}

/** 一键去味 / 重新生成共用同一套流程，入参始终取当前选中的风格与强度 */
async function runRewrite() {
  if (running.value) return

  const text = inputText.value.trim()
  if (!text) {
    inputPlaceholder.value = '请先输入要去味的文案哦～'
    focusInput()
    return
  }

  running.value = true
  try {
    const res = await api.content.rewrite.post(
      { text, level: level.value, tone: style.value, max_chars: 0 },
      { suppressGlobalError: true, suppressGlobalAuthError: true }
    )
    const taskId = res && res.code === 1 ? res.data?.task_id : null
    if (!taskId) {
      toast('去味失败，请重试')
      return
    }

    const content = await pollResult(taskId)
    if (!content) {
      toast('去味失败，请重试')
      return
    }
    outputText.value = content
    showResult.value = true
  } catch (err) {
    // 触发限流时后端会给出「过于频繁」的可执行文案，原样透传
    console.error('文案去味失败', err)
    toast(err?.data?.message || err?.message || '去味失败，请重试')
  } finally {
    running.value = false
  }
}

/** 复制结果：成功后按钮文案切「已复制」，1.5s 后复原 */
function handleCopy() {
  if (!outputText.value) return
  uni.setClipboardData({
    data: outputText.value,
    success: () => {
      copied.value = true
      if (copyTimer) clearTimeout(copyTimer)
      copyTimer = setTimeout(() => {
        copied.value = false
      }, 1500)
    },
    fail: (err) => {
      console.error('复制去味结果失败', err)
      toast('复制失败')
    },
  })
}

onUnload(() => {
  // 离开页面必须停掉轮询与复制态计时器，避免回调打到已销毁的页面
  if (pollTimer) clearInterval(pollTimer)
  if (copyTimer) clearTimeout(copyTimer)
  pollTimer = null
  copyTimer = null
})
</script>

<style lang="scss" scoped>
.flavor__body {
  padding: 18px 16px 24px;
}

.flavor__sub {
  display: block;
  margin-bottom: 10px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-tertiary);

  &::first-letter {
    color: var(--brand-primary);
  }
}

.flavor__paper-note {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
  font-size: 12px;
  color: var(--text-muted);
}

.flavor__paper-mark {
  width: 18px;
  height: 1px;
  background: var(--brand-secondary);
}

.flavor__heading {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.flavor__eyebrow {
  display: block;
  font-size: 11px;
  letter-spacing: 0.12em;
  color: var(--brand-primary);
}

.flavor__section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 12px;
}

.flavor__hint {
  padding-bottom: 2px;
  font-size: 11px;
  color: var(--text-muted);
}



/* ============ 卡片 ============ */
.flavor__card {
  background: #FDFBF6;
  background-image: linear-gradient(rgba(180, 142, 93, 0.08) 1px, transparent 1px);
  background-size: 100% 28px;
  border-top: 2px solid rgba(178, 58, 46, 0.18);

  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  margin-bottom: 20px;

  &--input {
    padding: 16px;
  }
}

.flavor__card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.flavor__card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.flavor__counter {
  font-size: 12px;
  color: var(--text-muted);
}

.flavor__textarea {
  width: 100%;
  height: 160px;
  font-size: 14px;
  line-height: 1.6;
  color: #26231E;
  background: transparent;

  &--out {
    height: 192px;
  }
}

/* ============ 选择区 ============ */
.flavor__section {
  margin-bottom: 20px;

  &--last {
    margin-bottom: 24px;
  }
}

.flavor__label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.flavor__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 选中态用品牌渐变填充（设计稿形态），覆盖通用芯片的描边选中态 */
.flavor__chip {
  padding: 8px 16px;
  border-width: 1px;

  &--active {
    background: var(--grad-brand);
    border-color: transparent;
    color: #ffffff;
    box-shadow: var(--shadow-brand);
  }
}

/* ============ 强度 ============ */
.flavor__levels {
  display: flex;
  gap: 12px;
}

.flavor__level {
  flex: 1;
  min-height: 84px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 8px;
  border-radius: var(--radius-md);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  color: var(--text-secondary);
  transition: all var(--transition-fast);

  &--active {
    border-color: var(--brand-primary);
    background: var(--brand-primary-light);
    color: var(--brand-primary);
  }
}

.flavor__level-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-medium);
  transition: all var(--transition-fast);
}

.flavor__level--active .flavor__level-dot {
  background: var(--grad-brand);
}

.flavor__level-name {
  font-size: 14px;
  font-weight: 500;
}

.flavor__level-desc {
  font-size: 11px;
  color: var(--text-muted);
}

/* ============ 主按钮 ============ */
.flavor__submit {
  width: 100%;
  height: 56px;
  font-size: 16px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-brand-lg);
  margin-bottom: 24px;

  &--loading {
    opacity: 0.8;
  }
}

/* ============ 结果区 ============ */
.flavor__result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
}

.flavor__result-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.flavor__pill {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--radius-full);
  background: var(--bg-hover);
  color: var(--text-secondary);

  &--brand {
    background: var(--brand-primary-light);
    color: var(--brand-primary);
  }
}

.flavor__result-body {
  padding: 16px;
}
</style>
