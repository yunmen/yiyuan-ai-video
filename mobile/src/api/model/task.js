import config from '@/config'
import http from '@/utils/request'

/**
 * 生成任务相关接口（前缀 /v1/task）：预估、建单、拆解、预检、素材识别、我的作品与任务操作。
 * 建单后任务为异步执行，前端通过 /detail 读取结果（result_text）。
 */
export default {
    estimate: {
        url: `${config.API_URL}/v1/task/estimate`,
        name: "预估本次生成消耗",
        // 参数：type、template_id(可选)、num_images(可选)、shot_count(可选)、per_shot_seconds(可选)、duration(可选)、ratio(可选)、resolution(可选)、has_reference_video(可选)
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    create: {
        url: `${config.API_URL}/v1/task/create`,
        name: "创建生成任务（视频复刻/九宫格建单）",
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    deconstruct: {
        url: `${config.API_URL}/v1/task/deconstruct`,
        name: "拆解对标视频分镜",
        // 参数：reference_video、intent(可选)、duration(可选)、format(可选)、creative_level(可选)、hook_boost(可选)、goal(可选)
        // 返回 { task_id 等 }，拆解结果经 /detail 的 result_text 回读
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    precheck: {
        url: `${config.API_URL}/v1/task/precheck`,
        name: "建单前预检（返回结构化缺失项）",
        // 参数：materials、intent(可选)、reference_video(可选)、duration(可选)
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    classifyImages: {
        url: `${config.API_URL}/v1/task/classify-images`,
        name: "AI 识别参考图角色（人物/产品/场景）",
        // 参数：urls；返回 data.{ roles: { url: 'person' | 'product' | 'scene' | '' } }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    updateAnalysis: {
        url: `${config.API_URL}/v1/task/analysis/update`,
        name: '补充原片元素与镜头关联',
        // 参数由解析凭证和本人分镜任务组成，不接受自由时间轴。
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    detectElements: {
        url: `${config.API_URL}/v1/task/detect-elements`,
        name: "检测对标视频原片元素槽位",
        // 参数：reference_video；返回 data.{ elements: [] }
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    list: {
        url: `${config.API_URL}/v1/task/list`,
        name: "我的作品列表",
        // 参数：pageNum、pageSize、status(可选)、task_no(可选)、type(可选)；返回 data 列表 + total
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    detail: {
        url: `${config.API_URL}/v1/task/detail`,
        name: "任务详情",
        // 参数：id
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    delete: {
        url: `${config.API_URL}/v1/task/delete`,
        name: "删除作品",
        // 参数：id
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    regenerate: {
        url: `${config.API_URL}/v1/task/regenerate`,
        name: "重新生成（可带风格换效果）",
        // 参数：id、creative_level(可选)、hook_boost(可选)
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    regenerateSegment: {
        url: `${config.API_URL}/v1/task/regenerate_segment`,
        name: "局部重跑（改一句台词重生成）",
        // 参数：id、segment_index、new_text；调用后任务回到 processing（result_video 清空），需轮询 /detail 至 success
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    resume: {
        url: `${config.API_URL}/v1/task/resume`,
        name: "断点续跑（从检查点继续）",
        // 参数：id
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    imageCreate: {
        url: `${config.API_URL}/v1/task/image/create`,
        name: "创建图片生成任务",
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    audioCreate: {
        url: `${config.API_URL}/v1/task/audio/create`,
        name: "创建音频生成任务（语音/背景音乐）",
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    textCreate: {
        url: `${config.API_URL}/v1/task/text/create`,
        name: "创建文本生成任务",
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    digitalCreate: {
        url: `${config.API_URL}/v1/task/digital/create`,
        name: "创建数字人口播任务",
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
    renderCreate: {
        url: `${config.API_URL}/v1/task/render/create`,
        name: "创建视频换口播任务",
        post: async function (data = {}, cfg = {}) {
            return await http.post(this.url, data, cfg);
        }
    },
}
