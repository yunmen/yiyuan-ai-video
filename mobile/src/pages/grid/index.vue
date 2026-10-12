<template>
  <view class="app-page grid-page">
    <AppNavBar title="九宫格成片" />

    <!-- 模式切换 -->
    <view class="tabs">
      <view
        v-for="m in modes"
        :key="m.key"
        class="tabs__item"
        :class="{ 'tabs__item--active': mode === m.key }"
        role="button"
        @click="mode = m.key"
      >
        <text>{{ m.label }}</text>
      </view>
    </view>

    <view class="content">
      <!-- 模式1:提示词生成九宫格 -->
      <block v-if="mode === 'prompt'">
        <view class="field">
          <text class="field__label">画面描述</text>
          <textarea
            class="field__textarea"
            v-model="prompt"
            placeholder="描述你想要的九宫格画面,将生成 9 个不同构图/风格的照片"
            placeholder-class="app-placeholder"
            :maxlength="2000"
          />
          <text class="field__count">{{ prompt.length }}/2000</text>
        </view>
        <view class="field">
          <text class="field__label">画幅</text>
          <view class="chips">
            <view
              v-for="r in ratios"
              :key="r"
              class="chip"
              :class="{ 'chip--active': ratio === r }"
              role="button"
              @click="ratio = r"
            >
              <text>{{ r }}</text>
            </view>
          </view>
        </view>
      </block>

      <!-- 模式2:上传 9 张拼合 -->
      <block v-if="mode === 'upload'">
        <text class="tip">上传 9 张照片,自动拼成 3×3 九宫格(也可少于 9 张,空缺格留白)</text>
        <view class="upload-grid">
          <view
            v-for="(cell, idx) in uploadCells"
            :key="idx"
            class="upload-cell"
            role="button"
            @click="pickUpload(idx)"
          >
            <image v-if="cell.url" :src="cell.localPath || cell.url" class="upload-cell__img" mode="aspectFill" />
            <view v-else class="upload-cell__content">
              <text v-if="cell.uploading" class="upload-cell__pct">{{ cell.progress }}%</text>
              <template v-else>
                <AppIcon name="plus" :size="28" color="#9C9488" />
                <text class="upload-cell__idx">{{ idx + 1 }}</text>
              </template>
            </view>
          </view>
        </view>
      </block>

      <!-- 模式3:上传一张九宫格拆分 -->
      <block v-if="mode === 'split'">
        <text class="tip">上传一张九宫格照片,自动按 3×3 拆分为 9 张单图</text>
        <view class="upload-single" role="button" @click="pickSplit">
          <image v-if="splitCell.url" :src="splitCell.localPath || splitCell.url" class="upload-single__img" mode="aspectFill" />
          <view v-else class="upload-single__content">
            <text v-if="splitCell.uploading" class="upload-single__pct">{{ splitCell.progress }}%</text>
            <template v-else>
              <AppIcon name="image" :size="32" color="#9C9488" />
              <text class="upload-single__hint">点击上传九宫格照片</text>
            </template>
          </view>
        </view>
      </block>

      <ToolCost ref="toolCost" :params="{ type: 'image', num_images: 9 }" />
      <!-- 提交按钮 -->
      <view class="actions">
        <view
          class="btn-primary app-btn-brand"
          :class="{ 'btn-primary--disabled': submitting }"
          role="button"
          @click="submit"
        >
          <text>{{ submitting ? '提交中…' : (mode === 'split' ? '拆分为 9 张' : '生成九宫格') }}</text>
        </view>
      </view>

      <!-- 结果区 -->
      <view v-if="task" class="result">
        <view v-if="task.status === 'processing'" class="result__progress">
          <text class="result__progress-text">生成中 {{ task.progress || 0 }}%</text>
        </view>
        <view v-else-if="task.status === 'failed'" class="result__fail">
          <text>生成失败:{{ task.fail_reason || '请重试' }}</text>
        </view>
        <view v-else-if="task.status === 'success'" class="result__ok">
          <text class="result__title">{{ isSplit ? '已拆分为 9 张单图' : '九宫格成片' }}</text>
          <image v-if="!isSplit && resultList[0]" :src="resultList[0]" class="result__grid-img" mode="widthFix" @click="preview(resultList[0])" />
          <view v-else class="result__split">
            <view v-for="(u, i) in resultList" :key="i" class="result__split-cell">
              <image
                :src="u"
                class="result__split-img"
                mode="aspectFill"
                @click="preview(u)"
              />
            </view>
          </view>
          <view class="result__save" role="button" @click="saveAll">
            <text>保存到相册</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { onUnload } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import ToolCost from '@/components/ToolCost.vue'

