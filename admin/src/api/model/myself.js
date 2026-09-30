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
    repwd: {
        url: `${config.API_URL}/v1/base/myself/repwd`,
        name: "修改密码",
        post: async function(data={}){
            return await http.post(this.url, data);
        }
    },
    edit: {
        url: `${config.API_URL}/v1/base/myself/edit`,
        name: "修改个人资料",
        post: async function(data={}){
            return await http.post(this.url, data);
        }
    },
}
