import config from "@/config"
import http from "@/utils/request"

export default {
	copyGenerate: {
		url: `${config.API_URL}/v1/base/common/copy/generate`,
		name: "AI 一键写文案",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	upload: {
		file: {
			url: `${config.API_URL}/v1/base/common/upload/file`,
			name: "文件上传",
			// 文件上传耗时远高于普通接口,单独放宽超时(全局默认仅 10s,大文件/弱网会被中途掐断报"请求服务器无响应")
			post: async function(data, options={}){
				return await http.post(this.url, data, { timeout: 5 * 60 * 1000, ...options });
			}
		},
		url: {
			url: `${config.API_URL}/v1/base/common/upload/url`,
			name: "文件上传",
			get: async function(data, config={}){
				return await http.post(this.url, data, config);
			}
		},
	}
}
