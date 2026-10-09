import api from '@/api'

/**
 * 使用账号接口刷新当前用户的资料与积分额度。
 * 返回 false 时调用方继续使用本地缓存，最终权限仍由后端校验。
 * 说明：后端只签发单个 token，无续期流程，鉴权失效由 request 层统一处理。
 */
export async function refreshCurrentUserProfile(userStore) {
  if (!userStore?.token) return false

  const sessionToken = userStore.token
  const suppressOptions = {
    suppressForbiddenRedirect: true,
    suppressGlobalAuthError: true,
    suppressGlobalError: true,
  }

  let refreshed = false

  try {
    const response = await api.account.info.post({}, suppressOptions)

    // 登录账号已变化时丢弃旧响应，防止旧资料覆盖新会话。
    if (userStore.token !== sessionToken) return false
    if (response.code === 1 && response.data) {
      userStore.setUserInfo(response.data)
      refreshed = true
    }
  } catch (error) {
    console.error('刷新用户资料失败，将继续使用本地缓存状态。', error)
    return false
  }

  try {
    const creditResponse = await api.account.credits.post({}, suppressOptions)

    // 同样丢弃已切换会话的额度响应。
    if (userStore.token !== sessionToken) return refreshed
    if (creditResponse.code === 1 && creditResponse.data) {
      userStore.setCreditTotal(creditResponse.data.total)
    }
  } catch (error) {
    // 额度刷新失败不影响资料刷新结果，也不向上抛出。
    console.error('刷新用户额度失败，将继续使用本地缓存状态。', error)
  }

  return refreshed
}
