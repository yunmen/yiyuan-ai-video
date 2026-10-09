import config from '@/config'
import http from '@/utils/request'

/**
 * 内容生成相关接口（前缀 /v1/content）。
 * 注意：copy / image-prompt / voice / prepare / translate / rewrite 均为异步接口，
 * 调用后只返回 { task_id }，必须用 result 轮询获取结果。
 */
export default {
    copy: {
        url: `${config.API_URL}/v1/content/copy`,
        name: "生成带货文案（大标题/副标题/口播）",
        // 异步：传入 instruction 与业务参数，返回 { task_id }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    imagePrompt: {
        url: `${config.API_URL}/v1/content/image-prompt`,
        name: "生成中文图片提示词",
        // 异步：返回 { task_id }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    voice: {
        url: `${config.API_URL}/v1/content/voice`,
        name: "语音合成（TTS）",
        // 异步：返回 { task_id }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    prepare: {
        url: `${config.API_URL}/v1/content/prepare`,
        name: "内容准备流水线（目标 → 多步骤内容生成）",
        // 异步：返回 { task_id }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    rewrite: {
        url: `${config.API_URL}/v1/content/rewrite`,
        name: "长文去 AI 味改写",
        // 异步：参数 text、level(1..4 强度)、tone(natural/formal/friendly/sharp/humorous)、max_chars；返回 { task_id }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    translate: {
        url: `${config.API_URL}/v1/content/translate`,
        name: "批量翻译（多语言本地化）",
        // 异步：参数 instruction(可选)、params.{ texts, target_lang }；返回 { task_id }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    result: {
        url: `${config.API_URL}/v1/content/result`,
        name: "轮询内容生成结果",
        // 参数：task_id；返回 data.{ status: 'done' | 'pending' | 'not_found', result? }
        // status 为 done 时 result 为 { content, metadata }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
}
