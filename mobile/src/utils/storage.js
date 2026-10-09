/**
 * 本地存储统一封装。
 * 基于 uni 的同步存储 API，H5 环境自动映射到 localStorage，小程序/App 保持一致。
 * 所有读写都做 try/catch，避免存储不可用时抛错影响业务。
 */

export function getStorage(key, fallback = '') {
  try {
    const value = uni.getStorageSync(key)
    return value === '' || value === null || value === undefined ? fallback : value
  } catch (err) {
    console.error('读取本地缓存失败')
    return fallback
  }
}

export function setStorage(key, value) {
  try {
    uni.setStorageSync(key, value)
  } catch (err) {
    console.error('写入本地缓存失败')
    // 存储写入失败时忽略，不阻断业务
  }
}

export function removeStorage(key) {
  try {
    uni.removeStorageSync(key)
  } catch (err) {
    console.error('清除本地缓存失败')
    // 存储清理失败时忽略
  }
}