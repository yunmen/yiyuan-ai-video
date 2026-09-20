1、生成uniapp的开发模板
```sh
mkdir mobile
cd mobile
npx degit dcloudio/uni-preset-vue#vite .
```
2、安装需要的依赖
```sh
npm install # 安装依赖
npm run dev:h5 # 启动项目
```
4、安装额外的依赖
```sh
npm install @dcloudio/uni-ui    # uniapp的官方UI库, 也可以选择其他的UI库
npm install sass
```
5、配置pages.js
```js
{
    "pages": [],
    "tabBar": {
		"color": "#6b7280",
		"selectedColor": "#10b981",
		"backgroundColor": "#ffffff",
		"borderStyle": "black",
		"list": [
			{
				"pagePath": "pages/battle/index",
				"iconPath": "static/tabbar/battle.png",
				"selectedIconPath": "static/tabbar/battle.png",
				"text": "战场"
			}, 
			{
				"pagePath": "pages/order/index",
				"iconPath": "static/tabbar/order.png",
				"selectedIconPath": "static/tabbar/order.png",
				"text": "订单"
			}, 
			{
				"pagePath": "pages/point/index",
				"iconPath": "static/tabbar/point.png",
				"selectedIconPath": "static/tabbar/point.png",
				"text": "积分"
			}
		]
	},
    "globalStyle": {
		"navigationBarTextStyle": "black",
		"navigationBarTitleText": "商城战场",
		"navigationBarBackgroundColor": "#F8F8F8",
		"backgroundColor": "#F8F8F8",
		"h5":{  //设置h5模式下不显示导航栏
			"navigationStyle": "custom"
		}
	},
	"easycom": {    //在 pages.json中添加 easycom规则，即可在项目中直接使用 uni-开头的组件而无需手动 import
		"autoscan": true,
		"custom": {
			"^uni-(.*)": "@dcloudio/uni-ui/lib/uni-$1/uni-$1.vue"
		}
	}
}
```
5、配置vite.config.js
```js
import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

// https://vitejs.dev/config/
export default defineConfig(( ) => {
  return {
    plugins: [
      uni()
    ],
    publicDir: 'public',        //增加公共目录
    transpileDependencies: ["@dcloudio/uni-ui"],
    css: {
      preprocessorOptions: {
        scss: {}
      }
    },
    server: {   //配置代理
      port: 5173,
      open: true,
      proxy: {
        '/api/user': {
          target: 'http://localhost:8801',
          changeOrigin: true,
          ws: true // 启用WebSocket代理
        },
      },
    },
  }
})

```
