<script setup>
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, NTag, createDiscreteApi } from 'naive-ui'
import adminApi from '@/api/admin'

const { notification } = createDiscreteApi(['notification'])

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const query = reactive({
  pageNum: 1,
  pageSize: 10,
  keyword: '',
  status: null
})

// status: 1待支付 2已支付 3已交付 4已取消 5退款中 6已退款
const statusMap = {
  1: { label: '待支付', type: 'default' },
  2: { label: '已支付', type: 'success' },
  3: { label: '已交付', type: 'info' },
  4: { label: '已取消', type: 'default' },
  5: { label: '退款中', type: 'warning' },
  6: { label: '已退款', type: 'error' }
}

const statusOptions = [
  { label: '全部', value: null },
  ...Object.entries(statusMap).map(([value, s]) => ({ label: s.label, value: Number(value) }))
]

const fetchList = async () => {
  loading.value = true
  try {
    const res = await adminApi.orderList({
      pageNum: query.pageNum,
      pageSize: query.pageSize,
      status: query.status ?? undefined,
      keyword: query.keyword || undefined
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

// 退款弹窗
const refundVisible = ref(false)
const refundLoading = ref(false)
const refundForm = reactive({
  order_no: '',
  reason: ''
})

const openRefund = (row) => {
  refundForm.order_no = row.order_no
  refundForm.reason = ''
  refundVisible.value = true
}

const handleRefund = async () => {
  refundLoading.value = true
  try {
    const res = await adminApi.orderRefund({
      order_no: refundForm.order_no,
      reason: refundForm.reason || undefined
    })
    if (res.code === 1) {
      notification.success({ title: '提示', duration: 2000, content: '退款申请已提交' })
      refundVisible.value = false
      fetchList()
    }
  } finally {
    refundLoading.value = false
  }
}

// 退款查询(回调丢失兜底)
const refundQuerying = ref('')
const handleRefundQuery = async (row) => {
  refundQuerying.value = row.order_no
  try {
    const res = await adminApi.orderRefundQuery({ order_no: row.order_no })
    if (res.code === 1) {
      notification.success({ title: '退款查询', duration: 3000, content: res.message || '退款状态已同步' })
      fetchList()
    }
  } finally {
    refundQuerying.value = ''
  }
}

const columns = [
  { title: '订单号', key: 'order_no', width: 200, ellipsis: { tooltip: true } },
  { title: '商品', key: 'package_name', minWidth: 130, ellipsis: { tooltip: true }, render: (row) => row.package_name || '-' },
  {
    title: '金额',
    key: 'amount',
    width: 100,
    render: (row) => h('span', { style: 'color:var(--brand);font-weight:600;' }, `¥${row.amount ?? '0'}`)
  },
  { title: '网关', key: 'gateway', width: 90, render: (row) => row.gateway || '-' },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => {
      const s = statusMap[row.status] || { label: `未知(${row.status})`, type: 'default' }
      return h(NTag, { size: 'small', type: s.type, bordered: false }, { default: () => s.label })
    }
  },
  { title: '支付时间', key: 'pay_time', width: 170, render: (row) => row.pay_time || '-' },
  { title: '退款原因/备注', key: 'remark', minWidth: 140, ellipsis: { tooltip: true }, render: (row) => row.remark || '-' },
  { title: '创建时间', key: 'create_time', width: 170 },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => {
      const btns = []
      if (row.status === 2 || row.status === 3) {
        btns.push(h(NButton, { size: 'small', type: 'warning', quaternary: true, onClick: () => openRefund(row) }, { default: () => '退款' }))
      }
      if (row.status === 5) {
        btns.push(h(NButton, {
          size: 'small',
          type: 'info',
          quaternary: true,
          loading: refundQuerying.value === row.order_no,
          onClick: () => handleRefundQuery(row)
        }, { default: () => '退款查询' }))
      }
      return btns.length ? h('div', { style: 'display:flex;gap:8px;' }, btns) : h('span', { style: 'color:#9B9B9B;' }, '-')
    }
  }
]

onMounted(fetchList)
</script>

<template>
  <div>
    <n-card :bordered="false" class="page-card">
      <div class="toolbar">
        <n-input
          v-model:value="query.keyword"
          placeholder="搜索订单号 / 商品名"
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

    <n-modal
      v-model:show="refundVisible"
      preset="card"
      title="发起退款"
      style="width: 460px"
      :mask-closable="false"
    >
      <n-form label-placement="left" label-width="80">
        <n-form-item label="订单号">
          <n-input :value="refundForm.order_no" disabled />
        </n-form-item>
        <n-form-item label="退款原因">
          <n-input
            v-model:value="refundForm.reason"
            type="textarea"
            :rows="3"
            placeholder="请输入退款原因(选填)"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display:flex;justify-content:flex-end;gap:12px;">
          <n-button @click="refundVisible = false">取消</n-button>
          <n-button type="warning" :loading="refundLoading" @click="handleRefund">确认退款</n-button>
        </div>
      </template>
    </n-modal>
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
