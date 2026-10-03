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
	precheck: {
		url: `${config.API_URL}/v1/task/precheck`,
		name: "建单前预检(素材缺失项)",
		// 纯校验、不扣额度:前端据此渲染"还缺什么 + 一键去补"
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	deconstruct: {
		url: `${config.API_URL}/v1/task/deconstruct`,
		name: "拆解对标视频分镜",
		// 拆解为异步任务:建单后由 worker 分析,前端轮询 detail 读取分镜 JSON;建单含校验,放宽超时
		post: async function(data, config={}){
			return await http.post(this.url, data, { timeout: 120 * 1000, ...config });
		}
	},
	classifyImages: {
		url: `${config.API_URL}/v1/task/classify-images`,
		name: "上传参考图 AI 识别角色",
		// 上传后逐张视觉识别(人物/产品/场景),作为预标;超时/失败前端降级为手动选择,不阻断上传
		post: async function(data, config={}){
			return await http.post(this.url, data, { timeout: 60 * 1000, ...config });
		}
	},
	detectElements: {
		url: `${config.API_URL}/v1/task/detect-elements`,
		name: "检测原片元素槽位",
		// 换元素复刻增强:对标视频 → 识别原片人物/产品/场景槽位,供用户把上传图精确绑定;
		// 超时/失败前端降级为不绑定,不阻断上传与生成
		post: async function(data, config={}){
			return await http.post(this.url, data, { timeout: 60 * 1000, ...config });
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
	renderCreate: {
		url: `${config.API_URL}/v1/task/render/create`,
		name: "创建视频换口播任务",
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
