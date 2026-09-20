// 静态路由配置
// 书写格式与动态路由格式一致，全部经由框架统一转换
// 比较动态路由在meta中多加入了role角色权限，为数组类型。一个菜单是否有权限显示，取决于它以及后代菜单是否有权限。
// routes 显示在左侧菜单中的路由(显示顺序在动态路由之前)
// 示例如下

// const routes = [
// 	{
// 		name: "demo",
// 		path: "/demo",
// 		meta: {
// 			icon: "el-icon-eleme-filled",
// 			title: "演示",
// 			role: ["SA"]
// 		},
// 		children: [{
// 			name: "demopage",
// 			path: "/demopage",
// 			component: "test/autocode/index",
// 			meta: {
// 				icon: "el-icon-menu",
// 				title: "演示页面",
// 				role: ["SA"]
// 			}
// 		}]
// 	}
// ]


const routes = [
    {
        "name": "home",
        "path": "/home",
        "meta": {
            "title": "首页",
            "icon": "el-icon-eleme-filled",
            "type": "menu"
        },
        "redirect": '/dashboard',
        "children": [
            {
                "name": "dashboard",
                "path": "/dashboard",
                "meta": {
                    "title": "控制台",
                    "icon": "el-icon-menu",
                    "affix": true
                },
                "component": "home"
            },
            {
                "name": "userCenter",
                "path": "/usercenter",
                "meta": {
                    "title": "帐号信息",
                    "icon": "el-icon-user",
                    "hidden": true
                },
                "component": "userCenter"
            },
        ]
    }
]

export default routes;