const toolCost = ref(null)
import api from '@/api'
import { uploadMedia } from '@/utils/upload'
import { useUserStore } from '@/store/modules/user'
import { currentPagePath, go, toLoginPath } from '@/utils/navigation'

const userStore = useUserStore()

// 三模式:提示词生成 / 上传9张拼合 / 上传1张拆分
const modes = [
  { key: 'prompt', label: '提示词生成' },
  { key: 'upload', label: '上传9张' },
  { key: 'split', label: '上传九宫格' },
]
const mode = ref('prompt')
const ratios = ['1:1', '16:9', '9:16', '4:3', '3:4']
const ratio = ref('1:1')
const prompt = ref('')

// 模式2:9 个上传格(每格独立上传 + 进度)
const uploadCells = reactive(
  Array.from({ length: 9 }, () => ({ url: '', localPath: '', uploading: false, progress: 0 }))
)
// 模式3:单张九宫格原图
const splitCell = reactive({ url: '', localPath: '', uploading: false, progress: 0 })

const submitting = ref(false)
const task = ref(null)
let pollTimer = null

const isSplit = computed(() => mode.value === 'split')
// 结果:拼合为单图(1 张),分割为多图(逗号拼接)——与 worker 回写 result_video 一致
const resultList = computed(() => {
  if (!task.value || !task.value.result_video) return []
  return String(task.value.result_video).split(',').filter(Boolean)
})

function requireLogin() {
  if (userStore.isLoggedIn) return true
  go(toLoginPath(currentPagePath()))
  return false
}

/** 上传单张图到后端 OSS,返回可透传的绝对地址(复用素材上传链路)。 */
async function uploadOne(path) {
  const data = await uploadMedia(path, {})
  return data && data.url
}

async function pickUpload(idx) {
  if (uploadCells[idx].uploading) return
  uni.chooseImage({
    count: 1,
    success: async (res) => {
      const path = res.tempFilePaths && res.tempFilePaths[0]
      if (!path) return
      uploadCells[idx].uploading = true
      try {
        const url = await uploadOne(path)
        uploadCells[idx].url = url
        uploadCells[idx].localPath = path
      } catch (err) {
        uni.showToast({ title: err?.message || '上传失败，请重试', icon: 'none' })
      } finally {
        uploadCells[idx].uploading = false
      }
    },
  })
}

async function pickSplit() {
  if (splitCell.uploading) return
  uni.chooseImage({
    count: 1,
    success: async (res) => {
      const path = res.tempFilePaths && res.tempFilePaths[0]
      if (!path) return
      splitCell.uploading = true
      try {
        const url = await uploadOne(path)
        splitCell.url = url
        splitCell.localPath = path
      } catch (err) {
        uni.showToast({ title: err?.message || '上传失败，请重试', icon: 'none' })
      } finally {
        splitCell.uploading = false
      }
    },
  })
}

