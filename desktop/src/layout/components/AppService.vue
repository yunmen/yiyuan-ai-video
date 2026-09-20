<script setup>
function share() {
  const url = window.location.href
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(
      () => window.$message?.success('链接已复制,快去分享吧'),
      () => window.$message?.error('复制失败,请手动复制')
    )
  } else {
    window.$message?.info('请手动复制浏览器地址分享')
  }
}
function contact() {
  window.$message?.info('客服热线:400-888-0000')
}
</script>

<template>
  <div class="service-fab">
    <n-popover trigger="click" placement="top">
      <template #trigger>
        <button class="fab-btn" aria-label="客服">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M21 11.5a8.38 8.38 0 01-8.5 8.5 8.5 8.5 0 01-3.9-.9L3 21l1.9-5.6A8.5 8.5 0 1121 11.5z" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </template>
      <div class="pop">
        <div class="pop-title">需要帮助?</div>
        <div class="pop-row">客服热线:400-888-0000</div>
        <div class="pop-actions">
          <n-button size="small" tertiary @click="contact">联系客服</n-button>
          <n-button size="small" type="primary" @click="share">分享应用</n-button>
        </div>
      </div>
    </n-popover>
  </div>
</template>

<style scoped>
.service-fab {
  position: fixed;
  right: 24px;
  bottom: 32px;
  z-index: 300;
}
.fab-btn {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: none;
  background: #FF4D1C;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
}
.fab-btn svg {
  width: 24px;
  height: 24px;
}
.fab-btn {
  transition: transform .18s, box-shadow .18s;
}
.fab-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(255, 77, 28, .32);
}
.pop-title {
  font-weight: 600;
  margin-bottom: 6px;
}
.pop-row {
  font-size: 13px;
  color: #666;
  margin-bottom: 10px;
}
.pop-actions {
  display: flex;
  gap: 8px;
}
@media (max-width: 768px) {
  .service-fab {
    right: 16px;
    bottom: 72px;
  }
}
</style>
