/**
 * @description Pinia store 入口，提供 this.$store 兼容层
 */

import { createPinia } from 'pinia'
import { useGlobalStore } from './modules/global'
import { useIframeStore } from './modules/iframe'
import { useKeepAliveStore } from './modules/keepAlive'
import { useViewTagsStore } from './modules/viewTags'

const pinia = createPinia()

const globalStore = useGlobalStore(pinia)
const iframeStore = useIframeStore(pinia)
const keepAliveStore = useKeepAliveStore(pinia)
const viewTagsStore = useViewTagsStore(pinia)

const stores = {
	global: globalStore,
	iframe: iframeStore,
	keepAlive: keepAliveStore,
	viewTags: viewTagsStore
}

const storeApi = {
	get state() {
		return stores
	},
	commit(type, payload) {
		for (const store of Object.values(stores)) {
			if (typeof store[type] === 'function') {
				store[type](payload)
				return
			}
		}
	}
}

export default {
	install(app) {
		app.use(pinia)
		app.config.globalProperties.$store = storeApi
	},
	// 兼容外部直接 import store from '@/store' 的用法
	get state() {
		return storeApi.state
	},
	commit(type, payload) {
		storeApi.commit(type, payload)
	}
}
