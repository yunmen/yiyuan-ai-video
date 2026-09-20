import config from "@/config"
import http from "@/utils/request"

export default {
	genConfig: {
		url: `${config.API_URL}/v1/base/common/gen-config`,
		name: "业务配置(定价等)",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	orderCreate: {
		url: `${config.API_URL}/v1/payment/order/create`,
		name: "创建支付订单",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	packageList: {
		url: `${config.API_URL}/v1/payment/package/list`,
		name: "充值套餐列表",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	recharge: {
		url: `${config.API_URL}/v1/payment/order/recharge`,
		name: "创建充值订单",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	orderList: {
		url: `${config.API_URL}/v1/payment/order/list`,
		name: "我的订单列表",
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	orderStatus: {
		url: `${config.API_URL}/v1/payment/order/status`,
		name: "订单状态查询",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	mockConfirm: {
		url: `${config.API_URL}/v1/payment/order/mock/confirm`,
		name: "模拟支付(开发环境)",
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
}
