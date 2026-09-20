import config from "@/config"
import http from "@/utils/request"

export default {
	create: {
		url: `${config.API_URL}/v1/task/create`,
		name: "创建生成任务",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	detail: {
		url: `${config.API_URL}/v1/task/detail`,
		name: "任务详情",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	regenerate: {
		url: `${config.API_URL}/v1/task/regenerate`,
		name: "重新生成",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	resume: {
		url: `${config.API_URL}/v1/task/resume`,
		name: "断点续跑",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	imageCreate: {
		url: `${config.API_URL}/v1/task/image/create`,
		name: "创建图片生成任务",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	audioCreate: {
		url: `${config.API_URL}/v1/task/audio/create`,
		name: "创建音频生成任务",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	textCreate: {
		url: `${config.API_URL}/v1/task/text/create`,
		name: "创建文本生成任务",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	list: {
		url: `${config.API_URL}/v1/task/list`,
		name: "我的作品",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	delete: {
		url: `${config.API_URL}/v1/task/delete`,
		name: "删除作品",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
}