/** 按当前模式构造建单参数(与后端 ImageCreateSchema 对齐)。 */
function buildParams() {
  if (mode.value === 'prompt') {
    const text = prompt.value.trim()
    if (!text) {
      uni.showToast({ title: '请填写画面描述', icon: 'none' })
      return null
    }
    return { prompt: text, grid: '3x3', num_images: 9, ratio: ratio.value }
  }
  if (mode.value === 'upload') {
    const materials = uploadCells.filter((c) => c.url).map((c) => c.url)
    if (materials.length < 2) {
      uni.showToast({ title: '请至少上传 2 张图片', icon: 'none' })
      return null
    }
    return { materials, grid: '3x3' }
  }
  // split:上传单张九宫格 → 拆分
  if (!splitCell.url) {
    uni.showToast({ title: '请上传一张九宫格照片', icon: 'none' })
    return null
  }
  return { materials: [splitCell.url], split: true }
}

/** 登录并核对费用后提交九宫格任务，避免重复扣费。 */
async function submit() {
  if (!requireLogin()) return
  if (submitting.value) return
  const params = buildParams()
  if (!params) return
  submitting.value = true
  task.value = null
  try {
    if (!await toolCost.value?.ensure()) return
    const res = await api.task.imageCreate.post(params)
    if (!res || res.code !== 1 || !res.data) {
      uni.showToast({ title: (res && res.message) || '创建失败', icon: 'none' })
      return
    }
    task.value = { id: res.data.id, status: res.data.status || 'processing', progress: 0 }
    startPoll(res.data.id)
    await toolCost.value?.refresh()
  } catch (err) {
    uni.showToast({ title: err?.message || '创建失败', icon: 'none' })
  } finally {
    submitting.value = false
  }
}

/** 轮询任务详情直到终态(success/failed)。 */
function startPoll(id) {
  stopPoll()
  pollTimer = setInterval(async () => {
    try {
      const res = await api.task.detail.post({ id })
      if (res && res.code === 1 && res.data) {
        task.value = { ...task.value, ...res.data }
        if (res.data.status === 'success' || res.data.status === 'failed') {
          stopPoll()
          await toolCost.value?.refresh()
        }
      }
    } catch (err) {
      // 轮询失败不阻断,下一拍继续
      console.error('轮询九宫格任务失败', err)
    }
  }, 2000)
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function preview(url) {
  if (!resultList.value.length) return
  uni.previewImage({ urls: resultList.value, current: url })
}

/** 逐张保存到相册：授权被拒时引导去设置页开启；其余失败尽力而为不打断。 */
async function saveAll() {
  let successCount = 0
  let authDenied = false
  for (const u of resultList.value) {
    try {
      const path = await new Promise((resolve, reject) => {
        uni.downloadFile({ url: u, success: (r) => resolve(r.tempFilePath), fail: reject })
      })
      const saved = await new Promise((resolve) => {
        uni.saveImageToPhotosAlbum({
          filePath: path,
          success: () => resolve(true),
          fail: (err) => {
            if (/auth|authorize|deny/i.test(String(err && err.errMsg))) authDenied = true
            resolve(false)
          },
        })
      })
      if (saved) successCount += 1
      if (authDenied) break
    } catch (err) {
      console.error('保存图片失败', err)
    }
  }
  if (authDenied) {
    uni.showModal({
      title: '需要相册权限',
      content: '保存图片到相册需要您授权访问手机相册，是否前往设置开启？',
      confirmText: '去设置',
      success: (res) => {
        if (res.confirm) uni.openSetting()
      },
    })
    return
  }
  uni.showToast({
    title: successCount ? `已保存 ${successCount} 张到相册` : '保存失败，请稍后重试',
    icon: 'none',
  })
}

onUnload(() => stopPoll())
</script>

<style lang="scss" scoped>
.app-page {
  min-height: 100vh;
  background: var(--paper-50);
}

.tabs {
  display: flex;
  gap: 0;
  padding: 16px 16px 0;
  border-bottom: 1px solid var(--line-2);
}

.tabs__item {
  flex: 1;
  text-align: center;
  padding: 12px 4px 11px;
  position: relative;
  color: var(--ink-500);
  font-family: var(--font-serif);
  font-size: 14px;
  letter-spacing: 0.04em;
}

.tabs__item--active {
  color: var(--brand-primary);
  font-weight: 700;
}

.tabs__item--active::after {
  content: '';
  position: absolute;
  left: 25%;
  right: 25%;
  bottom: -1px;
  height: 2px;
  background: var(--brand-primary);
}

.content {
  padding: 24px 16px 32px;
}

.field {
  margin-bottom: 24px;
  position: relative;
  padding-left: 12px;
  border-left: 2px solid var(--line-2);

  &__label {
    display: block;
    font-family: var(--font-serif);
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--ink-700);
    margin-bottom: 10px;
  }

  &__textarea {
    width: 100%;
    height: 120px;
    padding: 14px;
    border-radius: 2px;
    background: var(--paper-card);
    border: 1px solid var(--line-2);
    font-size: 14px;
    color: var(--ink-900);
    box-sizing: border-box;
    line-height: 1.7;
  }

  &__count {
    position: absolute;
    right: 10px;
    bottom: 8px;
    font-size: 11px;
    color: var(--ink-300);
  }
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  padding: 7px 16px;
  border-radius: 2px;
  background: var(--paper-card);
  border: 1px solid var(--line-2);
  color: var(--ink-500);
  font-size: 13px;

  &--active {
    background: var(--brand-primary-light);
    border-color: var(--brand-primary);
    color: var(--brand-primary);
    font-weight: 600;
  }
}

