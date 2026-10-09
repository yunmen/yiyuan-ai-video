<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import api from '@/api'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ pageNum: 1, pageSize: 12, status: null })

const filters = [
  { label: '全部', value: null },
  { label: '生成中', value: 'processing' },
  { label: '已完成', value: 'success' },
  { label: '失败', value: 'failed' },
]
const activeFilter = ref(null)

const statusText = { processing: '生成中', success: '已完成', failed: '失败' }

// 作品标题:视频任务取模板标题,数字人任务取数字人名称,视频换口播取提示词
function itemTitle(item) {
  if (item?.template_title) return item.template_title
  if (item?.params?.digital_name) return item.params.digital_name
  if (item?.type === 'digital') return '数字人口播'
  if (item?.type === 'render') return item?.params?.prompt || '视频换口播'
  return '未命名作品'
}

// 下载扩展名按结果形态推导:图片/音频此前会被写成 .mp4,下载后打不开(与 Generate.vue 的 EXT_BY_KIND 保持一致)
const EXT_BY_KIND = { video: 'mp4', image: 'png', audio: 'mp3' }
function itemExt(item) {
  const t = item?.type
  if (t === 'image' || t === 'audio') return EXT_BY_KIND[t]
  return 'mp4'
}

const countText = computed(() => {
  if (!activeFilter.value) return `${total.value} 个作品`
  return `${total.value} 个${statusText[activeFilter.value]}作品`
})

// 剩余额度:复用全局 store(与顶部额度、个人中心同源),不再单独请求
const creditTotal = computed(() => userStore.creditTotal)

// 无封面作品使用设计稿占位图轮播,保证瀑布流不出现空图
const FALLBACK_COVERS = ['/assets/hero-main.jpg', '/assets/digital-avatars.jpg', '/assets/studio-workflow.jpg']
function coverOf(item, i) {
  return item?.template_cover || FALLBACK_COVERS[i % FALLBACK_COVERS.length]
}

// 时长角标:接口返回秒数时格式化为 mm:ss;生成中固定占位 --:--
function durationText(item) {
  if (item?.status === 'processing') return '--:--'
  const raw = item?.duration
  if (raw == null || raw === '') return ''
  if (typeof raw === 'string' && raw.includes(':')) return raw
  const s = Number(raw)
  if (!s || !isFinite(s)) return ''
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(Math.floor(s % 60)).padStart(2, '0')}`
}

async function loadList() {
  loading.value = true
  try {
    const params = { ...query }
    if (!params.status) delete params.status
    const res = await api.task.list.post(params)
    if (res.code === 1) {
      list.value = res.data || []
      total.value = res.total || 0
    }
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
}

function onFilter(value) {
  if (activeFilter.value === value) return
  activeFilter.value = value
  query.status = value
  query.pageNum = 1
  loadList()
}

function onPageChange(page) {
  query.pageNum = page
  loadList()
}

function onView(item) {
  router.push(`/generate/${item.id}`)
}

function onDownload(item) {
  if (!item.result_video) { window.$message?.warning('视频还未生成'); return }
  const link = document.createElement('a')
  link.href = item.result_video
  link.download = `${itemTitle(item)}_${Date.now()}.${itemExt(item)}`
  link.target = '_blank'
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.$message?.success('已开始下载')
}

async function onDelete(item) {
  window.$dialog?.warning({
    title: '删除确认',
    content: `确定删除「${itemTitle(item)}」吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = await api.task.delete.post({ id: item.id })
        if (res.code === 1) {
          window.$message?.success('已删除')
          loadList()
        }
      } catch (e) { /* 拦截器已提示 */ }
    }
  })
}

onMounted(() => {
  if (!userStore.isLoggedIn) {
    userStore.openLogin()
    return
  }
  loadList()
})
</script>

