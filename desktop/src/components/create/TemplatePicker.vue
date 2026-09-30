<script setup>
// 平台模板选择器:模板替换本质上也是「视频复刻」,只是对标视频来自平台模板而非用户上传。
// 这里只负责列模板并把选中的模板抛给调用方(pick 事件),由复刻页决定如何预填。
import { ref, onMounted } from 'vue'
import api from '@/api'

const emit = defineEmits(['pick'])
const templates = ref([])
const loading = ref(false)

onMounted(loadTemplates)
async function loadTemplates() {
  loading.value = true
  try {
    const res = await api.template.list.post({ pageNum: 1, pageSize: 50 })
    if (res.code === 1) templates.value = (res.data || []).filter((t) => t.video_url)
  } catch (e) { /* 拦截器已提示 */ }
  finally { loading.value = false }
}
</script>

<template>
  <div class="tpl-picker">
    <n-spin :show="loading">
      <div class="grid">
        <div v-for="t in templates" :key="t.id" class="card" @click="emit('pick', t)">
          <img v-if="t.cover" :src="t.cover" :alt="t.title" />
          <video
            v-else
            :src="`${t.video_url}#t=0.1`"
            muted
            playsinline
            preload="metadata"
          ></video>
          <div class="meta">
            <b>{{ t.title }}</b>
            <span>{{ t.category || '模板' }}<template v-if="t.duration"> · {{ t.duration }}秒</template></span>
          </div>
          <span class="go">用它复刻 →</span>
        </div>
        <div v-if="!loading && !templates.length" class="empty">暂无可复刻的模板</div>
      </div>
    </n-spin>
  </div>
</template>

<style scoped>
.tpl-picker { max-height: 60vh; overflow-y: auto; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
.card {
  background: #fff; border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
  cursor: pointer; transition: transform .15s, box-shadow .15s;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0, 0, 0, .08); border-color: var(--brand); }
.card img, .card video { width: 100%; height: 110px; object-fit: cover; display: block; background: #000; }
.meta { padding: 8px 10px; }
.meta b {
  display: block; font-size: 13px; color: #1a1a1a;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.meta span { font-size: 12px; color: var(--weak); }
.go { display: block; padding: 0 10px 10px; font-size: 12px; color: var(--brand); font-weight: 600; }
.empty { grid-column: 1 / -1; text-align: center; color: var(--weak); padding: 30px; }
</style>
