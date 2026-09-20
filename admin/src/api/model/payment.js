import config from "@/config"
import http from "@/utils/request"

export default {
	order: {
		list: {
			url: `${config.API_URL}/v1/payment/order/list`,
			name: "获取支付订单列表",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		refund: {
			url: `${config.API_URL}/v1/payment/order/refund`,
			name: "发起退款",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		refundQuery: {
			url: `${config.API_URL}/v1/payment/order/refund-query`,
			name: "退款查询",
			get: async function(data){
				return await http.post(this.url, data);
			}
		}
	},
	package: {
		list: {
			url: `${config.API_URL}/v1/payment/package/list`,
			name: "获取充值套餐列表",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		save: {
			url: `${config.API_URL}/v1/payment/package/save`,
			name: "新增/编辑充值套餐",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		delete: {
			url: `${config.API_URL}/v1/payment/package/delete`,
			name: "删除充值套餐",
			get: async function(data){
				return await http.post(this.url, data);
			}
		}
	}
}