<template>
  <div class="works-page">
    <!-- 移动端顶部标题栏(桌面端由全局 AppHeader 承担,>=768px 隐藏) -->
    <header class="page-head">
      <h1 class="ph-title">我的作品</h1>
      <div class="ph-right">
        <button class="search-btn" aria-label="搜索">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7"></circle>
            <line x1="16.5" y1="16.5" x2="21" y2="21"></line>
          </svg>
        </button>
      </div>
    </header>

    <div class="wrap">
      <!-- 剩余额度条 -->
      <div class="balance-bar" @click="router.push('/balance')">
        <div class="bb-left">
          <div class="bb-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"></path>
            </svg>
          </div>
          <div class="bb-info">
            <div class="bb-label">剩余额度</div>
            <div class="bb-num">{{ creditTotal === null ? '—' : creditTotal }}<span>次</span></div>
          </div>
        </div>
        <button class="bb-btn" @click.stop="router.push('/balance')">充值</button>
      </div>

      <!-- 筛选 Tab(与设计稿 全部 / 生成中 / 已完成 / 失败 一一对应) -->
      <div class="filters">
        <button
          v-for="f in filters"
          :key="f.label"
          class="ftab"
          :class="{ on: activeFilter === f.value }"
          @click="onFilter(f.value)"
        >{{ f.label }}</button>
        <span class="filters-count">{{ countText }}</span>
      </div>

      <n-spin :show="loading">
        <!-- 空状态 -->
        <div v-if="!loading && !list.length" class="empty">
          <div class="empty-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="2" width="20" height="20" rx="2.5"></rect>
              <line x1="7" y1="2" x2="7" y2="22"></line>
              <line x1="17" y1="2" x2="17" y2="22"></line>
              <line x1="2" y1="12" x2="22" y2="12"></line>
              <line x1="2" y1="7" x2="7" y2="7"></line>
              <line x1="2" y1="17" x2="7" y2="17"></line>
              <line x1="17" y1="7" x2="22" y2="7"></line>
              <line x1="17" y1="17" x2="22" y2="17"></line>
            </svg>
          </div>
          <h3 class="empty-title">暂无作品</h3>
          <p class="empty-desc">去创作一个属于你的 AI 视频吧</p>
          <button class="empty-btn" @click="router.push('/studio')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9L12 3z"></path>
            </svg>
            立即创作
          </button>
        </div>

        <!-- 作品列表(2 列瀑布流) -->
        <template v-else>
          <div class="grid">
            <div v-for="(item, idx) in list" :key="item.id" class="wcard">
              <div class="cov" @click="onView(item)">
                <!-- 失败且无封面:展示占位图标 -->
                <div v-if="item.status === 'failed' && !item.template_cover" class="cov-empty">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="3" width="18" height="18" rx="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <path d="M21 15l-5-5L5 21"></path>
                    <line x1="3" y1="3" x2="21" y2="21"></line>
                  </svg>
                </div>
                <img v-else class="cov-img" :src="coverOf(item, idx)" :alt="itemTitle(item)" />

                <!-- 时长角标 -->
                <span v-if="durationText(item)" class="duration-badge">{{ durationText(item) }}</span>

                <!-- 生成中遮罩 -->
                <div v-if="item.status === 'processing'" class="proc-mask">
                  <div class="proc-spin">
                    <span class="ring ring-1"></span>
                    <span class="ring ring-2"></span>
                    <span class="proc-pct">{{ item.progress || 0 }}%</span>
                  </div>
                  <span class="proc-text">AI 生成中</span>
                  <div class="proc-bar">
                    <div class="proc-bar-fill" :style="{ width: (item.progress || 0) + '%' }"></div>
                  </div>
                </div>

                <!-- 生成中脉冲光点 -->
                <span v-if="item.status === 'processing'" class="pulse"></span>

                <!-- 状态标签 -->
                <span class="badge" :class="'b-' + item.status">
                  <svg v-if="item.status === 'success'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9"></circle>
                    <path d="M8.5 12.5l2.3 2.3 4.7-4.8"></path>
                  </svg>
                  <svg v-else-if="item.status === 'failed'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9"></circle>
                    <line x1="12" y1="8" x2="12" y2="13"></line>
                    <circle cx="12" cy="16.3" r="0.6" fill="currentColor"></circle>
                  </svg>
                  <svg v-else width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9"></circle>
                    <path d="M12 7v5l3 2"></path>
                  </svg>
                  {{ statusText[item.status] || item.status }}
                </span>
              </div>

              <div class="meta">
                <b class="title" :title="itemTitle(item)" @click="onView(item)">{{ itemTitle(item) }}</b>
                <div class="meta-row">
                  <span class="time">{{ item.create_time }}</span>
                  <!-- 参考图含真人时已被本地处理(丢弃改按文字描述/拟态化):替换目标的呈现方式被改变,须让用户知情 -->
                  <span v-if="item.deidentify_note" class="deid-tag">已打码</span>
                  <span v-if="item.image_note" class="deid-tag" :title="item.image_note">参考图已处理</span>
                  <!-- 降级标记:成片并未替换原视频元素,必须在列表里就能看出来 -->
                  <span v-if="item.degrade_note" class="deid-tag degrade-tag" :title="item.degrade_note">未替换</span>
                </div>
                <div class="ops">
                  <button class="op" :disabled="!item.result_video" @click="onDownload(item)">下载</button>
                  <button class="op danger" @click="onDelete(item)">删除</button>
                </div>
              </div>
            </div>
          </div>
          <div v-if="total > query.pageSize" class="pagination-wrap">
            <n-pagination
              v-model:page="query.pageNum"
              :item-count="total"
              :page-size="query.pageSize"
              :show-size-picker="false"
              @update:page="onPageChange"
            />
          </div>
        </template>
      </n-spin>
    </div>
  </div>
