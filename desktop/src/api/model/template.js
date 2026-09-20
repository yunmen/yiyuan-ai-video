import config from "@/config"
import http from "@/utils/request"

export default {
	list: {
		url: `${config.API_URL}/v1/template/list`,
		name: "模板列表",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	categoryList: {
		url: `${config.API_URL}/v1/template/category/list`,
		name: "分类列表",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	detail: {
		url: `${config.API_URL}/v1/template/detail`,
		name: "模板详情",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	recommend: {
		url: `${config.API_URL}/v1/template/recommend`,
		name: "首页热门推荐",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
}
