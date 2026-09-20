import config from "@/config"
import http from "@/utils/request"

export default {
	list: {
		url: `${config.API_URL}/v1/digital/list`,
		name: "数字人列表",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	detail: {
		url: `${config.API_URL}/v1/digital/detail`,
		name: "数字人详情",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
}