</template>

<style scoped>
.works-page {
  min-height: calc(100vh - var(--header-h));
  background: var(--bg);
  /* 底部 Tab 导航为固定定位,预留出不被遮挡的滚动空间 */
  padding-bottom: calc(var(--nav-h) + 24px + env(safe-area-inset-bottom));
}
.wrap { max-width: var(--page-max); margin: 0 auto; padding: var(--s-4) var(--s-4) 0; }

/* 移动端顶部标题栏:左标题 + 右搜索按钮 */
.page-head .ph-title {
  text-align: left;
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--ink);
}
.search-btn {
  width: 40px;
  height: 40px;
  margin-right: -8px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--ink-3);
  cursor: pointer;
  transition: background var(--transition-fast);
}
.search-btn:hover { background: var(--line-2); }

/* 剩余额度条 */
.balance-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  padding: 14px var(--s-4);
  border-radius: var(--radius-lg);
  background: var(--grad-brand);
  color: #fff;
  box-shadow: var(--shadow-brand);
  margin-bottom: var(--s-4);
  cursor: pointer;
}
.bb-left { display: flex; align-items: center; gap: var(--s-3); min-width: 0; }
.bb-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, .2);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}
.bb-info { min-width: 0; }
.bb-label { font-size: 12px; opacity: .75; margin-bottom: 2px; }
.bb-num { font-size: 18px; font-weight: 700; line-height: 1.1; }
.bb-num span { font-size: 13px; font-weight: 400; opacity: .75; margin-left: 4px; }
.bb-btn {
  flex-shrink: 0;
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-pill);
  background: #fff;
  color: var(--brand);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.bb-btn:hover { background: var(--line-2); }

/* 筛选 Tab:下划线指示器 */
.filters {
  display: flex;
  align-items: center;
  gap: var(--s-6);
  margin: 0 calc(-1 * var(--s-4)) var(--s-4);
  padding: 0 var(--s-4);
  border-bottom: 1px solid var(--line);
  overflow-x: auto;
}
.filters-count { margin-left: auto; font-size: 12px; color: var(--weak); white-space: nowrap; }
.ftab {
  position: relative;
  padding: 10px 4px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--body-2);
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition: color var(--transition-fast);
}
.ftab:hover { color: var(--brand); }
.ftab.on { color: var(--ink); font-weight: 600; }
.ftab.on::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 3px;
  border-radius: 2px;
  background: var(--grad-brand);
}

/* 空状态 */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 64px var(--s-5);
}
.empty-icon {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: var(--grad-brand-soft);
  color: var(--brand);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--s-5);
}
.empty-title { margin: 0 0 var(--s-2); font-size: 16px; font-weight: 600; color: var(--ink-2); }
.empty-desc { margin: 0 0 var(--s-6); font-size: 14px; color: var(--body-2); }
.empty-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 32px;
  border: none;
  border-radius: var(--radius-pill);
  background: var(--grad-brand);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-brand-lg);
  transition: transform var(--transition-fast);
}
.empty-btn:active { transform: scale(.98); }

/* 瀑布流网格 */
.grid { column-count: 2; column-gap: var(--s-3); }
.wcard {
  break-inside: avoid;
  margin-bottom: var(--s-3);
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}
.wcard:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }

