import config from '@/config'
import http from '@/utils/request'

/**
 * 视频模板相关接口（前缀 /v1/template）：列表、首页热门推荐、分类、详情。
 */
export default {
    list: {
        url: `${config.API_URL}/v1/template/list`,
        name: "模板列表",
        // 参数：pageNum、pageSize、keyword(可选)、category(可选)、recommend(可选)、sort_type(可选)；返回 data 列表 + total
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    recommend: {
        url: `${config.API_URL}/v1/template/recommend`,
        name: "首页热门推荐模板",
        // 返回 data 列表
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    categoryList: {
        url: `${config.API_URL}/v1/template/category/list`,
        name: "模板分类列表",
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    detail: {
        url: `${config.API_URL}/v1/template/detail`,
        name: "模板详情",
        // 参数：id
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
}
