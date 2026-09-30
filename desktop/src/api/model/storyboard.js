// 分镜/镜头接口:分镜级状态查询、镜头提示词/台词编辑(供局部重跑)
import config from "@/config"
import http from "@/utils/request"

export default {
	list: {
		url: `${config.API_URL}/v1/storyboard/list`,
		name: "分镜镜头列表",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	// 编辑单个镜头(覆盖提示词/台词/时长),调用方按 api.storyboard.shotUpdate.post(...) 使用
	shotUpdate: {
		url: `${config.API_URL}/v1/storyboard/shot/update`,
		name: "编辑镜头(提示词/台词/时长)",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
}
