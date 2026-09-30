import http from "@/utils/request"
import config from "@/config"

const CREATE_URL = `${config.API_URL}/v1/feedback/create`

export default {
	create: {
		url: CREATE_URL,
		name: "提交意见反馈",
		post: async function(data){
			return await http.post(this.url, data);
		}
	}
}
