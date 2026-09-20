import config from "@/config"
import http from "@/utils/request"

export default {
    info: {
        url: `${config.API_URL}/v1/base/myself/info`,
        name: "获取用户资料",
        get: async function(data={}){
            return await http.get(this.url, data);
        }
    },
    menus: {
        url: `${config.API_URL}/v1/base/myself/menus`,
        name: "获取用户菜单",
        get: async function(data={}){
            return await http.get(this.url, data);
        }
    },
}
