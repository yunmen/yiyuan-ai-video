<script setup>
import { h, onMounted, reactive, ref } from 'vue'
import { NProgress, NTag } from 'naive-ui'
import adminApi from '@/api/admin'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const query = reactive({
  pageNum: 1,
  pageSize: 10,
  keyword: '',
  status: null
})

const statusOptions = [
  { label: '全部', value: null },
  { label: '生成中', value: 'processing' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' }
]

const statusMap = {
  processing: { label: '生成中', type: 'warning' },
  success: { label: '成功', type: 'success' },
  failed: { label: '失败', type: 'error' }
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await adminApi.taskList({
      pageNum: query.pageNum,
      pageSize: query.pageSize,
      status: query.status || undefined,
      task_no: query.keyword || undefined
    })
    if (res.code === 1) {
      tableData.value = res.data || []
      total.value = res.total || 0
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  query.pageNum = 1
  fetchList()
}

const handleReset = () => {
  query.keyword = ''
  query.status = null
  query.pageNum = 1
  fetchList()
}

const handlePageChange = (page) => {
  query.pageNum = page
  fetchList()
}

const handlePageSizeChange = (pageSize) => {
  query.pageSize = pageSize
  query.pageNum = 1
  fetchList()
}

const columns = [
  { title: '任务号', key: 'task_no', width: 200, ellipsis: { tooltip: true } },
  { title: '模板ID', key: 'template_id', width: 90 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => {
      const s = statusMap[row.status] || { label: row.status || '-', type: 'default' }
      return h(NTag, { size: 'small', type: s.type, bordered: false }, { default: () => s.label })
    }
  },
  {
    title: '进度',
    key: 'progress',
    width: 140,
    render: (row) => row.status === 'processing'
      ? h(NProgress, { type: 'line', percentage: row.progress ?? 0, height: 10, processing: true })
      : h('span', null, `${row.progress ?? (row.status === 'success' ? 100 : 0)}%`)
  },
  {
    title: '失败原因',
    key: 'fail_reason',
    minWidth: 140,
    ellipsis: { tooltip: true },
    render: (row) => row.fail_reason || h('span', { style: 'color:#9B9B9B;' }, '-')
  },
  { title: '设备', key: 'device', width: 90 },
  { title: '用户ID', key: 'user_id', width: 90, render: (row) => row.user_id ?? '-' },
  { title: '订单号', key: 'order_no', width: 180, ellipsis: { tooltip: true }, render: (row) => row.order_no || '-' },
  { title: '创建时间', key: 'create_time', width: 170 }
]

onMounted(fetchList)
</script>

<template>
  <div>
    <n-card :bordered="false" class="page-card">
      <div class="toolbar">
        <n-input
          v-model:value="query.keyword"
          placeholder="搜索任务号"
          clearable
          style="width: 240px"
          @keyup.enter="handleSearch"
        />
        <n-select
          v-model:value="query.status"
          :options="statusOptions"
          style="width: 130px"
        />
        <n-button type="primary" class="brand-btn" @click="handleSearch">搜索</n-button>
        <n-button @click="handleReset">重置</n-button>
        <div class="toolbar-right">
          <n-button @click="fetchList">刷新</n-button>
        </div>
      </div>

      <n-data-table
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :row-key="(row) => row.id"
        :pagination="false"
      />
      <div class="pager">
        <n-pagination
          :page="query.pageNum"
          :page-size="query.pageSize"
          :item-count="total"
          show-size-picker
          :page-sizes="[10, 20, 50]"
          @update:page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </div>
    </n-card>
  </div>
</template>

<style scoped>
.page-card {
  border-radius: 8px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.toolbar-right {
  margin-left: auto;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.brand-btn {
  --n-color: var(--brand) !important;
  --n-color-hover: #e6451a !important;
  --n-color-pressed: #cc3e17 !important;
  --n-color-focus: var(--brand) !important;
  --n-ripple-color: var(--brand) !important;
  --n-border: 1px solid var(--brand) !important;
  --n-border-hover: 1px solid var(--brand) !important;
  --n-border-pressed: 1px solid var(--brand) !important;
  --n-border-focus: 1px solid var(--brand) !important;
}
</style>
