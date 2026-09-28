import { createRouter, createWebHistory } from 'vue-router'
import config from "@/config"
import { useUserStore } from '@/store/modules/user'


const routes = [
  {
    path: '/',
    component: () => import('../layout/index.vue'),
    redirect: '/home',
    children: [
      {
        path: '/home',
        name: 'Home',
        component: () => import('../views/home/Index.vue'),
        meta: { title: '首页', tabbar: true }
      },
      {
        path: '/templates',
        name: 'Templates',
        component: () => import('../views/template/Index.vue'),
        meta: { title: '爆款视频' }
      },
      {
        // 数字人口播:列表/选形象/填台词/提交,由 market/Digital.vue 承载。
        // 其余入口(AppHeader 导航 / AppFooter 页脚 / 首页功能卡)均指向 /digital,无需改动。
        path: '/digital',
        name: 'Digital',
        component: () => import('../views/market/Digital.vue'),
        meta: { title: '数字人' }
      },
      {
        // AI 创作:图片 / 音频 / 文本三条链路的 C 端页面。
        // ⚠️ 当前**刻意不在主导航暴露**(AppHeader 的 menuOptions 中不含本项):
        //    这三条链路尚未在真实网关完成验收,先以「可直连、不曝光」的方式交付。
        //    验收通过并确认产品形态后,如需对外开放,再把本项加入 menuOptions 即可。
        path: '/creator',
        name: 'Creator',
        component: () => import('../views/create/Creator.vue'),
        meta: { title: 'AI 创作' }
      },
      {
        path: '/works',
        name: 'Works',
        component: () => import('../views/user/Works.vue'),
        meta: { title: '我的作品', tabbar: true, auth: true }
      },
      {
        // 视频复刻:对标视频 + 产品图 → 拆解分镜(可编辑) → 生成复刻视频。
        // 对应 douyin-video-replication 的复刻链路,底层复用既有生成/拆解原子能力。
        path: '/replicate',
        name: 'Replicate',
        component: () => import('../views/create/Replicate.vue'),
        meta: { title: '视频复刻' }
      },
      {
        // 九宫格出片:商品信息 → 强 Hook 脚本 → 九宫格分镜图 → 出片(无需对标视频)。
        // 对应 douyin-video-replication 的强 Hook 九宫格 / 九宫格直投两条链路。
        path: '/storyboard',
        name: 'Storyboard',
        component: () => import('../views/create/Storyboard.vue'),
        meta: { title: '九宫格出片' }
      },
      {
        path: '/user',
        name: 'User',
        component: () => import('../views/user/Profile.vue'),
        meta: { title: '我的', tabbar: true, auth: true }
      },
      {
        path: '/settings',
        name: 'Settings',
        component: () => import('../views/user/Settings.vue'),
        meta: { title: '设置', auth: true }
      },
      {
        path: '/change-password',
        name: 'ChangePassword',
        component: () => import('../views/user/ChangePassword.vue'),
        meta: { title: '修改密码', auth: true }
      },
      {
        path: '/support',
        name: 'Support',
        component: () => import('../views/user/Support.vue'),
        meta: { title: '联系客服' }
      },
      {
        path: '/balance',
        name: 'Balance',
        component: () => import('../views/user/Balance.vue'),
        meta: { title: '账户余额', auth: true }
      },
      {
        path: '/orders',
        name: 'Orders',
        component: () => import('../views/user/Orders.vue'),
        meta: { title: '我的订单', auth: true }
      },
      {
        path: '/upload/:id',
        name: 'Upload',
        component: () => import('../views/create/Upload.vue'),
        meta: { title: '替换素材', hidden: true, auth: true }
      },
      {
        path: '/generate/:id',
        name: 'Generate',
        component: () => import('../views/create/Generate.vue'),
        meta: { title: '生成视频', hidden: true, auth: true }
      },
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../layout/NotFound.vue'),
    meta: { title: '404', hidden: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

//设置标题
document.title = config.APP_NAME
router.beforeEach((to, from) => {
  document.title = to.meta.title ? `${to.meta.title} - ${config.APP_NAME}` : `${config.APP_NAME}`
  // C端登录拦截:需登录页面未登录时弹登录框,不进入目标页
  if (to.meta.auth && !localStorage.getItem('token')) {
    useUserStore().openLogin()
    // 直接访问受保护URL时回首页;应用内跳转则停留在当前页
    return from.path === '/' && !from.name ? { path: '/home' } : false
  }
})

export default router
