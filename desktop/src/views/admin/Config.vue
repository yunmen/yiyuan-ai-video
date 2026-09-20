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
  group: ''
})

const fetchList = async () => {
  loading.value = true
  try {
    const res = await adminApi.configList({
      pageNum: query.pageNum,
      pageSize: query.pageSize,
      keyword: query.keyword || undefined,
      group: query.group || undefined
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
  query.group = ''
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

// 新增/编辑弹窗(upsert:有 key 即更新,无则新增)
const modalVisible = ref(false)
const modalLoading = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = reactive({
  key: '',
  value: '',
  group: 'gen',
  remark: '',
  is_public: true
})

const formRules = {
  key: [{ required: true, message: '请输入配置键', trigger: 'blur' }],
  group: [{ required: true, message: '请输入配置分组', trigger: 'blur' }]
}

const openCreate = () => {
  isEdit.value = false
  Object.assign(form, { key: '', value: '', group: 'gen', remark: '', is_public: true })
  modalVisible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  Object.assign(form, {
    key: row.key,
    value: row.value ?? '',
    group: row.group || 'gen',
    remark: row.remark || '',
    is_public: !!row.is_public
  })
  modalVisible.value = true
}

const handleSubmit = () => {
  formRef.value?.validate(async (errors) => {
    if (errors) return
    modalLoading.value = true
    try {
      const res = await adminApi.configUpsert({ ...form })
      if (res.code === 1) {
        notification.success({ title: '提示', duration: 2000, content: '配置已保存,worker 每分钟热更新,无需重启' })
        modalVisible.value = false
        fetchList()
      }
    } finally {
      modalLoading.value = false
    }
  })
}

const columns = [
  { title: '配置键', key: 'key', minWidth: 180, ellipsis: { tooltip: true } },
  { title: '配置值', key: 'value', minWidth: 220, ellipsis: { tooltip: true }, render: (row) => row.value ?? '-' },
  {
    title: '分组',
    key: 'group',
    width: 100,
    render: (row) => h(NTag, { size: 'small', bordered: false, type: 'info' }, { default: () => row.group })
  },
  { title: '说明', key: 'remark', minWidth: 160, ellipsis: { tooltip: true }, render: (row) => row.remark || '-' },
  {
    title: '公开',
    key: 'is_public',
    width: 80,
    render: (row) => h(NTag, { size: 'small', bordered: false, type: row.is_public ? 'success' : 'default' }, { default: () => row.is_public ? '公开' : '私有' })
  },
  { title: '更新时间', key: 'update_time', width: 170 },
  {
    title: '操作',
    key: 'actions',
    width: 90,
    render: (row) => h(NButton, { size: 'small', type: 'primary', quaternary: true, onClick: () => openEdit(row) }, { default: () => '编辑' })
  }
]

onMounted(fetchList)
</script>

<template>
  <div>
    <n-alert type="info" :bordered="false" class="tip-alert">
      业务配置由 worker 每分钟热更新拉取,保存后无需重启服务即可生效。
    </n-alert>
    <n-card :bordered="false" class="page-card">
      <div class="toolbar">
        <n-input
          v-model:value="query.keyword"
          placeholder="搜索配置键 / 说明"
          clearable
          style="width: 220px"
          @keyup.enter="handleSearch"
        />
        <n-input
          v-model:value="query.group"
          placeholder="分组"
          clearable
          style="width: 140px"
          @keyup.enter="handleSearch"
        />
        <n-button type="primary" class="brand-btn" @click="handleSearch">搜索</n-button>
        <n-button @click="handleReset">重置</n-button>
        <div class="toolbar-right">
          <n-button type="primary" class="brand-btn" @click="openCreate">新增配置</n-button>
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

    <n-modal
      v-model:show="modalVisible"
      preset="card"
      :title="isEdit ? '编辑配置' : '新增配置'"
      style="width: 520px"
      :mask-closable="false"
    >
      <n-form ref="formRef" :model="form" :rules="formRules" label-placement="left" label-width="90">
        <n-form-item label="配置键" path="key">
          <n-input v-model:value="form.key" placeholder="如:video.price.hd" :disabled="isEdit" />
        </n-form-item>
        <n-form-item label="配置值" path="value">
          <n-input v-model:value="form.value" type="textarea" :rows="3" placeholder="配置值" />
        </n-form-item>
        <n-form-item label="分组" path="group">
          <n-input v-model:value="form.group" placeholder="如:gen" />
        </n-form-item>
        <n-form-item label="说明" path="remark">
          <n-input v-model:value="form.remark" placeholder="配置说明" />
        </n-form-item>
        <n-form-item label="是否公开" path="is_public">
          <n-switch v-model:value="form.is_public" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display:flex;justify-content:flex-end;gap:12px;">
          <n-button @click="modalVisible = false">取消</n-button>
          <n-button type="primary" class="brand-btn" :loading="modalLoading" @click="handleSubmit">保存</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.tip-alert {
  margin-bottom: 12px;
  border-radius: 8px;
}
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
