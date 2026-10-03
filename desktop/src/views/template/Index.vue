<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { setPendingRef } from '@/utils/pendingRef'

const router = useRouter()
const loading = ref(false)
// 模板列表加载失败标记:用于空状态展示「重新加载」入口
const loadFailed = ref(false)

// 模板库只保留「选模板做」一种方式:
// 「用户上传视频做」已由工作台「视频复刻」标签承载(含上传、拆解、局部重跑),
// 这里不再提供第二个上传入口,避免同一能力两个入口造成割裂。
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
  loadFailed.value = false
  try {
    const res = await api.template.list.post({ ...query })
    if (res.code === 1) {
      templates.value = res.data || []
      total.value = res.total || 0
    } else {
      loadFailed.value = true
      window.$message?.error(res.message || '模板加载失败，请重试')
    }
  } catch (e) { /* 拦截器已提示 */
    loadFailed.value = true
  }
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

// 选模板做:与首页热门模板一致 —— 模板有成片视频则直通工作台「视频复刻」,
// 并把模板视频预填为对标视频,用户只需上传替换参考图;
// 无成片视频的模板回退到模板替换流程页,避免落空。
// 视频地址经 sessionStorage 中转,不拼进 URL,避免暴露 OSS 存储桶链接。
function useTemplate(t) {
  if (t.video_url) {
    setPendingRef({ url: t.video_url, title: t.title })
    router.push('/studio/replicate')
  } else {
    router.push(`/upload/${t.id}`)
  }
}

// 无封面时提取最能代表模板内容的一句话作为封面副标题
function coverSubtitle(item) {
  const parts = item.prompt_parts || {}
  const setting = (parts.setting || '').trim()
  if (setting) return setting
  const dt = item.default_text || {}
  return (dt.title || dt.subtitle || '').trim() || (item.category || '')
}

// 取前两个标签用于封面展示
function coverTags(item) {
  return (item.tags || []).slice(0, 2)
}

// 示例视频首帧:媒体片段 #t=0.1 让浏览器加载元数据时就渲染该帧,不用真正播放
function videoPoster(url) {
  if (!url) return ''
  return url.includes('#') ? url : `${url}#t=0.1`
}

// 示例视频加载失败(失效地址/跨域限制)时按 id 记录,回退到文字兜底,避免留黑块
const videoErr = ref({})
function onVideoError(id) {
  videoErr.value = { ...videoErr.value, [id]: true }
}

onMounted(() => {
  loadCategories()
  loadList()
})
</script>

<template>
  <div class="tpl-page">
    <!-- 选模板做:点模板即带着模板成片进入工作台「视频复刻」,无需用户再上传视频 -->
    <div>
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
            <div v-for="t in templates" :key="t.id" class="tcard" @click="useTemplate(t)">
              <div class="cover" :style="t.cover ? { backgroundImage: `url(${t.cover})` } : {}">
                <video
                  v-if="!t.cover && t.video_url && !videoErr[t.id]"
                  class="cover-video"
                  :src="videoPoster(t.video_url)"
                  muted playsinline preload="metadata" disablepictureinpicture
                  @error="onVideoError(t.id)"
                ></video>
                <div v-else-if="!t.cover" class="cover-info">
                  <div class="cover-cat">{{ t.category }}</div>
                  <div class="cover-title">{{ t.title }}</div>
                  <div class="cover-sub">{{ coverSubtitle(t) }}</div>
                  <div v-if="coverTags(t).length" class="cover-tags">
                    <span v-for="tag in coverTags(t)" :key="tag" class="cover-tag">{{ tag }}</span>
                  </div>
                </div>
                <div class="play" :class="{ 'play-on-info': !t.cover }">
                  <svg width="18" height="18" viewBox="0 0 18 18"><path d="M6 3L14 9L6 15V3Z" fill="#fff"/></svg>
                </div>
                <div class="tag">做同款</div>
                <div v-if="t.duration" class="dur">{{ t.duration }}s</div>
              </div>
              <p>{{ t.title }}</p>
              <span v-if="t.category" class="tcat">{{ t.category }}</span>
            </div>
          </div>
          <n-empty v-else-if="!loading && !loadFailed" description="该分类模板整理中，先看看其他分类" style="padding:60px 0" />
          <div v-else-if="!loading && loadFailed" class="load-fail">
            <p>模板加载失败</p>
            <button class="retry-btn" @click="loadList">重新加载</button>
          </div>
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
    </div>
  </div>
</template>

<style scoped>
.tpl-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding-bottom: 80px; }
.wrap { max-width: var(--page-max); margin: 0 auto; }


/* 分类条(原「模式切换」条已移除:上传视频链路统一由工作台「视频复刻」承载) */
.cats-bar {
  background: #fff;
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: var(--header-h);
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
  border-radius: var(--radius-lg);
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
.play-on-info {
  position: absolute; top: 10px; right: 10px;
  width: 30px; height: 30px;
  opacity: .75;
  z-index: 2;
}
.tcard:hover .play { transform: scale(1.08); }
.cover-video {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  pointer-events: none;
  z-index: 1;
}
.cover-info {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 12px 10px;
  color: #fff;
  text-align: center;
  text-shadow: 0 1px 3px rgba(0, 0, 0, .28);
  pointer-events: none;
  z-index: 1;
}
.cover-cat {
  font-size: 11px; opacity: .85; margin-bottom: 4px;
}
.cover-title {
  font-size: 15px; font-weight: 700; line-height: 1.25;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  margin-bottom: 6px;
}
.cover-sub {
  font-size: 12px; line-height: 1.3; opacity: .9;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  margin-bottom: 8px;
}
.cover-tags {
  display: flex; flex-wrap: wrap; gap: 4px; justify-content: center;
}
.cover-tag {
  font-size: 10px; padding: 2px 6px; border-radius: var(--radius-xs);
  background: rgba(255, 255, 255, .2);
}
.tag {
  position: absolute; right: 6px; bottom: 6px;
  background: var(--brand); color: #fff;
  font-size: 11px; font-weight: 700;
  padding: 4px 8px; border-radius: var(--radius-sm);
}
.dur {
  position: absolute; left: 6px; bottom: 6px;
  background: rgba(0, 0, 0, 0.5); color: #fff;
  font-size: 11px; padding: 2px 6px; border-radius: var(--radius-xs);
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

/* 模板加载失败:居中提示 + 重新加载 */
.load-fail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 64px 0;
  color: var(--weak);
  font-size: 14px;
}
.retry-btn {
  height: 40px;
  padding: 0 24px;
  border-radius: 20px;
  border: none;
  background: var(--brand);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
}
.retry-btn:hover { opacity: .9; }
</style>
