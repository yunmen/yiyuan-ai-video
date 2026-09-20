<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'

const router = useRouter()
const loading = ref(false)

// 创作模式:选模板做 / 上传参考做
const mode = ref('template')
const refFiles = ref([])

const templates = ref([])
const categories = ref([])
const total = ref(0)
const query = reactive({
  pageNum: 1,
  pageSize: 12,
  category: ''
})

async function loadCategories() {
  try {
    const res = await api.template.categoryList.post()
    if (res.code === 1) categories.value = res.data || []
  } catch (e) { /* 拦截器已提示 */ }
}

async function loadList() {
  loading.value = true
  try {
    const res = await api.template.list.post({ ...query })
    if (res.code === 1) {
      templates.value = res.data || []
      total.value = res.total || 0
    }
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
}

function switchCategory(category) {
  query.category = category
  query.pageNum = 1
  loadList()
}

function onPageChange(page) {
  query.pageNum = page
  loadList()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function useTemplate(id) {
  router.push(`/upload/${id}`)
}

// 上传参考做:校验与上传
function beforeRef(data) {
  const allowed = ['mp4', 'mov', 'm4v', 'webm']
  const ext = (data.file.name || '').split('.').pop().toLowerCase()
  if (!allowed.includes(ext)) {
    window.$message?.error('仅支持 MP4/MOV 等视频格式')
    return false
  }
  if (data.file.file.size > 50 * 1024 * 1024) {
    window.$message?.error('文件大小不能超过50MB')
    return false
  }
  return true
}

async function customRef({ file, onFinish, onError, onProgress }) {
  try {
    const formData = new FormData()
    formData.append('file', file.file)
    const res = await api.common.upload.file.post(formData, {
      onUploadProgress: (e) => {
        if (e.total) onProgress({ percent: Math.round((e.loaded * 100) / e.total) })
      }
    })
    if (res.code === 1) {
      file.url = res.data.url
      onFinish()
      window.$message?.success('参考视频已上传，请从模板库选择同款模板')
      mode.value = 'template'
    } else onError()
  } catch (e) { onError() }
}

onMounted(() => {
  loadCategories()
  loadList()
})
</script>

<template>
  <div class="tpl-page">
    <!-- 模式切换(选模板做 / 上传参考做) -->
    <div class="seg">
      <div class="seg-in">
        <div class="seg-item" :class="{ on: mode === 'template' }" @click="mode = 'template'">
          <b>选模板做</b><i></i>
        </div>
        <div class="seg-item" :class="{ on: mode === 'reference' }" @click="mode = 'reference'">
          <b>上传参考做</b><i></i>
        </div>
      </div>
    </div>

    <!-- 上传参考做 -->
    <template v-if="mode === 'reference'">
      <div class="wrap">
        <n-upload
          v-model:file-list="refFiles"
          accept="video/*"
          :max="1"
          :custom-request="customRef"
          :before-upload="beforeRef"
          :show-file-list="false"
          trigger-style="width:100%"
        >
          <n-upload-dragger>
            <div class="upload-zone">
              <div class="ic">
                <svg width="28" height="28" viewBox="0 0 28 28"><path d="M14 20V7M14 7L8.5 12.5M14 7L19.5 12.5" fill="none" stroke="#FF4D1C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 22H23" fill="none" stroke="#FF4D1C" stroke-width="2" stroke-linecap="round"/></svg>
              </div>
              <p>拖拽视频到这里，或点击上传</p>
              <p class="muted">支持 5-30 秒短视频，MP4 格式</p>
            </div>
          </n-upload-dragger>
          <div class="up-btn">上传视频</div>
        </n-upload>
      </div>
    </template>

    <!-- 选模板做 -->
    <template v-else>
      <div class="cats-bar">
        <div class="cats">
          <div class="cat" :class="{ on: query.category === '' }" @click="switchCategory('')">全部</div>
          <div
            v-for="c in categories"
            :key="c.name"
            class="cat"
            :class="{ on: query.category === c.name }"
            @click="switchCategory(c.name)"
          >{{ c.name }}<span v-if="c.count" class="cnt">{{ c.count }}</span></div>
        </div>
      </div>
      <div class="wrap">
        <n-spin :show="loading">
          <div v-if="templates.length" class="grid">
            <div v-for="t in templates" :key="t.id" class="tcard" @click="useTemplate(t.id)">
              <div class="cover" :style="t.cover ? { backgroundImage: `url(${t.cover})` } : {}">
                <div class="play">
                  <svg width="18" height="18" viewBox="0 0 18 18"><path d="M6 3L14 9L6 15V3Z" fill="#fff"/></svg>
                </div>
                <div class="tag">做同款</div>
                <div v-if="t.duration" class="dur">{{ t.duration }}s</div>
              </div>
              <p>{{ t.title }}</p>
              <span v-if="t.category" class="tcat">{{ t.category }}</span>
            </div>
          </div>
          <n-empty v-else-if="!loading" description="该分类模板整理中，先看看其他分类" style="padding:60px 0" />
        </n-spin>
        <div v-if="total > query.pageSize" class="pagination-wrap">
          <n-pagination
            v-model:page="query.pageNum"
            :item-count="total"
            :page-size="query.pageSize"
            :show-size-picker="false"
            @update:page="onPageChange"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.tpl-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding-bottom: 80px; }
.wrap { max-width: var(--page-max); margin: 0 auto; }

/* 模式切换 */
.seg {
  height: 48px;
  background: #fff;
  display: flex;
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: var(--header-h);
  z-index: 20;
}
.seg-in { max-width: var(--page-max); margin: 0 auto; width: 100%; display: flex; }
.seg-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  transition: color .15s;
}
.seg-item b { font-size: 15px; color: var(--weak); font-weight: 400; }
.seg-item.on b { color: var(--brand); font-weight: 700; }
.seg-item i { display: block; width: 56px; height: 3px; border-radius: 2px; background: transparent; }
.seg-item.on i { background: var(--brand); }
@media (min-width: 768px) {
  .seg-item { flex: 0 0 180px; }
  .seg-item:hover b { color: var(--brand); }
}

