import config from "@/config"
import http from "@/utils/request"

export default {
	template: {
		list: {
			url: `${config.API_URL}/v1/video/template/list`,
			name: "获取视频模板列表",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		detail: {
			url: `${config.API_URL}/v1/video/template/detail`,
			name: "获取视频模板详情",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		create: {
			url: `${config.API_URL}/v1/video/template/create`,
			name: "创建视频模板",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		update: {
			url: `${config.API_URL}/v1/video/template/update`,
			name: "修改视频模板",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		delete: {
			url: `${config.API_URL}/v1/video/template/delete`,
			name: "删除视频模板",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		active: {
			url: `${config.API_URL}/v1/video/template/active`,
			name: "上架/下架视频模板",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		recommend: {
			url: `${config.API_URL}/v1/video/template/recommend`,
			name: "首页推荐开关",
			get: async function(data){
				return await http.post(this.url, data);
			}
		}
	},
	category: {
		list: {
			url: `${config.API_URL}/v1/video/category/list`,
			name: "获取模板分类列表",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		save: {
			url: `${config.API_URL}/v1/video/category/save`,
			name: "新增/编辑模板分类",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		delete: {
			url: `${config.API_URL}/v1/video/category/delete`,
			name: "删除模板分类",
			get: async function(data){
				return await http.post(this.url, data);
			}
		}
	},
	task: {
		list: {
			url: `${config.API_URL}/v1/video/task/list`,
			name: "获取生成任务列表",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		detail: {
			url: `${config.API_URL}/v1/video/task/detail`,
			name: "获取生成任务详情",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		delete: {
			url: `${config.API_URL}/v1/video/task/delete`,
			name: "删除生成任务",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		resume: {
			url: `${config.API_URL}/v1/video/task/resume`,
			name: "断点续跑",
			get: async function(data){
				return await http.post(this.url, data);
			}
		}
	}
}
