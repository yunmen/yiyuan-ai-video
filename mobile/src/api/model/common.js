import config from '@/config'
import http from '@/utils/request'

/**
 * 公共基础接口（前缀 /v1/base/common）：公开业务配置、素材上传与直传签名。
 */
export default {
    genConfig: {
        url: `${config.API_URL}/v1/base/common/gen-config`,
        name: "公开业务配置",
        // 返回含 replicate_formats / replicate_intents / lead_acts / replicate_creative_levels /
        // replicate_hook_boosts / replicate_defaults / gen.* 等键值的业务配置
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    uploadFile: {
        url: `${config.API_URL}/v1/base/common/upload/file`,
        name: "上传素材文件",
        // 备注：multipart 表单，字段名为 file；页面直接用 uni.uploadFile 请求该 url
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    uploadSign: {
        url: `${config.API_URL}/v1/base/common/upload/sign`,
        name: "获取素材直传预签名 URL",
        // 参数：filename；返回 data.{ uploadUrl, url, filename }，浏览器直传对象存储
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
}
