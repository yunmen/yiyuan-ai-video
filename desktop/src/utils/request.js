import axios from 'axios'
import { createDiscreteApi } from 'naive-ui'
import sysConfig from '@/config'
import router from '@/router'
import { useUserStore } from '@/store/modules/user'

const { notification } = createDiscreteApi(['notification'])

axios.defaults.baseURL = ''

axios.defaults.timeout = sysConfig.TIMEOUT

// HTTP request 拦截器
axios.interceptors.request.use(
	(config) => {
		let token = localStorage.getItem('token')
		if(token){
			config.headers[sysConfig.TOKEN_NAME] = sysConfig.TOKEN_PREFIX + token
		}
		if(!sysConfig.REQUEST_CACHE && config.method == 'get'){
			config.params = config.params || {};
			config.params['_'] = new Date().getTime();
		}
		Object.assign(config.headers, sysConfig.HEADERS)
		return config;
	},
	(error) => {
		return Promise.reject(error);
	}
);

//FIX 多个API同时401时疯狂弹窗BUG
let MessageBox_401_show = false

// HTTP response 拦截器
axios.interceptors.response.use(
	(response) => {
		if (response.data.code == 0) {
			notification.warning({
				title: '提示',
				duration: 2500,
				content: response.data.message || response.data.msg
			})
		}
		if (response.data.code == 9) {
			router.replace({
				path: '/'
			});
			notification.warning({
				title: '提示',
				duration: 2500,
				content: response.data.message || response.data.msg
			})
		}
		return response;
	},
	(error) => {
		if (error.response) {
			if (error.response.status == 404) {
				notification.error({
					title: '请求错误',
					duration: 2500,
					content: error.response.data.message || error.response.data.msg || "Status:404，正在请求不存在的服务器记录！"
				});
			} else if (error.response.status == 500) {
				notification.error({
					title: '请求错误',
					duration: 2500,
					content: error.response.data.message || error.response.data.msg || "Status:500，服务器发生错误！"
				});
			} else if (error.response.status == 401) {
			// 401 统一处理:清除失效登录态并引导重新登录,而不是弹死路错误框
			const userStore = useUserStore()
			const wasLoggedIn = userStore.isLoggedIn
			userStore.logout()
			// 退出登录接口本身的 401 静默处理,由页面提示"已退出登录"
			const isLogout = (error.config?.url || '').includes('/account/logout')
			if(!MessageBox_401_show && !isLogout){
				MessageBox_401_show = true
				notification.warning({
					title: '提示',
					duration: 2500,
					content: wasLoggedIn ? '登录已过期，请重新登录' : '请先登录'
				})
				setTimeout(() => { MessageBox_401_show = false }, 2500)
				// 当前在需登录页面时回首页,避免页面持续请求受保护接口
				if (router.currentRoute.value.meta?.auth) router.replace({path: '/'})
				userStore.openLogin()
			}
		} else {
				notification.error({
					title: '请求错误',
					duration: 2500,
					content: error.message || `Status:${error.response.status}，未知错误！`
				});
			}
		} else {
			notification.error({
				title: '请求错误',
				duration: 2500,
				content: "请求服务器无响应！"
			});
		}

		return Promise.reject(error.response);
	}
);

var http = {

	/** get 请求
	 * @param  {string} url 接口地址
	 * @param  {object} params 请求参数
	 * @param  {object} config 参数
	 */
	get: function(url, params={}, config={}) {
		return new Promise((resolve, reject) => {
			axios({
				method: 'get',
				url: url,
				params: params,
				...config
			}).then((response) => {
				resolve(response.data);
			}).catch((error) => {
				reject(error);
			})
		})
	},

	/** post 请求
	 * @param  {string} url 接口地址
	 * @param  {object} data 请求参数
	 * @param  {object} config 参数
	 */
	post: function(url, data={}, config={}) {
		return new Promise((resolve, reject) => {
			axios({
				method: 'post',
				url: url,
				data: data,
				...config
			}).then((response) => {
				resolve(response.data);
			}).catch((error) => {
				reject(error);
			})
		})
	},

	/** put 请求
	 * @param  {string} url 接口地址
	 * @param  {object} data 请求参数
	 * @param  {object} config 参数
	 */
	put: function(url, data={}, config={}) {
		return new Promise((resolve, reject) => {
			axios({
				method: 'put',
				url: url,
				data: data,
				...config
			}).then((response) => {
				resolve(response.data);
			}).catch((error) => {
				reject(error);
			})
		})
	},
}

export default http;
