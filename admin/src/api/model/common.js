import config from "@/config"
import http from "@/utils/request"

export default {
	upload: {
		url: `${config.API_URL}/v1/base/common/upload/file`,
		name: "文件上传",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	dic: {
		url: `${config.API_URL}/upload`,
		name: "文件上传",
		get: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	}
}
