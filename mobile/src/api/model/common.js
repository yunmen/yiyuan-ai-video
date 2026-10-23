import config from '@/config'
import http from '@/utils/request'

/**
 * 公共基础接口（前缀 /v1/base/common）：公开业务配置、素材上传与直传签名。
 */
export default {
    materialRole: {
        url: `${config.API_URL}/v1/base/common/materials/role`,
        name: '保存素材用途标识',
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    materialType: {
        url: `${config.API_URL}/v1/base/common/materials/type`,
        name: '保存素材类型标识',
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    materialsSync: {
        url: `${config.API_URL}/v1/base/common/materials/sync`,
        name: '找回历史上传素材',
        /** 分批确认早期直传记录，仅找回当前账号真实存在的文件。 */
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    materials: {
        url: `${config.API_URL}/v1/base/common/materials`,
        name: '我的历史上传素材',
        /** 分页只返回当前用户已完成上传的图片和视频。 */
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    uploadConfirm: {
        url: `${config.API_URL}/v1/base/common/upload/confirm`,
        name: '确认素材上传完成',
        /** 服务端核验本人直传对象已存在，再登记到素材列表。 */
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
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
