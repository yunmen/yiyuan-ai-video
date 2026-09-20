import config from "@/config"
import http from "@/utils/request"

export default {
	register: {
		url: `${config.API_URL}/v1/account/register`,
		name: "用户注册",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	login: {
		url: `${config.API_URL}/v1/account/login`,
		name: "用户登录",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	logout: {
		url: `${config.API_URL}/v1/account/logout`,
		name: "退出登录",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	info: {
		url: `${config.API_URL}/v1/account/info`,
		name: "我的资料",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	update: {
		url: `${config.API_URL}/v1/account/update`,
		name: "修改资料",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	changePassword: {
		url: `${config.API_URL}/v1/account/change-password`,
		name: "修改密码",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	setPassword: {
		url: `${config.API_URL}/v1/account/set-password`,
		name: "设置密码",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	smsSend: {
		url: `${config.API_URL}/v1/account/sms/send`,
		name: "发送验证码",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	loginByCode: {
		url: `${config.API_URL}/v1/account/login/code`,
		name: "验证码登录",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	signStatus: {
		url: `${config.API_URL}/v1/account/sign/status`,
		name: "签到状态",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	sign: {
		url: `${config.API_URL}/v1/account/sign`,
		name: "每日签到",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	credits: {
		url: `${config.API_URL}/v1/account/credits`,
		name: "我的额度",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	creditsLogs: {
		url: `${config.API_URL}/v1/account/credits/logs`,
		name: "额度流水",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
}
