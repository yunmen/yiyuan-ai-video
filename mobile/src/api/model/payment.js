import config from '@/config'
import http from '@/utils/request'

/**
 * 支付相关接口（前缀 /v1/payment）：充值套餐、充值下单、订单状态与列表。
 */
export default {
    packageList: {
        url: `${config.API_URL}/v1/payment/package/list`,
        name: "充值套餐列表（上架）",
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    orderRecharge: {
        url: `${config.API_URL}/v1/payment/order/recharge`,
        name: "创建额度充值订单",
        // 参数：package_id、device
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    orderStatus: {
        url: `${config.API_URL}/v1/payment/order/status`,
        name: "订单状态查询（前端轮询）",
        // 参数：order_no
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    orderList: {
        url: `${config.API_URL}/v1/payment/order/list`,
        name: "我的订单列表",
        // 参数：pageNum、pageSize、status(可选)
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    orderMockConfirm: {
        url: `${config.API_URL}/v1/payment/order/mock/confirm`,
        name: "模拟支付成功",
        // 参数：order_no；备注：仅开发环境 mock 支付模式可用
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
}
