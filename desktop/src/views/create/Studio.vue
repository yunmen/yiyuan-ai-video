<script setup>
// 统一创作工作台:把“视频复刻 / 九宫格出片”两条创作链路收拢到同一入口,
// 用顶部标签页切换;每条链路内部已复用 AdvancedCreationSettings 组件,
// 创意档位 / 开头钩子 / 专家模式等能力在各方式下一致呈现(对应重新设计目标 B)。
// 「模板替换」不再单列:它本质是复刻的一种,对标视频选平台模板即可,入口在复刻页内。
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const tabs = [
  { key: 'replicate', label: '视频复刻', desc: '上传视频或选平台模板,换产品 / 人物 / 场景', to: '/studio/replicate' },
  { key: 'storyboard', label: '九宫格出片', desc: '只需商品信息,自动出强 Hook 脚本与分镜', to: '/studio/storyboard' },
]
const active = computed(() => {
  if (route.path.startsWith('/studio/replicate')) return 'replicate'
  if (route.path.startsWith('/studio/storyboard')) return 'storyboard'
  return 'replicate'
})
</script>

<template>
  <div class="studio">
    <div class="studio-hero">
      <h1>创作工作台</h1>
      <p>选择一种创作方式。所有方式都支持「创意档位 / 开头钩子 / 专家模式」高级设置;视频复刻还能选择平台模板当对标视频,并在拆解分镜后逐镜微调、局部重跑。</p>
    </div>
    <div class="studio-tabs">
      <div
        v-for="t in tabs"
        :key="t.key"
        :class="['stab', { on: active === t.key }]"
        @click="router.push(t.to)"
      >
        <b>{{ t.label }}</b>
        <span>{{ t.desc }}</span>
      </div>
    </div>
    <router-view />
  </div>
</template>

<style scoped>
.studio { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding: 20px 16px 48px; }
/* 宽度与内嵌创作页(Replicate/Storyboard/Creator 均为 720px)对齐:
   此前是 920px,与下方 720px 内容卡左右边缘错位,视觉上“两层皮” */
.studio-hero { max-width: 720px; margin: 0 auto 18px; text-align: center; }
.studio-hero h1 { font-size: 22px; font-weight: 700; margin: 0 0 8px; color: #1a1a1a; }
.studio-hero p { font-size: 13px; color: var(--weak); margin: 0; line-height: 1.7; }
.studio-tabs {
  max-width: 720px; margin: 0 auto 18px;
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;
}
.stab {
  background: #fff; border: 1px solid var(--line); border-radius: 12px;
  padding: 14px 16px; cursor: pointer; display: flex; flex-direction: column; gap: 4px;
  transition: border-color .15s, box-shadow .15s;
}
.stab:hover { border-color: var(--brand); }
.stab.on { border-color: var(--brand); box-shadow: 0 4px 14px rgba(255, 77, 28, .12); background: var(--brand-bg); }
.stab b { font-size: 15px; color: #1a1a1a; }
.stab span { font-size: 12px; color: var(--weak); }
.stab.on b { color: var(--brand); }
@media (max-width: 768px) {
  /* 小屏收敛:说明压缩、两个标签改为横排分段控件,不再竖向堆叠占半屏 */
  .studio { padding: 14px 12px 40px; }
  .studio-hero { margin-bottom: 12px; }
  .studio-hero h1 { font-size: 18px; margin-bottom: 6px; }
  .studio-hero p { font-size: 12px; line-height: 1.6; }
  .studio-tabs { display: flex; gap: 8px; margin-bottom: 14px; }
  .stab {
    flex: 1;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    padding: 10px 4px;
    border-radius: 10px;
    gap: 0;
  }
  /* 小屏只留标签名,描述移除(Hero 说明已概括三条链路) */
  .stab span { display: none; }
  .stab b { font-size: 14px; }
}
</style>
