<script setup>
import { ref, onMounted } from 'vue'
import { toast } from '../store/app'
import { AVATARS } from '../data'
import { digitalApi } from '../api'
import AppBar from '../components/AppBar.vue'

const avatars = ref([])
const loading = ref(true)

// 本地示例数据兜底:原型环境未接后端时仍可独立演示
const FALLBACK = AVATARS.map((a, i) => ({
  id: -1 - i, name: a.n, avatar: '', gender: '女', style: '', desc: '',
  bg: a.bg, fg: a.fg, mock: true
}))

async function load() {
  try {
    const res = await digitalApi.list({ pageNum: 1, pageSize: 50 })
    avatars.value = res.code === 1 && res.data?.length ? res.data : FALLBACK
  } catch (e) {
    avatars.value = FALLBACK
  }
  loading.value = false
}

function choose(a) {
  if (a.mock) {
    toast('未连接接口，当前为原型示例数据')
    return
  }
  toast(`已选择「${a.name}」，请在桌面端填写台词生成口播视频`)
}

onMounted(load)
</script>

<template>
  <section class="page active">
    <AppBar title="数字人口播" back-target="home" />
    <div class="body">
      <div class="grid">
        <div v-for="a in avatars" :key="a.id" class="card" style="width:159px;padding:8px;text-align:center">
          <img v-if="a.avatar" :src="a.avatar" :alt="a.name" style="width:100%;height:180px;object-fit:cover;border-radius:10px" />
          <svg v-else viewBox="0 0 143 180" width="100%" height="180">
            <rect width="143" height="180" rx="10" :fill="a.bg || '#F3E8FF'"/>
            <circle cx="71.5" cy="70" r="28" :fill="a.fg || '#C4A0E8'"/>
            <path d="M30 142C30 112 48 96 71.5 96C95 96 113 112 113 142V180H30V142Z" :fill="a.fg || '#C4A0E8'"/>
          </svg>
          <div style="font-size:13px;font-weight:500;margin:8px 0">{{ a.name }}</div>
          <div class="up gray" style="justify-content:center;border-radius:16px;height:32px" @click="choose(a)">选择</div>
        </div>
      </div>
    </div>
    <div style="flex:0 0 auto; background:#FFF7F2; padding:14px 20px; text-align:center; font-size:12px; color:#FF7A45">
      数字人口播生成请前往桌面端体验（选择形象 → 填写台词 → 一键生成）
    </div>
  </section>
</template>
