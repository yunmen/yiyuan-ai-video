// 内容生成统一入口(对外只暴露产品功能:文案 / 图片提示词 / 语音 / 内容准备)。
// 内部由哪个 worker 技能执行完全在服务端映射,前端不感知技能名与编排,避免实现泄露。
import config from "@/config"
import http from "@/utils/request"

export default {
  // 生成/润色带货文案 -> 后端 /content/copy
  // 注意:必须用普通函数而非箭头函数 —— 箭头函数捕获模块作用域 this(为 undefined),
  // 会导致 this.url 报 "Cannot read properties of undefined (reading 'url')"
  copy: {
    url: `${config.API_URL}/v1/content/copy`,
    name: "生成文案",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
  // 生成中文图片提示词 -> /content/image-prompt
  imagePrompt: {
    url: `${config.API_URL}/v1/content/image-prompt`,
    name: "生成图片提示词",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
  // 语音合成 -> /content/voice
  voice: {
    url: `${config.API_URL}/v1/content/voice`,
    name: "语音合成",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
  // 内容准备流水线 -> /content/prepare
  prepare: {
    url: `${config.API_URL}/v1/content/prepare`,
    name: "内容准备",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
  // 长文去 AI 味改写 -> /content/rewrite(映射服务端 text-rewrite 技能)
  rewrite: {
    url: `${config.API_URL}/v1/content/rewrite`,
    name: "去 AI 味改写",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
  // 批量翻译(多语言本地化) -> /content/translate(映射服务端 text-translate 技能)
  translate: {
    url: `${config.API_URL}/v1/content/translate`,
    name: "批量翻译",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
  // 轮询异步产物 -> /content/result(仅 task_id,无技能名)
  result: {
    url: `${config.API_URL}/v1/content/result`,
    name: "内容结果",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
}
