import { defineStore } from 'pinia'
import config from "@/config";

export const useGlobalStore = defineStore('global', {
	state: () => ({
		ismobile: false,
		layout: config.LAYOUT,
		menuIsCollapse: config.MENU_IS_COLLAPSE,
		layoutTags: config.LAYOUT_TAGS,
		theme: config.THEME,
		setting: config.SETTING_SHOW
	}),
	actions: {
		SET_ismobile(key){
			this.ismobile = key
		},
		SET_layout(key){
			this.layout = key
		},
		SET_theme(key){
			this.theme = key
		},
		TOGGLE_menuIsCollapse(){
			this.menuIsCollapse = !this.menuIsCollapse
		},
		TOGGLE_layoutTags(){
			this.layoutTags = !this.layoutTags
		}
	}
})
