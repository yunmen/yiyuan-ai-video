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
	// 用户自助上传形象 → 专属数字人:创建与我的列表
	personalCreate: {
		url: `${config.API_URL}/v1/digital/personal/create`,
		name: "创建专属数字人",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	personalList: {
		url: `${config.API_URL}/v1/digital/personal/list`,
		name: "我的专属数字人列表",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	personalUpdate: {
		url: `${config.API_URL}/v1/digital/personal/update`,
		name: "编辑专属数字人",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	personalDelete: {
		url: `${config.API_URL}/v1/digital/personal/delete`,
		name: "删除专属数字人",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
}
