import config from '@/config'
import http from '@/utils/request'

/**
 * 数字人相关接口（前缀 /v1/digital）：平台形象列表/详情与我的专属数字人增删改查。
 * list 仅返回已上架的平台数字人形象。
 */
export default {
    list: {
        url: `${config.API_URL}/v1/digital/list`,
        name: "平台数字人形象列表",
        // 参数：pageNum、pageSize、keyword(可选)、gender(可选)；仅上架、仅平台数字人
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    detail: {
        url: `${config.API_URL}/v1/digital/detail`,
        name: "数字人详情",
        // 参数：id
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    personalCreate: {
        url: `${config.API_URL}/v1/digital/personal/create`,
        name: "创建专属数字人",
        // 参数：name、gender(可选)、style(可选)、desc(可选)、avatar(可选)、image、voice(可选)、voice_reference(可选)、default_text(可选)
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    personalList: {
        url: `${config.API_URL}/v1/digital/personal/list`,
        name: "我的专属数字人列表",
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    personalUpdate: {
        url: `${config.API_URL}/v1/digital/personal/update`,
        name: "编辑专属数字人",
        // 参数：id + 创建时的同名字段
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    personalDelete: {
        url: `${config.API_URL}/v1/digital/personal/delete`,
        name: "删除专属数字人",
        // 参数：id
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
}
