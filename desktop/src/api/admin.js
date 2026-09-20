import axios from 'axios'
import { createDiscreteApi } from 'naive-ui'
import sysConfig from '@/config'
import router from '@/router'

const { notification } = createDiscreteApi(['notification'])

export const ADMIN_TOKEN_KEY = 'adminToken'
export const ADMIN_INFO_KEY = 'adminInfo'

// 管理端独立 axios 实例,使用 adminToken,与 C 端 token 隔离
const adminHttp = axios.create({
	baseURL: '',
	timeout: sysConfig.TIMEOUT
})

adminHttp.interceptors.request.use(
	(config) => {
		const token = localStorage.getItem(ADMIN_TOKEN_KEY)
		if (token) {
			config.headers[sysConfig.TOKEN_NAME] = sysConfig.TOKEN_PREFIX + token
		}
		Object.assign(config.headers, sysConfig.HEADERS)
		return config
	},
	(error) => Promise.reject(error)
)

adminHttp.interceptors.response.use(
	(response) => {
		const res = response.data
		if (res.code == 0) {
			notification.warning({
				title: '提示',
				duration: 2500,
				content: res.message || res.msg || '操作失败'
			})
		}
		if (res.code == 9) {
			localStorage.removeItem(ADMIN_TOKEN_KEY)
			localStorage.removeItem(ADMIN_INFO_KEY)
			notification.warning({
				title: '提示',
				duration: 2500,
				content: res.message || res.msg || '登录已过期,请重新登录'
			})
			router.replace({ path: '/admin/login' })
		}
		return res
	},
	(error) => {
		const msg = error.response?.data?.message || error.response?.data?.msg || error.message || '请求服务器无响应!'
		if (error.response?.status == 401) {
			localStorage.removeItem(ADMIN_TOKEN_KEY)
			localStorage.removeItem(ADMIN_INFO_KEY)
			router.replace({ path: '/admin/login' })
		}
		notification.error({
			title: '请求错误',
			duration: 2500,
			content: msg
		})
		return Promise.reject(error)
	}
)

const post = (url, data = {}) => adminHttp.post(url, data)

// 上传素材文件(复用后端公共上传接口,支持图片/视频,50MB 内)
const uploadFile = async (file) => {
	const formData = new FormData()
	formData.append('file', file)
	const res = await adminHttp.post(`${sysConfig.API_URL}/v1/base/common/upload/file`, formData, {
		// 上传单独放宽超时(adminHttp 默认 10s,大文件会被中断)
		timeout: 5 * 60 * 1000
	})
	if (res.code === 1) return res.data
	throw new Error(res.message || '上传失败')
}

const adminApi = {
	uploadFile,
	// 登录
	login: (data) => post(`${sysConfig.API_URL}/admin/v1/base/auth/password`, data),

	// 业务配置
	configList: (data) => post(`${sysConfig.API_URL}/admin/v1/system/config/list`, data),
	configUpsert: (data) => post(`${sysConfig.API_URL}/admin/v1/system/config/upsert`, data),

	// 视频模板
	templateList: (data) => post(`${sysConfig.API_URL}/admin/v1/video/template/list`, data),
	templateCreate: (data) => post(`${sysConfig.API_URL}/admin/v1/video/template/create`, data),
	templateUpdate: (data) => post(`${sysConfig.API_URL}/admin/v1/video/template/update`, data),
	templateActive: (data) => post(`${sysConfig.API_URL}/admin/v1/video/template/active`, data),
	templateDelete: (data) => post(`${sysConfig.API_URL}/admin/v1/video/template/delete`, data),

	// 生成任务
	taskList: (data) => post(`${sysConfig.API_URL}/admin/v1/video/task/list`, data),

	// 支付订单
	orderList: (data) => post(`${sysConfig.API_URL}/admin/v1/payment/order/list`, data),
	orderRefund: (data) => post(`${sysConfig.API_URL}/admin/v1/payment/order/refund`, data),
	orderRefundQuery: (data) => post(`${sysConfig.API_URL}/admin/v1/payment/order/refund-query`, data),
}

export default adminApi
