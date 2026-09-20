import {createRouter, createWebHistory} from 'vue-router';
import { ElNotification } from 'element-plus';
import config from "@/config"
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import tool from '@/utils/tool';
import systemRouter from './systemRouter';
import userRoutes from '@/config/route';
import {beforeEach, afterEach} from './scrollBehavior';

// 预加载所有视图组件，构建映射表（解决 Vite 不支持变量动态导入的问题）
const viewModules = import.meta.glob('../views/**/*.vue')
const viewMap = {}
Object.keys(viewModules).forEach(key => {
	const match = key.match(/\.\.\/views\/(.+)\.vue$/)
	if (match) {
		const path = match[1]
		viewMap[path] = viewModules[key]
		// 如果是 index.vue，同时注册父目录名，如 home/index → home
		if (path.endsWith('/index')) {
			viewMap[path.replace('/index', '')] = viewModules[key]
		}
	}
})

//系统路由
const routes = systemRouter

//系统特殊路由
const routes_404 = {
	path: "/:pathMatch(.*)*",
	hidden: true,
	component: () => import('@/layout/other/404.vue'),
}
let routes_404_r = ()=>{}

const router = createRouter({
	history: createWebHistory(),
	routes: routes
})

//设置标题
document.title = config.APP_NAME

//判断是否已加载过动态/静态路由
var isGetRouter = false;

router.beforeEach(async (to, from) => {

	NProgress.start()
	//动态标题
	document.title = to.meta.title ? `${to.meta.title} - ${config.APP_NAME}` : `${config.APP_NAME}`

	let token = tool.cookie.get("TOKEN");

	if(to.path === "/login"){
		//删除路由(替换当前layout路由)
		router.addRoute(routes[0])
		//删除路由(404)
		routes_404_r()
		isGetRouter = false;
		return;
	}

	if(routes.findIndex(r => r.path === to.path) >= 0){
		return;
	}

	if(!token){
		return { path: '/login' };
	}

	//整页路由处理
	if(to.meta.fullpage){
		to.matched = [to.matched[to.matched.length-1]]
	}
	//加载动态/静态路由
	if(!isGetRouter){
		let apiMenu = tool.data.get("MENU") || []
		let userInfo = tool.data.get("USER_INFO")
		let userMenu = treeFilter(userRoutes, node => {
			return node.meta.role ? node.meta.role.filter(item=>userInfo.role.indexOf(item)>-1).length > 0 : true
		})
		let menu = [...userMenu, ...apiMenu]
		var menuRouter = filterAsyncRouter(menu)
		menuRouter = flatAsyncRoutes(menuRouter)
		menuRouter.forEach(item => {
			router.addRoute("layout", item)
		})
		routes_404_r = router.addRoute(routes_404)
		if (to.matched.length == 0) {
			router.push(to.fullPath);
		}
		isGetRouter = true;
	}
	beforeEach(to, from)
});

router.afterEach((to, from) => {
	afterEach(to, from)
	NProgress.done()
});

router.onError((error) => {
	NProgress.done();
	ElNotification.error({
		title: '路由错误',
		message: error.message
	});
});

//入侵追加自定义方法、对象
router.sc_getMenu = () => {
	var apiMenu = tool.data.get("MENU") || []
	let userInfo = tool.data.get("USER_INFO")
	let userMenu = treeFilter(userRoutes, node => {
		return node.meta.role ? node.meta.role.filter(item=>userInfo.role.indexOf(item)>-1).length > 0 : true
	})
	var menu = [...userMenu, ...apiMenu]
	return menu
}

//转换
function filterAsyncRouter(routerMap) {
	const accessedRouters = []
	routerMap.forEach(item => {
		item.meta = item.meta?item.meta:{};
		//处理外部链接特殊路由
		if(item.meta.type=='iframe'){
			item.meta.url = item.path;
			item.path = `/i/${item.name}`;
		}
		//MAP转路由对象
		var route = {
			path: item.path,
			name: item.name,
			meta: item.meta,
			redirect: item.redirect,
			children: item.children ? filterAsyncRouter(item.children) : null,
			component: loadComponent(item.component)
		}
		accessedRouters.push(route)
	})
	return accessedRouters
}
function loadComponent(component){
	if(component){
		if(viewMap[component]){
			return viewMap[component]
		}
		console.error('未找到组件: ' + component)
		return () => import('@/layout/other/empty.vue')
	}else{
		return () => import('@/layout/other/empty.vue')
	}
}

//路由扁平化
function flatAsyncRoutes(routes, breadcrumb=[]) {
	let res = []
	routes.forEach(route => {
		const tmp = {...route}
        if (tmp.children) {
            let childrenBreadcrumb = [...breadcrumb]
            childrenBreadcrumb.push(route)
            let tmpRoute = { ...route }
            tmpRoute.meta.breadcrumb = childrenBreadcrumb
            delete tmpRoute.children
            res.push(tmpRoute)
            let childrenRoutes = flatAsyncRoutes(tmp.children, childrenBreadcrumb)
            childrenRoutes.map(item => {
                res.push(item)
            })
        } else {
            let tmpBreadcrumb = [...breadcrumb]
            tmpBreadcrumb.push(tmp)
            tmp.meta.breadcrumb = tmpBreadcrumb
            res.push(tmp)
        }
    })
    return res
}

//过滤树
function treeFilter(tree, func) {
	return tree.map(node => ({ ...node })).filter(node => {
		node.children = node.children && treeFilter(node.children, func)
		return func(node) || (node.children && node.children.length)
	})
}

export default router
