import config from "@/config"
import http from "@/utils/request"

export default {
	estimate: {
		url: `${config.API_URL}/v1/task/estimate`,
		name: "预估生成消耗",
		// 下单前可见花费/预计耗时/可选规格,与建单扣减同源
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	create: {
		url: `${config.API_URL}/v1/task/create`,
		name: "创建生成任务",
		// 创建任务后端会同步做商品图视觉识别与提示词组装,耗时可达数十秒,覆盖全局 10s 超时
		post: async function(data, config={}){
			return await http.post(this.url, data, { timeout: 120 * 1000, ...config });
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
		// 重新生成与创建同链路(含视觉识别),同样需要放宽超时
		post: async function(data, config={}){
			return await http.post(this.url, data, { timeout: 120 * 1000, ...config });
		}
	},
	resume: {
		url: `${config.API_URL}/v1/task/resume`,
		name: "断点续跑",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	regenerateSegment: {
		url: `${config.API_URL}/v1/task/regenerate_segment`,
		name: "局部重跑(改一句台词重生成)",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	imageCreate: {
		url: `${config.API_URL}/v1/task/image/create`,
		name: "创建图片生成任务",
		// 与视频生成同属创建任务,建单含额度预估等同步步骤,放宽全局 10s 超时保持一致
		post: async function(data, config={}){
			return await http.post(this.url, data, { timeout: 120 * 1000, ...config });
		}
	},
	audioCreate: {
		url: `${config.API_URL}/v1/task/audio/create`,
		name: "创建音频生成任务",
		// 与视频生成同属创建任务,建单含额度预估等同步步骤,放宽全局 10s 超时保持一致
		post: async function(data, config={}){
			return await http.post(this.url, data, { timeout: 120 * 1000, ...config });
		}
	},
	textCreate: {
		url: `${config.API_URL}/v1/task/text/create`,
		name: "创建文本生成任务",
		// 与视频生成同属创建任务,建单含额度预估等同步步骤,放宽全局 10s 超时保持一致
		post: async function(data, config={}){
			return await http.post(this.url, data, { timeout: 120 * 1000, ...config });
		}
	},
	digitalCreate: {
		url: `${config.API_URL}/v1/task/digital/create`,
		name: "创建数字人口播任务",
		// 与视频生成同属创建任务,建单含额度预估等同步步骤,放宽全局 10s 超时保持一致
		post: async function(data, config={}){
			return await http.post(this.url, data, { timeout: 120 * 1000, ...config });
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
