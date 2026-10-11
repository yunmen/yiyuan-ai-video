<template>
  <view class="app-page detail">
    <AppNavBar title="分镜编辑" align="left" solid />

    <view class="detail__body">
      <!-- 加载中 -->
      <view v-if="loading && !detail" class="detail__state">
        <AppIcon name="loader" :size="28" color="#9C9488" class="app-spin" />
        <text class="detail__state-text">加载中…</text>
      </view>

      <!-- 错误态 -->
      <AppEmpty
        v-else-if="error"
        title="加载失败"
        :desc="error"
        icon="alert-circle"
        action-text="重试"
        @action="reload"
      />

      <template v-else-if="detail">
        <!-- 成片 / 重跑占位 -->
        <view class="detail__player">
          <video
            v-if="detail.result_video && statusOf(detail).key !== 'processing'"
            class="detail__video"
            :src="detail.result_video"
            controls
            object-fit="contain"
          />
          <view v-else class="detail__player-empty">
            <AppIcon name="film" :size="40" color="#D5CBB6" :stroke-width="1.5" />
            <text v-if="statusOf(detail).key === 'processing'" class="detail__player-phase">
              {{ workStageText(detail.progress) }}
            </text>
            <text v-else class="detail__player-hint">暂无成片</text>
          </view>
        </view>

        <!-- 处理中进度条（局部重跑回到 processing 时展示） -->
        <view v-if="statusOf(detail).key === 'processing'" class="detail__progress">
          <view class="detail__progress-bar">
            <view class="detail__progress-fill" :style="{ width: normalizeProgress(detail.progress) + '%' }" />
          </view>
          <text class="detail__progress-text">{{ normalizeProgress(detail.progress) }}% · 局部重跑中</text>
        </view>

        <view v-if="bindingQc && statusOf(detail).key !== 'processing'" class="detail__shot">
          <text class="detail__shot-no">元素替换核验 · {{ bindingQcLabel(bindingQc.status) }}</text>
          <text class="detail__shot-qc-note">仅核验抽样帧，不代表全片通过；未采样区间和离场空档仍需人工检查。</text>
          <text v-if="bindingQc.reason" class="detail__shot-qc-note">{{ bindingQc.reason }}</text>
          <view v-for="element in bindingQc.elements || []" :key="element.element_id">
            <text class="detail__shot-narration">{{ element.label || element.element_id }}：{{ bindingQcLabel(element.status) }}</text>
            <text v-if="element.reason" class="detail__shot-qc-note">{{ element.reason }}</text>
            <text v-for="(sample, index) in element.samples || []" :key="index" class="detail__shot-qc-note">
              {{ sample.source_time }}秒 · {{ bindingQcLabel(sample.status) }}：{{ sample.reason }}
            </text>
            <text v-if="element.consistency" class="detail__shot-qc-note">身份一致性：{{ bindingQcLabel(element.consistency.status) }} · {{ element.consistency.reason }}</text>
          </view>
        </view>

        <!-- 分镜列表 -->
        <view class="detail__shots">
          <view class="detail__shots-title">
            <view class="detail__shots-heading">
              <text class="detail__shots-count">分镜（{{ visibleShots.length }}/{{ shots.length }}）</text>
              <view
                class="detail__filter"
                :class="{ 'detail__filter--active': onlyLowShots }"
                role="button"
                @click="onlyLowShots = !onlyLowShots"
              >
                <view class="detail__filter-check">
                  <AppIcon v-if="onlyLowShots" name="check" :size="11" color="#FFFFFF" :stroke-width="2.5" />
                </view>
                <text>只看低分镜头</text>
              </view>
            </view>
            <text class="detail__shots-sub">可改每镜提示词，或改一句台词重生成</text>
          </view>

          <view v-if="!shots.length || !visibleShots.length" class="detail__empty">
            <AppIcon name="layers" :size="32" color="#D5CBB6" :stroke-width="1.5" />
            <text class="detail__empty-text">{{ shots.length ? '当前没有低分镜头' : '该任务暂无可编辑分镜（仅支持带时间轴的新任务）' }}</text>
          </view>

          <view v-for="shot in visibleShots" :key="shot.index" class="detail__shot">
            <view class="detail__shot-head">
              <text class="detail__shot-no">镜头 {{ shot.index + 1 }}</text>
              <text class="detail__shot-time">{{ shotTimeText(shot) }}</text>
            </view>

            <view class="detail__shot-quality" :class="`detail__shot-quality--${qualityState(shot).key}`">
              <view class="detail__shot-quality-main">
                <AppIcon :name="qualityState(shot).icon" :size="14" :color="qualityState(shot).color" :stroke-width="2.2" />
                <text>{{ qualityState(shot).label }}</text>
              </view>
              <text v-if="hasQcScore(shot)" class="detail__shot-score">{{ formatQcScore(shot.qc_score) }}分</text>
            </view>
            <text v-if="shot.qc_note" class="detail__shot-qc-note">{{ shot.qc_note }}</text>
            <view v-if="shot.qc_low" class="detail__shot-rerun-tip">
              <AppIcon name="refresh-cw" :size="13" color="#B98236" :stroke-width="2.5" />
              <text>建议修改提示词后重跑该镜头，优先检查画面主体、动作和运镜是否清晰。</text>
            </view>

            <text v-if="shot.narration" class="detail__shot-narration">原片台词：{{ shot.narration }}</text>

            <textarea
              v-model="shot.prompt"
              class="detail__shot-input"
              placeholder="输入该镜头的生视频提示词（画面与运镜），留空则沿用原片"
              :maxlength="500"
            />

            <view class="detail__shot-actions">
              <view class="detail__btn detail__btn--ghost" role="button" @click="saveShotPrompt(shot)">
                <text>保存</text>
              </view>
              <view
                class="detail__btn detail__btn--primary"
                :class="{ 'detail__btn--disabled': regenerating || !canRerun }"
                role="button"
                @click="regenerateShot(shot)"
              >
                <text>{{ regenerating ? '重跑中…' : '改这句重生成' }}</text>
              </view>
            </view>
          </view>
        </view>
      </template>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import AppEmpty from '@/components/AppEmpty.vue'