.tip {
  display: block;
  padding: 10px 12px;
  border-left: 2px solid var(--line-2);
  font-size: 13px;
  color: var(--ink-500);
  margin: 4px 0 16px;
  line-height: 1.7;
}

/* 9 格上传 */
.upload-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.upload-cell {
  position: relative;
  padding-top: 100%;
  border-radius: 2px;
  background: var(--paper-card);
  border: 1px dashed var(--line-2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  overflow: hidden;

  &__img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  &__content {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }

  &__pct {
    font-size: 13px;
    color: var(--brand-primary, #B23A2E);
  }

  &__idx {
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

/* 单张上传 */
.upload-single {
  position: relative;
  padding-top: 100%;
  border-radius: 2px;
  background: var(--paper-card);
  border: 1px dashed var(--line-2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  overflow: hidden;

  &__img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  &__content {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  &__pct {
    font-size: 14px;
    color: var(--brand-primary, #B23A2E);
  }

  &__hint {
    font-size: 13px;
    color: var(--text-tertiary);
  }
}

/* 提交 */
.actions {
  margin-top: 24px;
}

.btn-primary {
  height: 50px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;

  &--disabled {
    opacity: 0.6;
  }
}

/* 结果 */
.result {
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid var(--line-2);

  &__progress {
    padding: 24px;
    text-align: center;
    border-radius: 2px;
    background: var(--paper-card);
    border: 1px solid var(--line-2);
  }

  &__progress-text {
    font-size: 15px;
    color: var(--brand-primary, #B23A2E);
    font-weight: 600;
  }

  &__fail {
    padding: 24px;
    text-align: center;
    border-radius: 2px;
    background: var(--paper-card);
    border: 1px solid #e9c4bd;
    color: var(--brand-primary);
    font-size: 14px;
  }

  &__ok {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  &__title {
    font-family: var(--font-serif);
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--ink-700);
  }

  &__grid-img {
    width: 100%;
    border: 1px solid var(--line-2);
    border-radius: 2px;
    box-shadow: var(--shadow-sm);
  }

  &__split {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }

  &__split-cell {
    /* 1:1 撑高：不用 aspect-ratio，旧版小程序内核不支持会导致结果图塌陷 */
    position: relative;
    padding-top: 100%;
    overflow: hidden;
    border: 1px solid var(--line-2);
    border-radius: 2px;
    background: var(--paper-card);
  }

  &__split-img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }

  &__save {
    margin-top: 4px;
    align-self: center;
    padding: 10px 28px;
    border-radius: 3px;
    background: var(--paper-card);
    border: 1px solid var(--brand-primary);
    color: var(--brand-primary);
    font-family: var(--font-serif);
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.06em;
  }
}
</style>
