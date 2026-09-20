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
			post: async function(data, config={}){
				return await http.post(this.url, data, config);
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