/* 上传参考 */
.upload-zone {
  margin: 20px;
  border: 1.5px dashed #C9CCD1;
  border-radius: 14px;
  height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: #fff;
  cursor: pointer;
}
/* 去掉 n-upload-dragger 默认样式,避免与自定义虚线框叠加;拖拽悬停时高亮自定义框 */
:deep(.n-upload-dragger) {
  border: none;
  padding: 0;
  background: transparent;
}
:deep(.n-upload-dragger:hover) {
  border: none;
}
:deep(.n-upload-dragger:hover .upload-zone) {
  border-color: #FF4D1C;
  background: var(--brand-bg);
}
.upload-zone .ic {
  width: 56px; height: 56px; border-radius: 50%;
  background: var(--brand-bg);
  display: flex; align-items: center; justify-content: center;
}
.upload-zone p { margin: 0; font-size: 14px; color: var(--body-c); }
.muted { font-size: 12px !important; color: var(--weak) !important; }
.up-btn {
  margin: 0 20px;
  height: 48px;
  border-radius: 24px;
  background: var(--brand);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
@media (min-width: 768px) {
  .upload-zone { max-width: 640px; margin: 32px auto 20px; }
  .up-btn { max-width: 320px; margin: 0 auto; }
}

/* 分类条 */
.cats-bar {
  background: #fff;
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: calc(var(--header-h) + 48px);
  z-index: 15;
}
.cats {
  max-width: var(--page-max);
  margin: 0 auto;
  display: flex;
  gap: 10px;
  padding: 12px 20px;
  overflow-x: auto;
}
.cats::-webkit-scrollbar { height: 0; }
.cat {
  height: 32px;
  padding: 0 14px;
  border-radius: 16px;
  background: var(--bg);
  color: var(--body-c);
  font-size: 13px;
  display: flex;
  align-items: center;
  white-space: nowrap;
  cursor: pointer;
  flex: 0 0 auto;
  transition: background .15s, color .15s;
}
.cat:hover { background: var(--brand-bg); color: var(--brand); }
.cat.on { background: var(--brand); color: #fff; font-weight: 700; }
.cat .cnt { margin-left: 4px; font-size: 11px; opacity: 0.75; }

/* 模板竖卡 */
.grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 16px 20px 20px;
}
.tcard { width: calc(50% - 28px); cursor: pointer; }
.cover {
  aspect-ratio: 159 / 220;
  border-radius: var(--radius);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #FFB88A, #FF5A20);
  background-size: cover;
  background-position: center;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: transform .2s, box-shadow .2s;
}
.tcard:hover .cover { transform: translateY(-4px); box-shadow: var(--shadow-brand); }
.play {
  width: 44px; height: 44px; border-radius: 50%;
  background: rgba(0, 0, 0, 0.32);
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.15s;
}
.tcard:hover .play { transform: scale(1.08); }
.tag {
  position: absolute; right: 6px; bottom: 6px;
  background: var(--brand); color: #fff;
  font-size: 11px; font-weight: 700;
  padding: 4px 8px; border-radius: 10px;
}
.dur {
  position: absolute; left: 6px; bottom: 6px;
  background: rgba(0, 0, 0, 0.5); color: #fff;
  font-size: 11px; padding: 2px 6px; border-radius: 6px;
}
.tcard p { margin: 8px 0 0; font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tcard .tcat { font-size: 11px; color: var(--weak); margin-top: 2px; display: block; }
@media (min-width: 768px) {
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 20px;
    padding: 24px;
  }
  .tcard { width: auto; }
}
@media (min-width: 1200px) {
  .grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
}
.pagination-wrap { display: flex; justify-content: center; padding: 8px 0 24px; }
</style>
