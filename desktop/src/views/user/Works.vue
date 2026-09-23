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

// 作品标题:视频任务取模板标题,数字人任务取数字人名称
function itemTitle(item) {
  return item?.template_title || item?.params?.digital_name || (item?.type === 'digital' ? '数字人口播' : '未命名作品')
}

const countText = computed(() => {
  if (!activeFilter.value) return `${total.value} 个作品`
  return `${total.value} 个${statusText[activeFilter.value]}作品`
})

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
  link.download = `视频_${itemTitle(item)}_${Date.now()}.mp4`
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
    <div class="wrap">
      <div class="page-head">
        <div>
          <h2>我的作品</h2>
          <span class="sub">{{ countText }}</span>
        </div>
        <button class="create-btn" @click="router.push('/templates')">
          <svg width="16" height="16" viewBox="0 0 16 16"><path d="M8 3V13M3 8H13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          新建视频
        </button>
      </div>

      <div class="filters">
        <div
          v-for="f in filters"
          :key="f.label"
          class="ftab"
          :class="{ on: activeFilter === f.value }"
          @click="onFilter(f.value)"
        >{{ f.label }}</div>
      </div>

      <n-spin :show="loading">
        <!-- 空状态 -->
        <div v-if="!loading && !list.length" class="empty">
          <svg width="96" height="96" viewBox="0 0 96 96">
            <rect x="14" y="22" width="68" height="50" rx="10" stroke="#D8DADE" stroke-width="3" fill="none"/>
            <path d="M14 38H82" stroke="#D8DADE" stroke-width="3"/>
            <circle cx="34" cy="30" r="3" fill="#D8DADE"/><circle cx="44" cy="30" r="3" fill="#D8DADE"/>
            <path d="M40 46L54 54L40 62V46Z" fill="#E3E5E8"/>
          </svg>
          <div class="empty-text">还没有作品，去做第一条爆款视频吧</div>
          <div class="go-btn" @click="router.push('/templates')">去制作</div>
        </div>

        <!-- 作品列表 -->
        <template v-else>
          <div class="grid">
            <div v-for="item in list" :key="item.id" class="wcard">
              <div class="cov" :style="item.template_cover ? { backgroundImage: `url(${item.template_cover})` } : {}" @click="onView(item)">
                <svg width="34" height="34" viewBox="0 0 34 34">
                  <circle cx="17" cy="17" r="15" fill="rgba(0,0,0,.3)"/>
                  <path d="M13.5 11L23 17L13.5 23V11Z" fill="#fff"/>
                </svg>
                <span class="badge" :class="item.status">
                  {{ statusText[item.status] || item.status }}
                  <template v-if="item.status === 'processing'"> {{ item.progress }}%</template>
                </span>
              </div>
              <div class="meta">
                <b :title="itemTitle(item)" @click="onView(item)">{{ itemTitle(item) }}</b>
                <span class="time">{{ item.create_time }}</span>
                <span v-if="item.deidentify_note" class="deid-tag">已打码</span>
                <!-- 降级标记:成片并未替换原视频元素,必须在列表里就能看出来 -->
                <span v-if="item.degrade_note" class="deid-tag degrade-tag" :title="item.degrade_note">未替换</span>
              </div>
              <div class="ops">
                <button class="op" :disabled="!item.result_video" @click="onDownload(item)">下载</button>
                <button class="op danger" @click="onDelete(item)">删除</button>
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
.works-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding-bottom: 80px; }
.wrap { max-width: var(--page-max); margin: 0 auto; padding: 16px; }

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.page-head h2 { margin: 0; font-size: 20px; font-weight: 700; }
.page-head .sub { font-size: 12px; color: var(--weak); }
.create-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 18px;
  border: none;
  border-radius: 19px;
  background: var(--brand);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(255, 77, 28, .22);
}
.create-btn:hover { background: var(--brand-l); }

.filters {
  display: flex;
  gap: 8px;
  margin: 16px 0;
  overflow-x: auto;
}
.ftab {
  height: 32px;
  padding: 0 16px;
  border-radius: 16px;
  background: #fff;
  color: var(--body-c);
  font-size: 13px;
  display: flex;
  align-items: center;
  white-space: nowrap;
  cursor: pointer;
  transition: background .15s, color .15s;
}
.ftab:hover { color: var(--brand); }
.ftab.on { background: var(--brand); color: #fff; font-weight: 600; }

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 70px 20px;
  background: #fff;
  border-radius: var(--radius-lg);
}
.empty-text { font-size: 14px; color: var(--weak); }
.go-btn {
  width: 160px; height: 44px; border-radius: 22px;
  background: var(--brand); color: #fff; font-size: 15px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.wcard {
  background: #fff;
  border-radius: var(--radius);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: var(--shadow-sm);
  transition: transform .2s, box-shadow .2s;
}
.wcard:hover { transform: translateY(-3px); box-shadow: var(--shadow-brand); }
.cov {
  aspect-ratio: 16 / 10;
  border-radius: 10px;
  position: relative;
  background: linear-gradient(135deg, #FFCDB0, #FF8347);
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
}
.badge {
  position: absolute;
  left: 8px;
  top: 8px;
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  background: rgba(0, 0, 0, .45);
}
.badge.processing { background: var(--brand); }
.badge.success { background: #18A058; }
.badge.failed { background: #D03050; }
.meta { min-width: 0; }
.meta b {
  font-size: 13px;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
.meta .time { font-size: 11px; color: var(--weak); margin-top: 4px; display: block; }
.meta .deid-tag { font-size: 11px; color: #fff; background: var(--brand); padding: 1px 7px; border-radius: 6px; align-self: flex-start; }
.meta .degrade-tag { background: #d03050; }
.ops { display: flex; gap: 8px; }
.op {
  flex: 1;
  height: 30px;
  border: 1px solid var(--line);
  border-radius: 15px;
  background: #fff;
  color: var(--body-c);
  font-size: 12px;
  cursor: pointer;
  transition: color .15s, border-color .15s;
}
.op:hover:not(:disabled) { color: var(--brand); border-color: var(--brand); }
.op:disabled { opacity: .45; cursor: not-allowed; }
.op.danger:hover { color: #D03050; border-color: #D03050; }
.pagination-wrap { display: flex; justify-content: center; padding: 20px 0 8px; }

@media (min-width: 768px) {
  .wrap { padding: 24px; }
  .filters { overflow-x: visible; }
  .grid { grid-template-columns: repeat(4, 1fr); gap: 18px; }
}
@media (min-width: 1200px) {
  .grid { grid-template-columns: repeat(5, 1fr); }
}
</style>
