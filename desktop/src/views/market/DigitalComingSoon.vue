<script setup>
import { useRouter } from 'vue-router'

// 数字人口播「开发中」占位页。
//
// 为什么单独建占位页,而不是直接改 market/Digital.vue:
//   ① 原页面(列表 / 选形象 / 填台词 / 提交)完整保留,待 gen.digital_model 接入网关后,
//      只需把路由指回 Digital.vue 即可恢复,零回滚风险;
//   ② 当前后端数字人模型未接入,用户提交必然失败 —— 把"不可用"前置成明确的
//      「开发中」提示,而不是让用户填完内容、扣完额度后才收到一条失败原因。
//
// 入口来源(三处都指向 /digital,改路由后本页自动生效):
//   · 顶部主导航(AppHeader)  · 页脚产品服务(AppFooter)  · 首页功能卡(home/Index)
const router = useRouter()
</script>

<template>
  <div class="coming">
    <div class="box">
      <div class="icon">
        <svg width="44" height="44" viewBox="0 0 40 40" aria-hidden="true">
          <rect x="4" y="8" width="32" height="24" rx="8" fill="#FFF0EA"/>
          <circle cx="15" cy="19" r="2.4" fill="#FF4D1C"/>
          <circle cx="25" cy="19" r="2.4" fill="#FF4D1C"/>
          <path d="M15 26C17.5 27.6 22.5 27.6 25 26" stroke="#FF4D1C" stroke-width="2" stroke-linecap="round" fill="none"/>
        </svg>
      </div>
      <h1>数字人口播正在开发中</h1>
      <p>我们正在打磨数字人的口型驱动与形象表现，完成后会在这里直接开放。</p>
      <p class="sub">在此之前，你可以先用「爆款视频」生成同类型的短视频。</p>
      <div class="actions">
        <n-button type="primary" round size="large" @click="router.push('/templates')">去做爆款视频</n-button>
        <n-button round size="large" quaternary @click="router.push('/home')">返回首页</n-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.coming {
  min-height: calc(100vh - var(--header-h));
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px calc(40px + env(safe-area-inset-bottom));
}
.box {
  width: 100%;
  max-width: 460px;
  background: #fff;
  border-radius: var(--radius);
  padding: 40px 28px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}
.icon { margin-bottom: 4px; }
h1 { font-size: 18px; font-weight: 700; color: #1a1a1a; margin: 0; }
p { font-size: 13px; color: var(--body-c); line-height: 1.7; margin: 0; }
p.sub { font-size: 12px; color: var(--weak); }
.actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 12px;
}
</style>
