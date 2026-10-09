import config from '@/config'
import http from '@/utils/request'

/**
 * 账号相关接口（前缀 /v1/account）：注册登录、验证码、资料、密码、额度。
 * 登录成功后 data 返回 { info, token } —— 后端只签发单个 token，没有 refresh_token。
 */
export default {
    register: {
        url: `${config.API_URL}/v1/account/register`,
        name: "账号密码注册",
        // 参数：account、password、nickname(可选)
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    login: {
        url: `${config.API_URL}/v1/account/login`,
        name: "账号密码登录",
        // 参数：account、password；返回 data.{ info, token }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    smsSend: {
        url: `${config.API_URL}/v1/account/sms/send`,
        name: "发送登录/注册短信验证码",
        // 参数：phone
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    loginByCode: {
        url: `${config.API_URL}/v1/account/login/code`,
        name: "手机号验证码登录（首次自动注册）",
        // 参数：phone、code、nickname(可选)、invite_code(可选)；返回 data.{ info, token, is_new }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    setPassword: {
        url: `${config.API_URL}/v1/account/set-password`,
        name: "设置/重设密码",
        // 参数：password
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    info: {
        url: `${config.API_URL}/v1/account/info`,
        name: "我的资料",
        // 无需参数，返回当前登录用户资料
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    update: {
        url: `${config.API_URL}/v1/account/update`,
        name: "修改资料",
        // 参数：nickname、avatar(可选)
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    changePassword: {
        url: `${config.API_URL}/v1/account/change-password`,
        name: "修改密码",
        // 参数：old_password、new_password
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    logout: {
        url: `${config.API_URL}/v1/account/logout`,
        name: "退出登录",
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    credits: {
        url: `${config.API_URL}/v1/account/credits`,
        name: "我的额度（余额+今日已用）",
        // 返回 data.{ free_credits, credits, total, daily_free, today_used }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    creditsLogs: {
        url: `${config.API_URL}/v1/account/credits/logs`,
        name: "额度流水（分页）",
        // 参数：type(可选)、pageNum、pageSize；返回 data 列表 + total
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
}
