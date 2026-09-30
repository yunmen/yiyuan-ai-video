import axios from "axios"
import config from "@/config"
import http from "@/utils/request"

// 直传对象存储专用实例:不走全局拦截器,避免把 Authorization 带给对象存储导致签名失效
const ossHttp = axios.create()

const UPLOAD_FILE_URL = `${config.API_URL}/v1/base/common/upload/file`
const UPLOAD_SIGN_URL = `${config.API_URL}/v1/base/common/upload/sign`
const COPY_GENERATE_URL = `${config.API_URL}/v1/base/common/copy/generate`
const COPY_RESULT_URL = `${config.API_URL}/v1/base/common/copy/result`

// 文案下单后 worker 侧要跑视觉识别 + 大模型,轮询窗口给到 150s;
// 与 worker 写 Redis 的结果 TTL(ai_copy:{task_id}, 900s)无关,只是前端耐心上限
const COPY_POLL_TIMEOUT = 150 * 1000
const COPY_POLL_INTERVAL = 2000

/**
 * 上传素材:优先浏览器直传对象存储,不可用时回退服务器中转。
 * 服务器在海外,中转国内上行仅约 80KB/s,稍大文件必然超时,故直传为默认路径。
 * @param {File|Blob} file 文件或二进制块
 * @param {Object} [options] filename:对象存储取扩展名用;onProgress:进度回调(0~1)
 * @returns {Promise<string>} 素材可访问 URL
 */
export async function uploadFile(file, options = {}) {
	const filename = options.filename || file.name || "file.bin"
	const report = options.onProgress
	const onUploadProgress = (e) => {
		if (report && e.total) report(e.loaded / e.total)
	}
	let sign = null
	try {
		sign = await http.post(UPLOAD_SIGN_URL, { filename })
	} catch (e) {
		// 签名接口本身不可用(网络异常/对象存储未启用),走下方服务器中转兜底
	}
	// 拿到预签名即走直传,且不再回退中转:中转上行极慢,大文件二次上传必定失败,
	// 反而会把直传的真实错误掩盖成"请求服务器无响应"
	if (sign && sign.code === 1 && sign.data?.uploadUrl) {
		await ossHttp.put(sign.data.uploadUrl, file, {
			headers: { "Content-Type": file.type || "application/octet-stream" },
			timeout: 10 * 60 * 1000,
			onUploadProgress,
		})
		return sign.data.url
	}
	const formData = new FormData()
	formData.append("file", file, filename)
	const res = await http.post(UPLOAD_FILE_URL, formData, {
		timeout: 5 * 60 * 1000,
		onUploadProgress,
	})
	if (res.code === 1) return res.data.url
	throw new Error(res.message || "上传失败")
}

/**
 * AI 一键写文案(异步两阶段):下单 → 轮询结果 → 返回文案结构。
 *
 * 后端 /copy/generate 已改为**只下发任务、立即返回 task_id**(真正的写文案由 worker 执行),
 * 文案结果必须再调 /copy/result 轮询获取。本函数把这两步收敛到一处,对外仍旧同步风格使用:
 * 返回体与旧同步契约一致({ code, message, data },data 即 { title, subtitle, script, demand, ... }),
 * 调用方无需自己实现轮询,避免各页面各写一份、把"同步假设"复制到多处。
 *
 * @param {Object} data /copy/generate 的入参(template_title/category/images/roles/with_demand 等)
 * @param {Object} [options] timeout:轮询总上限(ms);interval:轮询间隔(ms);onProgress:每次轮询回调
 * @returns {Promise<{code:number,message:string,data?:Object}>} 文案结果(失败时 code=0 且 data 为空)
 */
export async function generateCopy(data, options = {}) {
	const timeout = options.timeout ?? COPY_POLL_TIMEOUT
	const interval = options.interval ?? COPY_POLL_INTERVAL
	const submit = await http.post(COPY_GENERATE_URL, data, { timeout: 30 * 1000 })
	const taskId = submit?.code === 1 ? submit.data?.task_id : null
	if (!taskId) return { code: 0, message: submit?.message || "文案生成任务下发失败" }

	const deadline = Date.now() + timeout
	while (Date.now() < deadline) {
		await new Promise((r) => setTimeout(r, interval))
		const res = await http.post(COPY_RESULT_URL, { task_id: taskId })
		if (res?.code !== 1) return { code: 0, message: res?.message || "文案生成结果查询失败" }
		const status = res.data?.status
		if (status === "done") return { code: 1, message: "文案已生成", data: res.data.result || {} }
		// not_found:worker 未消费/结果 TTL 已过(不再是"还在生成"),继续空转只会让用户干等
		if (status === "not_found") return { code: 0, message: "AI 写作服务未就绪或结果已过期,请重试一次" }
		options.onProgress?.()
	}
	return { code: 0, message: "AI 写作时间过长,请稍后重试" }
}

export default {
	genConfig: {
		url: `${config.API_URL}/v1/base/common/gen-config`,
		name: "业务配置(定价/复刻选项)",
		// 公共配置归属 /v1/base/common 而非支付域,此前错挂在 payment 模块里,
		// 导致"支付模块读定价"与"公共配置"两份入口长期并存,现收敛到 common 一处
		post: async function(data={}, config={}){
			return await http.post(this.url, data, config);
		}
	},
	copyGenerate: {
		url: COPY_GENERATE_URL,
		name: "AI 一键写文案(下单,异步)",
		// 后端已改为异步:本调用只负责下发并立刻返回 task_id,文案需继续轮询 /copy/result。
		// 页面请统一调用 generateCopy(),不要直接读本接口的 data 当文案(那是 task_id,没有 title/script)
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	copyResult: {
		url: COPY_RESULT_URL,
		name: "轮询 AI 文案生成结果",
		// data.status: pending(继续轮询) / done(data.result 为文案) / not_found(任务不存在或已过期)
		post: async function(data, config={}){
			return await http.post(this.url, data, config);
		}
	},
	upload: {
		file: {
			url: UPLOAD_FILE_URL,
			name: "文件上传",
			// 文件上传耗时远高于普通接口,单独放宽超时(全局默认仅 10s,大文件/弱网会被中途掐断报"请求服务器无响应")
			post: async function(data, options={}){
				return await http.post(this.url, data, { timeout: 5 * 60 * 1000, ...options });
			}
		},
		sign: {
			url: UPLOAD_SIGN_URL,
			name: "获取上传预签名URL",
			post: async function(data){
				return await http.post(this.url, data);
			}
		},
	}
}
