<script setup>
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, NImage, NPopconfirm, NSwitch, NTag, createDiscreteApi } from 'naive-ui'
import adminApi from '@/api/admin'

const { notification } = createDiscreteApi(['notification'])

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const query = reactive({
  pageNum: 1,
  pageSize: 10,
  keyword: '',
  category: '',
  active: null
})

const activeOptions = [
  { label: '全部', value: null },
  { label: '已上架', value: true },
  { label: '已下架', value: false }
]

const fetchList = async () => {
  loading.value = true
  try {
    const res = await adminApi.templateList({
      pageNum: query.pageNum,
      pageSize: query.pageSize,
      keyword: query.keyword || undefined,
      category: query.category || undefined,
      active: query.active
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
  query.category = ''
  query.active = null
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

// 新建/编辑弹窗
const modalVisible = ref(false)
const modalLoading = ref(false)
const editingRow = ref(null)
const formRef = ref(null)
const form = reactive({
  title: '',
  category: '',
  cover: '',
  video_url: '',
  duration: 10,
  desc: '',
  tags: [],
  sort: 0,
  active: true
})

const formRules = {
  title: [{ required: true, message: '请输入模板标题', trigger: 'blur' }],
  category: [{ required: true, message: '请输入模板分类', trigger: 'blur' }]
}

// 素材上传(封面图 / 示例视频),直传后端公共上传接口
const uploadingCover = ref(false)
const uploadingVideo = ref(false)
const coverInput = ref(null)
const videoInput = ref(null)

const handleFilePick = async (e, field, loadingRef) => {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  if (file.size > 50 * 1024 * 1024) {
    notification.warning({ title: '提示', duration: 2500, content: '文件大小不能超过 50MB' })
    return
  }
  loadingRef.value = true
  try {
    const data = await adminApi.uploadFile(file)
    form[field] = data.url
    notification.success({ title: '提示', duration: 2000, content: '上传成功' })
  } catch (err) {
    notification.error({ title: '上传失败', duration: 2500, content: err.message })
  } finally {
    loadingRef.value = false
  }
}

const resetForm = () => {
  Object.assign(form, {
    title: '',
    category: '',
    cover: '',
    video_url: '',
    duration: 10,
    desc: '',
    tags: [],
    sort: 0,
    active: true
  })
  editingRow.value = null
}

const openCreate = () => {
  resetForm()
  modalVisible.value = true
}

const openEdit = (row) => {
  resetForm()
  editingRow.value = row
  Object.assign(form, {
    title: row.title,
    category: row.category,
    cover: row.cover || '',
    video_url: row.video_url || '',
    duration: row.duration ?? 10,
    desc: row.desc || '',
    tags: Array.isArray(row.tags) ? [...row.tags] : [],
    sort: row.sort ?? 0,
    active: !!row.active
  })
  modalVisible.value = true
}

const handleSubmit = () => {
  formRef.value?.validate(async (errors) => {
    if (errors) return
    modalLoading.value = true
    try {
      // 后端 update 为全量覆盖,编辑时保留未在表单中的字段
      const payload = { ...form }
      if (editingRow.value) {
        payload.id = editingRow.value.id
        payload.hot = editingRow.value.hot ?? 0
        payload.use_count = editingRow.value.use_count ?? 0
        payload.example_images = Array.isArray(editingRow.value.example_images) ? editingRow.value.example_images : []
      }
      const res = editingRow.value
        ? await adminApi.templateUpdate(payload)
        : await adminApi.templateCreate(payload)
      if (res.code === 1) {
        notification.success({ title: '提示', duration: 2000, content: editingRow.value ? '模板已更新' : '模板已创建' })
        modalVisible.value = false
        fetchList()
      }
    } finally {
      modalLoading.value = false
    }
  })
}

// 上下架
const handleActive = async (row) => {
  const res = await adminApi.templateActive({ id: row.id })
  if (res.code === 1) {
    notification.success({ title: '提示', duration: 2000, content: res.data?.active ? '已上架' : '已下架' })
    fetchList()
  } else {
    fetchList()
  }
}

// 删除
const handleDelete = async (row) => {
  const res = await adminApi.templateDelete({ id: row.id })
  if (res.code === 1) {
    notification.success({ title: '提示', duration: 2000, content: '模板已删除' })
    if (tableData.value.length === 1 && query.pageNum > 1) query.pageNum -= 1
    fetchList()
  }
}

const columns = [
  {
    title: '封面',
    key: 'cover',
    width: 90,
    render: (row) => row.cover
      ? h(NImage, { src: row.cover, width: 60, height: 40, objectFit: 'cover', style: 'border-radius:4px;' })
      : h('span', { style: 'color:#9B9B9B;font-size:12px;' }, '无封面')
  },
  { title: '标题', key: 'title', minWidth: 140, ellipsis: { tooltip: true } },
  {
    title: '分类',
    key: 'category',
    width: 100,
    render: (row) => h(NTag, { size: 'small', bordered: false }, { default: () => row.category })
  },
  { title: '时长', key: 'duration', width: 80, render: (row) => `${row.duration}s` },
  { title: '热度', key: 'hot', width: 80 },
  { title: '使用次数', key: 'use_count', width: 90 },
  { title: '排序', key: 'sort', width: 70 },
  {
    title: '上架',
    key: 'active',
    width: 80,
    render: (row) => h(NSwitch, {
      value: !!row.active,
      size: 'small',
      onUpdateValue: () => handleActive(row)
    })
  },
  { title: '创建时间', key: 'create_time', width: 170 },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => h('div', { style: 'display:flex;gap:8px;' }, [
      h(NButton, { size: 'small', type: 'primary', quaternary: true, onClick: () => openEdit(row) }, { default: () => '编辑' }),
      h(NPopconfirm, {
        onPositiveClick: () => handleDelete(row)
      }, {
        trigger: () => h(NButton, { size: 'small', type: 'error', quaternary: true }, { default: () => '删除' }),
        default: () => `确定删除模板「${row.title}」吗?`
      })
    ])
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
          placeholder="搜索标题 / 标签 / 描述"
          clearable
          style="width: 220px"
          @keyup.enter="handleSearch"
        />
        <n-input
          v-model:value="query.category"
          placeholder="分类"
          clearable
          style="width: 140px"
          @keyup.enter="handleSearch"
        />
        <n-select
          v-model:value="query.active"
          :options="activeOptions"
          style="width: 120px"
        />
        <n-button type="primary" class="brand-btn" @click="handleSearch">搜索</n-button>
        <n-button @click="handleReset">重置</n-button>
        <div class="toolbar-right">
          <n-button type="primary" class="brand-btn" @click="openCreate">新建模板</n-button>
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
      :title="editingRow ? '编辑模板' : '新建模板'"
      style="width: 560px"
      :mask-closable="false"
    >
      <n-form ref="formRef" :model="form" :rules="formRules" label-placement="left" label-width="90">
        <n-form-item label="标题" path="title">
          <n-input v-model:value="form.title" placeholder="请输入模板标题" />
        </n-form-item>
        <n-form-item label="分类" path="category">
          <n-input v-model:value="form.category" placeholder="如:带货 / 探店 / 口播" />
        </n-form-item>
        <n-form-item label="封面" path="cover">
          <div class="upload-row">
            <div v-if="form.cover" class="upload-preview">
              <n-image :src="form.cover" width="72" height="96" object-fit="cover" style="border-radius:6px;" />
              <n-button size="tiny" quaternary type="error" @click="form.cover = ''">移除</n-button>
            </div>
            <n-button :loading="uploadingCover" @click="coverInput?.click()">
              {{ form.cover ? '重新上传' : '上传封面' }}
            </n-button>
            <input ref="coverInput" type="file" accept="image/*" hidden @change="(e) => handleFilePick(e, 'cover', uploadingCover)" />
            <n-input v-model:value="form.cover" placeholder="或直接粘贴图片地址" size="small" style="max-width: 220px" />
          </div>
        </n-form-item>
        <n-form-item label="示例视频" path="video_url">
          <div class="upload-row">
            <video v-if="form.video_url" :src="form.video_url" class="video-preview" controls muted />
            <n-button :loading="uploadingVideo" @click="videoInput?.click()">
              {{ form.video_url ? '重新上传' : '上传视频' }}
            </n-button>
            <input ref="videoInput" type="file" accept="video/*" hidden @change="(e) => handleFilePick(e, 'video_url', uploadingVideo)" />
            <n-input v-model:value="form.video_url" placeholder="或直接粘贴视频地址" size="small" style="max-width: 220px" />
          </div>
        </n-form-item>
        <n-form-item label="时长(秒)" path="duration">
          <n-input-number v-model:value="form.duration" :min="1" style="width: 160px" />
        </n-form-item>
        <n-form-item label="描述" path="desc">
          <n-input v-model:value="form.desc" type="textarea" :rows="3" placeholder="模板描述" />
        </n-form-item>
        <n-form-item label="标签" path="tags">
          <n-dynamic-tags v-model:value="form.tags" />
        </n-form-item>
        <n-form-item label="排序" path="sort">
          <n-input-number v-model:value="form.sort" style="width: 160px" />
        </n-form-item>
        <n-form-item label="上架" path="active">
          <n-switch v-model:value="form.active" />
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
.upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  width: 100%;
}
.upload-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.video-preview {
  width: 120px;
  height: 80px;
  border-radius: 6px;
  background: #000;
  object-fit: cover;
}
</style>
