import config from '@/config'
import http from '@/utils/request'

/**
 * 意见反馈相关接口（前缀 /v1/feedback）。
 */
export default {
    create: {
        url: `${config.API_URL}/v1/feedback/create`,
        name: "提交意见反馈",
        // 参数：content、contact(可选)
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
}