import api from '@/api'
import {
  normalizeProgress,
  workFailReason,
  workStageText,
  workStatus,
} from '@/utils/task'

const taskId = ref(null)
const detail = ref(null)
const shots = ref([])
const loading = ref(false)
const error = ref('')
const regenerating = ref(false)
const onlyLowShots = ref(false)
let pollTimer = null

const statusOf = (item) => workStatus(item.status)

/** 只展示与当前交付成片一致的验收报告，避免重跑期间沿用旧片结论。 */
const bindingQc = computed(() => {
  const item = detail.value
  const qc = item?.usage?.element_binding_qc
  return qc && qc.checked_output_url === item.result_video ? qc : null
})

/** 验收通过仅指采样帧；缺失或未知状态不能展示为成功。 */
function bindingQcLabel(status) {
  return { pass: '采样通过', fail: '发现替换问题', unknown: '无法判断' }[status] || '无法判断'
}

const visibleShots = computed(() => {
  if (!onlyLowShots.value) return shots.value
  return shots.value.filter((shot) => shot.qc_low)
})

function hasQcScore(shot) {
  return shot.qc_score !== null && shot.qc_score !== undefined && shot.qc_score !== '' && Number.isFinite(Number(shot.qc_score))
}

function formatQcScore(score) {
  const value = Number(score)
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function qualityState(shot) {
  if (shot.qc_low) return { key: 'low', label: '需要优化', icon: 'alert-circle', color: '#B98236' }
  if (hasQcScore(shot)) return { key: 'good', label: '质量良好', icon: 'check-circle', color: '#5C8A68' }
  return { key: 'unknown', label: '待质检', icon: 'info', color: '#8B8378' }
}

/** 仅带真实时间轴的视频任务支持局部重跑（与后端 regenerate_segment 校验口径一致） */
const canRerun = computed(() => {
  const item = detail.value
  if (!item || item.type !== 'video') return false
  if (statusOf(item).key === 'processing') return false
  const timing = item.usage && item.usage.subtitle_timing
  return Array.isArray(timing) && timing.length > 0
})

/** 毫秒 → 带一位小数的秒（如 2500 → 2.5s） */
function fmtSec(ms) {
  return (Number(ms || 0) / 1000).toFixed(1)
}
function shotTimeText(shot) {
  return `${fmtSec(shot.start_ms)}s - ${fmtSec(shot.end_ms)}s`
}

function toast(title) {
  uni.showToast({ title, icon: 'none' })
}

/** 拉取任务详情（状态 / 进度 / 成片 / usage）；非 200 业务错误一律写入 error */
async function loadDetail() {
  const res = await api.task.detail.post({ id: taskId.value }, { suppressGlobalError: true })
  if (res && res.code === 1 && res.data) {
    detail.value = res.data
    return res.data
  }
  // 业务错误（如任务不存在）：后端可能返回 {detail:"..."}，无 code 字段
  error.value = res?.data?.message || res?.message || res?.detail || res?.msg || '加载任务详情失败'
  return null
}

/** 拉取任务分镜/镜头列表（含提示词、台词、时长、质检） */
async function loadShots() {
  const res = await api.storyboard.list.post(
    { task_id: taskId.value, page_num: 1, page_size: 100 },
    { suppressGlobalError: true },
  )
  const list = res && res.code === 1 && res.data ? res.data.shots : null
  shots.value = Array.isArray(list) ? list : []
}

async function reload() {
  error.value = ''
  loading.value = true
  try {
    await loadDetail()
    if (detail.value) await loadShots()
  } catch (err) {
    error.value = err?.data?.message || err?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

/** 保存单镜提示词：回写 usage.shot_prompts，供后续局部重跑读取编辑后的提示词 */
async function saveShotPrompt(shot) {
  try {
    const res = await api.storyboard.shotUpdate.post(
      { task_id: taskId.value, index: shot.index, prompt: shot.prompt || '' },
      { suppressGlobalError: true },
    )
    if (res && res.code === 1) toast('已保存镜头提示词')
    else toast(res?.data?.message || res?.message || res?.detail || '保存失败')
  } catch (err) {
    console.error('保存镜头提示词失败', err)
    toast(err?.data?.message || err?.message || '保存失败')
  }
}

/** 改一句台词重生成：先落盘编辑后的提示词（best-effort），再提交局部重跑，随后轮询至完成 */
async function regenerateShot(shot) {
  if (regenerating.value) return
  if (!canRerun.value) {
    toast('该任务暂不支持局部重跑')
    return
  }
  try {
    // 先把当前编辑的提示词落盘，失败也不阻断重跑（重跑以 new_text 为准）
    try {
      await api.storyboard.shotUpdate.post(
        { task_id: taskId.value, index: shot.index, prompt: shot.prompt || '' },
        { suppressGlobalError: true },
      )
    } catch (saveErr) {
      console.error('局部重跑前保存提示词失败（继续重跑）', saveErr)
    }
    const res = await api.task.regenerateSegment.post(
      { id: taskId.value, segment_index: shot.index, new_text: shot.prompt || '' },
      { suppressGlobalError: true },
    )
    if (!(res && res.code === 1)) {
      toast(res?.data?.message || res?.message || res?.detail || '提交局部重跑失败')
      return
    }
    regenerating.value = true
    toast('已提交，正在重新生成该镜头')
    startPolling()
  } catch (err) {
    console.error('局部重跑失败', err)
    toast(err?.data?.message || err?.message || '提交失败')
  }
}

/** 轮询任务详情，直到局部重跑完成（success）或失败 */
function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    const data = await loadDetail()
    if (!data) {
      // 详情拉取失败（如会话失效）：停止轮询，交由错误态提示
      stopPolling()
      regenerating.value = false
      return
    }
    const key = statusOf(data).key
    if (key === 'success') {
      stopPolling()
      regenerating.value = false
      await loadShots()
      toast('局部重跑完成')
    } else if (key === 'failed') {
      stopPolling()
      regenerating.value = false
      toast(workFailReason(data) || '局部重跑失败')
    }
  }, 2000)
}
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onLoad((options) => {
  const id = Number(options && options.id)
  if (!Number.isFinite(id) || id <= 0) {
    error.value = '缺少任务参数'
    return
  }
  taskId.value = id
  reload()
})

