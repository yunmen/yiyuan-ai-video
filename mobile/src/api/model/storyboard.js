import config from '@/config'
import http from '@/utils/request'

/**
 * 分镜/镜头接口（前缀 /v1/storyboard）：分镜级状态查询、镜头提示词/台词编辑（供局部重跑）。
 * 与桌面端 storyboard.js 同源，字段契约以后端路由 /user/v1/storyboard 为准。
 */
export default {
    list: {
        url: `${config.API_URL}/v1/storyboard/list`,
        name: "分镜镜头列表",
        // 参数：task_id、page_num、page_size；返回 data.{ total, episode, shots: [] }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    shotUpdate: {
        url: `${config.API_URL}/v1/storyboard/shot/update`,
        name: "编辑镜头(提示词/台词/时长)",
        // 参数：task_id、index、prompt(可选)、narration(可选)、start_ms(可选)、end_ms(可选)
        // 返回更新后的镜头；后端会同步回写任务 usage.shot_prompts，供局部重跑读取编辑后的提示词
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
}
