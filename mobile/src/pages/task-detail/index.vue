<template>
  <view class="app-page detail">
    <AppNavBar title="分镜编辑" align="left" solid />

    <view class="detail__body">
      <!-- 加载中 -->
      <view v-if="loading && !detail" class="detail__state">
        <AppIcon name="loader" :size="28" color="#94A3B8" class="app-spin" />
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
            <AppIcon name="film" :size="40" color="#CBD5E1" :stroke-width="1.5" />
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

        <!-- 分镜列表 -->
        <view class="detail__shots">
          <view class="detail__shots-title">
            <text class="detail__shots-count">分镜（{{ shots.length }}）</text>
            <text class="detail__shots-sub">可改每镜提示词，或改一句台词重生成</text>
          </view>

          <view v-if="!shots.length" class="detail__empty">
            <AppIcon name="layers" :size="32" color="#CBD5E1" :stroke-width="1.5" />
            <text class="detail__empty-text">该任务暂无可编辑分镜（仅支持带时间轴的新任务）</text>
          </view>

          <view v-for="shot in shots" :key="shot.index" class="detail__shot">
            <view class="detail__shot-head">
              <text class="detail__shot-no">镜头 {{ shot.index + 1 }}</text>
              <text class="detail__shot-time">{{ shotTimeText(shot) }}</text>
            </view>

            <text v-if="shot.narration" class="detail__shot-narration">原片台词：{{ shot.narration }}</text>

            <textarea
              v-model="shot.prompt"
              class="detail__shot-input"
              placeholder="输入该镜头的生视频提示词（画面与运镜），留空则沿用原片"
              :maxlength="500"
            />

            <view v-if="shot.qc_low" class="detail__shot-qc">
              <AppIcon name="alert-circle" :size="13" color="#F59E0B" :stroke-width="2.5" />
              <text>{{ shot.qc_note || '该镜头质检偏低，建议重跑' }}</text>
            </view>

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
let pollTimer = null

const statusOf = (item) => workStatus(item.status)

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
  background: var(--bg-page, #f8fafc);

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
    background: #0f172a;
  }

  &__video {
    width: 100%;
    height: 240px;
    display: block;
    background: #000;
  }

  &__player-empty {
    height: 240px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: var(--grad-brand-soft, #eef2ff);
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

    &-qc {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 8px;
      font-size: 11px;
      color: #f59e0b;
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
