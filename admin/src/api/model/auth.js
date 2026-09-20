import config from "@/config"
import http from "@/utils/request"

export default {
	password: {
		url: `${config.API_URL}/v1/base/auth/password`,
		name: "账号密码登录",
		get: async function(data={}){
			return await http.post(this.url, data);
		}
	}
}
