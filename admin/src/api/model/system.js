import config from "@/config"
import http from "@/utils/request"

export default {
	menu: {
		list: {
			url: `${config.API_URL}/v1/system/menu/list`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		tree: {
			url: `${config.API_URL}/v1/system/menu/tree`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		create: {
			url: `${config.API_URL}/v1/system/menu/create`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		update: {
			url: `${config.API_URL}/v1/system/menu/update`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		delete: {
			url: `${config.API_URL}/v1/system/menu/delete`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		}
	},
	user: {
		list: {
			url: `${config.API_URL}/v1/system/user/list`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		create: {
			url: `${config.API_URL}/v1/system/user/create`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		update: {
			url: `${config.API_URL}/v1/system/user/update`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		delete: {
			url: `${config.API_URL}/v1/system/user/delete`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		active: {
			url: `${config.API_URL}/v1/system/user/active`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
	},
	dept: {
		list: {
			url: `${config.API_URL}/v1/system/dept/list`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		tree: {
			url: `${config.API_URL}/v1/system/dept/tree`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		create: {
			url: `${config.API_URL}/v1/system/dept/create`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		update: {
			url: `${config.API_URL}/v1/system/dept/update`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		delete: {
			url: `${config.API_URL}/v1/system/dept/delete`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		active: {
			url: `${config.API_URL}/v1/system/dept/active`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
	},
	role: {
		list: {
			url: `${config.API_URL}/v1/system/role/list`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		create: {
			url: `${config.API_URL}/v1/system/role/create`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		update: {
			url: `${config.API_URL}/v1/system/role/update`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		delete: {
			url: `${config.API_URL}/v1/system/role/delete`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		active: {
			url: `${config.API_URL}/v1/system/role/active`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		all: {
			url: `${config.API_URL}/v1/system/role/all`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		menu: {
			url: `${config.API_URL}/v1/system/role/menu`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		permission: {
			url: `${config.API_URL}/v1/system/role/permission`,
			name: "获取菜单",
			get: async function(data){
				return await http.post(this.url, data);
			}
		},
		
	},
	log: {
			list: {
				url: `${config.API_URL}/v1/system/log/list`,
				name: "获取菜单",
				get: async function(data){
					return await http.post(this.url, data);
				}
			},
			detail: {
				url: `${config.API_URL}/v1/system/log/detail`,
				name: "获取菜单",
				get: async function(data){
					return await http.post(this.url, data);
				}
			},
		},
		task: {
			all: {
				url: `${config.API_URL}/v1/system/task/all`,
				name: "获取菜单",
				get: async function(data){
					return await http.post(this.url, data);
				}
			},
			create: {
				url: `${config.API_URL}/v1/system/task/create`,
				name: "获取菜单",
				get: async function(data){
					return await http.post(this.url, data);
				}
			},
			update: {
				url: `${config.API_URL}/v1/system/task/update`,
				name: "获取菜单",
				get: async function(data){
					return await http.post(this.url, data);
				}
			},
			delete: {
				url: `${config.API_URL}/v1/system/task/delete`,
				name: "获取菜单",
				get: async function(data){
					return await http.post(this.url, data);
				}
			},
			active: {
				url: `${config.API_URL}/v1/system/task/active`,
				name: "获取菜单",
				get: async function(data){
					return await http.post(this.url, data);
				}
			},
			run: {
				url: `${config.API_URL}/v1/system/task/run`,
				name: "获取菜单",
				get: async function(data){
					return await http.post(this.url, data);
				}
			},
		},
		monitor: {
			detail: {
				url: `${config.API_URL}/v1/system/monitor/detail`,
				name: "获取菜单",
				get: async function(data){
					return await http.post(this.url, data);
				}
			}
		},
		cache: {
			admin: {
				all: {
					url: `${config.API_URL}/v1/system/cache/admin/all`,
					name: "获取菜单",
					get: async function(data){
						return await http.post(this.url, data);
					}
				},
				delete: {
					url: `${config.API_URL}/v1/system/cache/admin/delete`,
					name: "获取菜单",
					get: async function(data){
						return await http.post(this.url, data);
					}
				}
			},
			user: {
				get: {
					url: `${config.API_URL}/v1/system/cache/user/get`,
					name: "获取菜单",
					get: async function(data){
						return await http.post(this.url, data);
					}
				}
			}
		},
		config: {
			list: {
				url: `${config.API_URL}/v1/system/config/list`,
				name: "获取业务配置列表",
				get: async function(data){
					return await http.post(this.url, data);
				}
			},
			upsert: {
				url: `${config.API_URL}/v1/system/config/upsert`,
				name: "新增/修改业务配置",
				get: async function(data){
					return await http.post(this.url, data);
				}
			}
		}
}