onUnload(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
.detail {
  min-height: 100vh;
  background: var(--bg-page, #FBF8F2);

  &__body {
    padding: 16px;
  }

  &__state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 80px 0;
  }

  &__state-text {
    font-size: 13px;
    color: var(--text-muted);
  }

  /* 成片播放 */
  &__player {
    width: 100%;
    border-radius: var(--radius-xl);
    overflow: hidden;
    background: #1F1D1A;
  }

  &__video {
    width: 100%;
    height: 240px;
    display: block;
    background: #1F1D1A;
  }

  &__player-empty {
    height: 240px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: var(--grad-brand-soft, #F8EAE6);
  }

  &__player-phase {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
  }

  &__player-hint {
    font-size: 13px;
    color: var(--text-muted);
  }

  /* 进度条 */
  &__progress {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;

    &-bar {
      width: 100%;
      height: 6px;
      border-radius: var(--radius-full);
      background: var(--bg-hover);
      overflow: hidden;
    }

    &-fill {
      height: 100%;
      border-radius: var(--radius-full);
      background: var(--grad-brand);
      transition: width 0.7s cubic-bezier(0.4, 0, 0.2, 1);
    }

    &-text {
      font-size: 12px;
      color: var(--text-secondary);
    }
  }

  /* 分镜列表 */
  &__shots {
    margin-top: 20px;
  }

  &__shots-title {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-bottom: 12px;
  }

  &__shots-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  &__filter {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 5px 8px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-full);
    color: var(--text-muted);
    font-size: 11px;

    &--active {
      border-color: #D6A866;
      color: #9A6826;
      background: #FFF7E8;
    }
  }

  &__filter-check {
    width: 14px;
    height: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border-light);
    border-radius: 3px;
    background: var(--bg-card);
  }

  &__filter--active &__filter-check {
    border-color: #B98236;
    background: #B98236;
  }

  &__shots-count {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
  }

  &__shots-sub {
    font-size: 12px;
    color: var(--text-muted);
  }

  &__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 40px 0;
  }

  &__empty-text {
    font-size: 13px;
    color: var(--text-muted);
    text-align: center;
  }

  &__shot {
    padding: 14px;
    margin-bottom: 12px;
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-xl);

    &-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    &-no {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
    }

    &-time {
      font-size: 11px;
      color: var(--text-muted);
      font-variant-numeric: tabular-nums;
    }

    &-narration {
      display: block;
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.5;
      margin-bottom: 8px;
    }

    &-input {
      width: 100%;
      min-height: 56px;
      padding: 8px 10px;
      font-size: 12px;
      line-height: 1.5;
      color: var(--text-primary);
      background: var(--bg-hover);
      border: 1px solid var(--border-light);
      border-radius: var(--radius-sm);
    }

    &-quality {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 6px;
      font-size: 12px;
      font-weight: 600;

      &--low {
        color: #9A6826;
      }

      &--good {
        color: #4E7958;
      }

      &--unknown {
        color: var(--text-muted);
      }
    }

    &-quality-main {
      display: flex;
      align-items: center;
      gap: 5px;
    }

    &-score {
      font-variant-numeric: tabular-nums;
    }

    &-qc-note {
      display: block;
      margin-bottom: 8px;
      font-size: 11px;
      line-height: 1.5;
      color: var(--text-secondary);
    }

    &-rerun-tip {
      display: flex;
      align-items: flex-start;
      gap: 4px;
      margin-bottom: 8px;
      font-size: 11px;
      line-height: 1.5;
      color: #B98236;
    }

    &-actions {
      display: flex;
      gap: 10px;
      margin-top: 12px;
    }
  }

  /* 按钮 */
  &__btn {
    flex: 1;
    height: 38px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-full);
    font-size: 13px;
    font-weight: 600;

    &--ghost {
      background: var(--bg-hover);
      color: var(--text-secondary);
    }

    &--primary {
      background: var(--grad-brand);
      color: #ffffff;
    }

    &--disabled {
      opacity: 0.5;
    }
  }
}
</style>
