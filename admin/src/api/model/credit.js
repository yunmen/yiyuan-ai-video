import config from "@/config"
import http from "@/utils/request"

export default {
	user: {
		list: {
			url: `${config.API_URL}/v1/credit/user/list`,
			name: "获取用户额度列表",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		logs: {
			url: `${config.API_URL}/v1/credit/logs`,
			name: "获取用户额度流水",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		grant: {
			url: `${config.API_URL}/v1/credit/grant`,
			name: "赠送额度",
			get: async function(data){
				return await http.post(this.url, data);
			}
		}
	}
}
