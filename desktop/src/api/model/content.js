// 内容生成统一入口(对外只暴露产品功能:文案 / 图片提示词 / 语音 / 内容准备)。
// 内部由哪个 worker 技能执行完全在服务端映射,前端不感知技能名与编排,避免实现泄露。
import config from "@/config"
import http from "@/utils/request"

export default {
  // 生成/润色带货文案 -> 后端 /content/copy
  copy: {
    url: `${config.API_URL}/v1/content/copy`,
    name: "生成文案",
    post: async (data = {}, cfg = {}) => http.post(this.url, data, cfg),
  },
  // 生成英文图片提示词 -> /content/image-prompt
  imagePrompt: {
    url: `${config.API_URL}/v1/content/image-prompt`,
    name: "生成图片提示词",
    post: async (data = {}, cfg = {}) => http.post(this.url, data, cfg),
  },
  // 语音合成 -> /content/voice
  voice: {
    url: `${config.API_URL}/v1/content/voice`,
    name: "语音合成",
    post: async (data = {}, cfg = {}) => http.post(this.url, data, cfg),
  },
  // 内容准备流水线 -> /content/prepare
  prepare: {
    url: `${config.API_URL}/v1/content/prepare`,
    name: "内容准备",
    post: async (data = {}, cfg = {}) => http.post(this.url, data, cfg),
  },
  // 轮询异步产物 -> /content/result(仅 task_id,无技能名)
  result: {
    url: `${config.API_URL}/v1/content/result`,
    name: "内容结果",
    post: async (data = {}, cfg = {}) => http.post(this.url, data, cfg),
  },
}
