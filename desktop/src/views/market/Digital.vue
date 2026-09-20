<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

const avatars = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await api.digital.list.post({ pageNum: 1, pageSize: 50 })
    if (res.code === 1) avatars.value = res.data || []
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
}

function choose() {
  window.$message?.info('功能开发中')
}

onMounted(load)
</script>

<template>
  <div class="av-page">
    <div class="wrap">
      <n-spin :show="loading">
        <div v-if="avatars.length" class="grid">
          <div v-for="a in avatars" :key="a.id" class="avcard">
            <div class="avcover">
              <img v-if="a.avatar" :src="a.avatar" :alt="a.name" />
              <svg v-else viewBox="0 0 143 180" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
                <rect width="143" height="180" fill="#F3E8FF"/>
                <circle cx="71.5" cy="70" r="28" fill="#C4A0E8"/>
                <path d="M30 142C30 112 48 96 71.5 96C95 96 113 112 113 142V180H30V142Z" fill="#C4A0E8"/>
              </svg>
            </div>
            <div class="avname">{{ a.name }}</div>
            <div class="avsub">{{ a.gender === 'male' ? '男声' : '女声' }} · 口播</div>
            <div class="avbtn" @click="choose">选择</div>
          </div>
        </div>
        <n-empty v-else-if="!loading" description="数字人整理中，敬请期待" style="padding:60px 0" />
      </n-spin>
    </div>
    <div class="avtip">数字人功能持续更新中，敬请期待</div>
  </div>
</template>

<style scoped>
.av-page {
  min-height: calc(100vh - var(--header-h));
  background: var(--bg);
  padding-bottom: 80px;
  display: flex;
  flex-direction: column;
}
.wrap { max-width: var(--page-max); margin: 0 auto; width: 100%; flex: 1; }
.grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 16px 20px;
}
.avcard {
  width: calc(50% - 8px);
  background: #fff;
  border-radius: var(--radius);
  padding: 8px 8px 12px;
  text-align: center;
  box-shadow: var(--shadow-sm);
  transition: transform .2s, box-shadow .2s;
}
.avcard:hover { transform: translateY(-3px); box-shadow: var(--shadow-brand); }
.avcover {
  aspect-ratio: 143 / 180;
  border-radius: 10px;
  overflow: hidden;
  background: #F3E8FF;
}
.avcover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.avname { font-size: 13px; font-weight: 500; margin: 8px 0 2px; }
.avsub { font-size: 11px; color: var(--weak); margin-bottom: 8px; }
.avbtn {
  height: 32px;
  border-radius: 16px;
  background: var(--brand-bg);
  color: var(--brand);
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.avtip {
  background: #FFF7F2;
  padding: 14px 20px;
  text-align: center;
  font-size: 12px;
  color: #FF7A45;
}
@media (min-width: 768px) {
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; padding: 20px; }
  .avcard { width: auto; }
}
</style>
