/**
 * @description 自动 import 导入所有 api 模块
 */

const modules = {}
const files = import.meta.glob('./model/*.js', { eager: true })

Object.keys(files).forEach((key) => {
  const name = key.replace(/\.\/model\//g, '').replace(/\.js/g, '')
  modules[name] = files[key].default
})

export default modules
