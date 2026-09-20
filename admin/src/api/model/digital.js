import config from "@/config"
import http from "@/utils/request"

export default {
	list: {
		url: `${config.API_URL}/v1/video/digital/list`,
		name: "获取数字人列表",
		get: async function(data){
			return await http.post(this.url, data);
		}
	},
	detail: {
		url: `${config.API_URL}/v1/video/digital/detail`,
		name: "获取数字人详情",
		get: async function(data){
			return await http.post(this.url, data);
		}
	},
	create: {
		url: `${config.API_URL}/v1/video/digital/create`,
		name: "创建数字人",
		get: async function(data){
			return await http.post(this.url, data);
		}
	},
	update: {
		url: `${config.API_URL}/v1/video/digital/update`,
		name: "修改数字人",
		get: async function(data){
			return await http.post(this.url, data);
		}
	},
	delete: {
		url: `${config.API_URL}/v1/video/digital/delete`,
		name: "删除数字人",
		get: async function(data){
			return await http.post(this.url, data);
		}
	},
	active: {
		url: `${config.API_URL}/v1/video/digital/active`,
		name: "上架/下架数字人",
		get: async function(data){
			return await http.post(this.url, data);
		}
	}
}
