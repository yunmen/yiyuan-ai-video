// 用户工程模板(参数模板化 / 一套结构百变体)。
// 仅暴露产品功能:保存模板 / 我的模板 / 删除 / 按模板生成 / 批量出变体。
// 模板只存创意配置快照,生成变体时由前端补入新素材与覆盖项。
import config from "@/config"
import http from "@/utils/request"

export default {
  // 保存当前创意配置为模板
  save: {
    url: `${config.API_URL}/v1/task/template/save`,
    name: "保存工程模板",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
  // 我的模板 + 平台公共模板
  list: {
    url: `${config.API_URL}/v1/task/template/list`,
    name: "我的工程模板",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
  // 删除模板
  remove: {
    url: `${config.API_URL}/v1/task/template/delete`,
    name: "删除工程模板",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
  // 按模板生成单个变体
  generate: {
    url: `${config.API_URL}/v1/task/template/generate`,
    name: "按模板生成变体",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
  // 批量出变体(百变体)
  batch: {
    url: `${config.API_URL}/v1/task/template/batch`,
    name: "批量出变体",
    post: async function (data = {}, cfg = {}) { return http.post(this.url, data, cfg) },
  },
}