.cov { position: relative; overflow: hidden; background: var(--line-2); cursor: pointer; }
.wcard:nth-child(3n + 1) .cov { aspect-ratio: 3 / 4; }
.wcard:nth-child(3n + 2) .cov { aspect-ratio: 4 / 5; }
.wcard:nth-child(3n) .cov { aspect-ratio: 9 / 16; }
.cov-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.cov-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--line-2);
  color: var(--weak);
}

/* 时长角标 */
.duration-badge {
  position: absolute;
  right: var(--s-2);
  bottom: var(--s-2);
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0, 0, 0, .65);
  color: #fff;
  font-size: 11px;
  line-height: 1.4;
  backdrop-filter: blur(4px);
}

/* 生成中遮罩 */
.proc-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--s-2);
  background: rgba(0, 0, 0, .4);
  backdrop-filter: blur(2px);
}
.proc-spin { position: relative; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; }
.proc-spin .ring { position: absolute; inset: 0; border-radius: 50%; border: 2px solid transparent; }
.proc-spin .ring-1 { border-color: rgba(255, 255, 255, .2); }
.proc-spin .ring-2 {
  border-top-color: #fff;
  border-right-color: #fff;
  animation: works-spin 1.2s linear infinite;
}
.proc-pct { color: #fff; font-size: 12px; font-weight: 700; }
.proc-text { color: #fff; font-size: 12px; font-weight: 500; }
.proc-bar { width: 70%; height: 4px; border-radius: var(--radius-pill); background: rgba(255, 255, 255, .2); overflow: hidden; }
.proc-bar-fill { height: 100%; border-radius: var(--radius-pill); background: #fff; transition: width var(--transition-base); }
@keyframes works-spin { to { transform: rotate(360deg); } }

/* 生成中脉冲光点 */
.pulse {
  position: absolute;
  top: var(--s-2);
  right: var(--s-2);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--warning);
}
.pulse::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: var(--warning);
  animation: works-ping 1.4s cubic-bezier(0, 0, .2, 1) infinite;
}
@keyframes works-ping { 75%, 100% { transform: scale(2); opacity: 0; } }

/* 状态标签 */
.badge {
  position: absolute;
  top: var(--s-2);
  left: var(--s-2);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 500;
}
.badge.b-processing { background: var(--info-bg); color: var(--info); }
.badge.b-success { background: var(--success-bg); color: var(--success); }
.badge.b-failed { background: var(--danger-bg); color: var(--danger); }

/* 卡片信息 */
.meta { padding: var(--s-3); }
.meta .title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
  color: var(--ink);
  cursor: pointer;
  margin-bottom: 6px;
}
.meta-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.meta .time { font-size: 11px; color: var(--weak); }
.meta .deid-tag {
  font-size: 10px;
  color: var(--brand);
  background: var(--brand-bg);
  padding: 1px 6px;
  border-radius: var(--radius-xs);
}
.meta .degrade-tag { color: var(--danger); background: var(--danger-bg); }

.ops { display: flex; gap: var(--s-2); margin-top: var(--s-3); }
.op {
  flex: 1;
  height: 30px;
  border: 1px solid var(--line);
  border-radius: var(--radius-pill);
  background: var(--bg-elev);
  color: var(--body-c);
  font-size: 12px;
  cursor: pointer;
  transition: color var(--transition-fast), border-color var(--transition-fast);
}
.op:hover:not(:disabled) { color: var(--brand); border-color: var(--brand); }
.op:disabled { opacity: .45; cursor: not-allowed; }
.op.danger:hover { color: var(--danger); border-color: var(--danger); }

.pagination-wrap { display: flex; justify-content: center; padding: var(--s-5) 0 var(--s-2); }

/* 桌面端:隐藏移动标题栏,内容居中并放宽为 4-5 列 */
@media (min-width: 768px) {
  .page-head { display: none; }
  .wrap { padding: var(--s-6) var(--s-6) 0; }
  .works-page { padding-bottom: 80px; }
  .filters { margin-left: 0; margin-right: 0; padding: 0; overflow-x: visible; }
  .grid { column-count: 4; column-gap: var(--s-5); }
  .wcard { margin-bottom: var(--s-5); }
}
@media (min-width: 1200px) {
  .grid { column-count: 5; }
}
</style>
