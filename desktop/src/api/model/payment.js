import config from "@/config"
import http from "@/utils/request"

export default {
	// 注:业务配置(定价/复刻选项)已迁至 common 模块的 genConfig(后端路径属 /v1/base/common),
	// 不要再在此处挂同名入口,避免两份定义漂移
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
