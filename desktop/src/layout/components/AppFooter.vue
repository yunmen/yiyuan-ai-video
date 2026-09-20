<script setup>
const groups = [
  {
    title: '产品服务',
    links: [
      { text: '爆款视频', path: '/templates' },
      { text: '数字人口播', path: '/digital' },
      { text: '账户余额', path: '/balance' },
    ]
  },
  {
    title: '帮助支持',
    links: [
      { text: '联系客服', path: '/support' },
      { text: '我的作品', path: '/works' },
      { text: '个人中心', path: '/user' },
    ]
  },
]
</script>

<template>
  <footer class="app-footer">
    <div class="footer-inner">
      <div class="footer-top">
        <div class="brand">
          <div class="brand-logo">
            <span class="logo-badge">
              <svg width="16" height="16" viewBox="0 0 28 28"><path d="M9 6.5L21 14L9 21.5V6.5Z" fill="#fff"/></svg>
            </span>
            <span>一源 AI 视频</span>
          </div>
          <p class="brand-desc">选模板 → 换素材 → 出视频，3 步生成你的爆款营销视频。</p>
        </div>
        <div v-for="g in groups" :key="g.title" class="link-group">
          <h4>{{ g.title }}</h4>
          <router-link v-for="l in g.links" :key="l.text" :to="l.path">{{ l.text }}</router-link>
        </div>
        <div class="link-group">
          <h4>联系我们</h4>
          <span class="contact">客服热线：400-888-0000</span>
          <span class="contact">邮箱：support@example.com</span>
          <span class="contact">工作日 9:00 - 21:00</span>
        </div>
      </div>
      <div class="footer-bottom">
        <span>© 2026 一源AI. All rights reserved.</span>
        <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener">粤ICP备2024XXXXXX号</a>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  background: #16161F;
  color: #a0aec0;
  padding: 28px 20px 20px;
  margin-top: auto;
}
.footer-inner {
  max-width: var(--page-max);
  margin: 0 auto;
}
.footer-top {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.brand-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}
.logo-badge {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: linear-gradient(135deg, #FF8A3D, #FF4D1C);
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-desc {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.8;
  color: #718096;
  max-width: 320px;
}
.link-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.link-group h4 {
  margin: 0 0 2px;
  font-size: 13px;
  color: #fff;
  font-weight: 600;
}
.link-group a,
.link-group .contact {
  font-size: 12px;
  color: #8b95a5;
  text-decoration: none;
  transition: color .2s;
}
.link-group a:hover { color: #FF6A3D; }
.footer-bottom {
  margin-top: 22px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, .08);
  display: flex;
  flex-wrap: wrap;
  gap: 10px 20px;
  font-size: 12px;
  color: #5b6472;
}
.footer-bottom a { color: #5b6472; text-decoration: none; }
.footer-bottom a:hover { color: #FF6A3D; }

@media (min-width: 768px) {
  .app-footer { padding: 40px 24px 24px; }
  .footer-top {
    flex-direction: row;
    justify-content: space-between;
    gap: 40px;
  }
  .brand { flex: 1.4; min-width: 240px; }
  .link-group { flex: 1; min-width: 140px; }
}
</style>
