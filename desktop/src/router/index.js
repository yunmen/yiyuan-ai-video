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
        path: '/digital',
        name: 'Digital',
        component: () => import('../views/market/Digital.vue'),
        meta: { title: '数字人' }
      },
      {
        path: '/works',
        name: 'Works',
        component: () => import('../views/user/Works.vue'),
        meta: { title: '我的作品', tabbar: true, auth: true }
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
    path: '/admin/login',
    name: 'AdminLogin',
    component: () => import('../views/admin/Login.vue'),
    meta: { title: '管理后台登录', hidden: true }
  },
  {
    path: '/admin',
    component: () => import('../layout/admin/index.vue'),
    redirect: '/admin/template',
    meta: { admin: true },
    children: [
      {
        path: 'template',
        name: 'AdminTemplate',
        component: () => import('../views/admin/Template.vue'),
        meta: { title: '模板管理', admin: true }
      },
      {
        path: 'task',
        name: 'AdminTask',
        component: () => import('../views/admin/Task.vue'),
        meta: { title: '任务监控', admin: true }
      },
      {
        path: 'config',
        name: 'AdminConfig',
        component: () => import('../views/admin/Config.vue'),
        meta: { title: '业务配置', admin: true }
      },
      {
        path: 'order',
        name: 'AdminOrder',
        component: () => import('../views/admin/Order.vue'),
        meta: { title: '订单管理', admin: true }
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
  // 管理端路由守卫:无 adminToken 跳登录页
  if (to.meta.admin && !localStorage.getItem('adminToken')) {
    return { path: '/admin/login' }
  }
  // 已登录管理员访问登录页直接进入后台
  if (to.path === '/admin/login' && localStorage.getItem('adminToken')) {
    return { path: '/admin/template' }
  }
  // C端登录拦截:需登录页面未登录时弹登录框,不进入目标页
  if (to.meta.auth && !localStorage.getItem('token')) {
    useUserStore().openLogin()
    // 直接访问受保护URL时回首页;应用内跳转则停留在当前页
    return from.path === '/' && !from.name ? { path: '/home' } : false
  }
})

export default router
