<script setup>
const groups = [
  {
    title: '产品服务',
    links: [
      { text: '创作工作台', path: '/studio' },
      { text: '数字人口播', path: '/digital' },
      { text: '视频换口播', path: '/render' },
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
          <p class="brand-desc">视频复刻 / 九宫格出片 / 数字人口播，一站式生成你的爆款营销视频。</p>
          <div class="brand-stats">
            <div class="stat">
              <b>10w+</b>
              <span>已生成视频</span>
            </div>
            <div class="stat">
              <b>5000+</b>
              <span>活跃商家</span>
            </div>
            <div class="stat">
              <b>98%</b>
              <span>用户好评</span>
            </div>
          </div>
        </div>
        <div class="footer-links">
          <div v-for="g in groups" :key="g.title" class="link-group">
            <h4>{{ g.title }}</h4>
            <router-link v-for="l in g.links" :key="l.text" :to="l.path">{{ l.text }}</router-link>
          </div>
          <div class="link-group contact-group">
            <h4>联系我们</h4>
            <span class="contact">客服热线：400-888-0000</span>
            <span class="contact">邮箱：support@example.com</span>
            <span class="contact">工作日 9:00 - 21:00</span>
          </div>
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
  background: #0F172A;
  color: #8b95a5;
  padding: var(--s-8) var(--s-5) var(--s-5);
  margin-top: auto;
  position: relative;
  overflow: hidden;
}
/* 顶部光晕装饰 */
.app-footer::before {
  content: '';
  position: absolute;
  top: -80px;
  left: 50%;
  transform: translateX(-50%);
  width: 600px;
  height: 200px;
  background: radial-gradient(ellipse at center, rgba(79, 70, 229, .18) 0%, transparent 70%);
  pointer-events: none;
}
.footer-inner {
  max-width: var(--page-max);
  margin: 0 auto;
  position: relative;
  z-index: 1;
}
.footer-top {
  display: flex;
  flex-direction: column;
  gap: var(--s-7);
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
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--grad-brand);
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-desc {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.8;
  color: #718096;
  max-width: 340px;
}
.brand-stats {
  display: flex;
  gap: var(--s-5);
  margin-top: var(--s-4);
  padding-top: var(--s-4);
  border-top: 1px solid rgba(255, 255, 255, .06);
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat b {
  font-size: 18px;
  font-weight: 800;
  color: var(--brand-l);
}
.stat span {
  font-size: 11px;
  color: #5b6472;
}

.link-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.link-group h4 {
  margin: 0;
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
.link-group a:hover { color: var(--brand-l); }
.footer-bottom {
  margin-top: var(--s-7);
  padding-top: var(--s-5);
  border-top: 1px solid rgba(255, 255, 255, .06);
  display: flex;
  flex-wrap: wrap;
  gap: var(--s-3) var(--s-5);
  font-size: 12px;
  color: #5b6472;
}
.footer-bottom a { color: #5b6472; text-decoration: none; }
.footer-bottom a:hover { color: var(--brand-l); }

/* 移动端：设计稿为 App 形态(底部 Tab 导航),不展示页脚;
   站内入口(客服/设置/个人中心)在移动端可从首页额度徽章进入 /user 后抵达 */
@media (max-width: 768px) {
  .app-footer { display: none; }
  .footer-top { gap: var(--s-5); }
  .footer-links {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--s-5) var(--s-4);
  }
  .contact-group { display: block; grid-column: span 2; }
  .contact-group .contact { margin-right: var(--s-3); }
  .footer-bottom { margin-top: var(--s-5); padding-top: var(--s-4); }
}

@media (min-width: 768px) {
  .app-footer { padding: var(--s-9) var(--s-6) var(--s-6); }
  .footer-top {
    flex-direction: row;
    justify-content: space-between;
    gap: var(--s-8);
  }
  .brand { flex: 1.4; min-width: 240px; }
  .footer-links { flex: 2.2; display: flex; gap: var(--s-8); }
  .link-group { flex: 1; min-width: 140px; }
}
</style>
