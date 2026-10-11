/**
 * 自动聚合 `api/model/*.js` 模块，统一对外暴露。
 * 各业务页面通过 `@/api` 获取按模块命名的 API 对象。
 */

const modules = {}
const files = import.meta.glob('./model/*.js', { eager: true })

Object.keys(files).forEach((key) => {
  const name = key.replace(/\.\/model\//g, '').replace(/\.js/g, '')
  modules[name] = files[key].default
})

export default modules