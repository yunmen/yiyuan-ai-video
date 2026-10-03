import axios from "axios"
import config from "@/config"
import http from "@/utils/request"

// 直传对象存储专用实例:不走全局拦截器,避免把 Authorization 带给对象存储导致签名失效
const ossHttp = axios.create()

const UPLOAD_FILE_URL = `${config.API_URL}/v1/base/common/upload/file`
const UPLOAD_SIGN_URL = `${config.API_URL}/v1/base/common/upload/sign`

/**
 * 上传素材:优先浏览器直传对象存储,不可用时回退服务器中转。
 * 服务器在海外,中转国内上行仅约 80KB/s,稍大文件必然超时,故直传为默认路径。
 * @param {File|Blob} file 文件或二进制块
 * @param {Object} [options] filename:对象存储取扩展名用;onProgress:进度回调(0~1)
 * @returns {Promise<string>} 素材可访问 URL
 */
export async function uploadFile(file, options = {}) {
	const filename = options.filename || file.name || "file.bin"
	const report = options.onProgress
	const onUploadProgress = (e) => {
		if (report && e.total) report(e.loaded / e.total)
	}
	let sign = null
	try {
		sign = await http.post(UPLOAD_SIGN_URL, { filename })
	} catch (e) {
		// 签名接口本身不可用(网络异常/对象存储未启用),走下方服务器中转兜底
	}
	// 拿到预签名即走直传,且不再回退中转:中转上行极慢,大文件二次上传必定失败,
	// 反而会把直传的真实错误掩盖成"请求服务器无响应"
	if (sign && sign.code === 1 && sign.data?.uploadUrl) {
		await ossHttp.put(sign.data.uploadUrl, file, {
			headers: { "Content-Type": file.type || "application/octet-stream" },
			timeout: 10 * 60 * 1000,
			onUploadProgress,
		})
		return sign.data.url
	}
	const formData = new FormData()
	formData.append("file", file, filename)
	const res = await http.post(UPLOAD_FILE_URL, formData, {
		timeout: 5 * 60 * 1000,
		onUploadProgress,
	})
	if (res.code === 1) return res.data.url
	throw new Error(res.message || "上传失败")
}

/**
 * 文件上传(浏览器直传对象存储,失败时回退服务器中转)。详见 uploadFile。
 */

export default {
	genConfig: {
		url: `${config.API_URL}/v1/base/common/gen-config`,
		name: "业务配置(定价/复刻选项)",
		// 公共配置归属 /v1/base/common 而非支付域,此前错挂在 payment 模块里,
		// 导致"支付模块读定价"与"公共配置"两份入口长期并存,现收敛到 common 一处
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	upload: {
		file: {
			url: UPLOAD_FILE_URL,
			name: "文件上传",
			// 文件上传耗时远高于普通接口,单独放宽超时(全局默认仅 10s,大文件/弱网会被中途掐断报"请求服务器无响应")
			post: async function(data, options={}){
				return await http.post(this.url, data, { timeout: 5 * 60 * 1000, ...options });
			}
		},
		sign: {
			url: UPLOAD_SIGN_URL,
			name: "获取上传预签名URL",
			post: async function(data){
				return await http.post(this.url, data);
			}
		},
	}
}
