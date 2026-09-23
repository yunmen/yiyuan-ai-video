<template>
	<el-container>
		<el-header>
			<div class="left-panel">
				<el-button type="primary" icon="el-icon-pie-chart" @click="openCacheStats">缓存命中统计</el-button>
			</div>
			<div class="right-panel">
				<div class="right-panel-search">
					<el-input v-model="search.task_no" placeholder="任务编号" clearable style="width: 180px"></el-input>
					<el-select v-model="search.type" placeholder="任务类型" clearable style="width: 110px; margin-left: 10px">
						<el-option label="视频" value="video"></el-option>
						<el-option label="数字人" value="digital"></el-option>
						<el-option label="图片" value="image"></el-option>
						<el-option label="音频" value="audio"></el-option>
						<el-option label="文本" value="text"></el-option>
					</el-select>
					<el-select v-model="search.status" placeholder="状态" clearable style="width: 110px; margin-left: 10px">
						<el-option label="生成中" value="processing"></el-option>
						<el-option label="生成成功" value="success"></el-option>
						<el-option label="生成失败" value="failed"></el-option>
					</el-select>
					<el-button type="primary" icon="el-icon-search" style="margin-left: 10px" @click="upsearch"></el-button>
				</div>
			</div>
		</el-header>
		<el-main class="nopadding">
			<scTable ref="table" :apiObj="apiObj" stripe remoteSort remoteFilter>
				<el-table-column label="#" type="index" width="50"></el-table-column>
				<el-table-column label="任务编号" prop="task_no" min-width="180" show-overflow-tooltip></el-table-column>
				<el-table-column label="类型" prop="type" align="center" width="80">
					<template #default="scope">
						<el-tag size="small" effect="plain">{{typeMap[scope.row.type] || scope.row.type}}</el-tag>
					</template>
				</el-table-column>
				<el-table-column label="状态" prop="status" align="center" width="100">
					<template #default="scope">
						<el-tag :type="statusMap[scope.row.status]?.type || 'info'" size="small">{{statusMap[scope.row.status]?.label || scope.row.status}}</el-tag>
					</template>
				</el-table-column>
				<el-table-column label="进度" prop="progress" align="center" width="140">
					<template #default="scope">
						<el-progress :percentage="scope.row.progress || 0" :stroke-width="8" :status="scope.row.status=='failed' ? 'exception' : (scope.row.status=='success' ? 'success' : '')"></el-progress>
					</template>
				</el-table-column>
				<el-table-column label="生成结果" prop="result_video" align="center" width="90">
					<template #default="scope">
						<el-link v-if="scope.row.result_video" type="primary" @click="handlePreview(scope.row)">查看</el-link>
						<span v-else>-</span>
					</template>
				</el-table-column>
				<el-table-column label="失败原因" prop="fail_reason" min-width="140" show-overflow-tooltip>
					<template #default="scope">{{scope.row.fail_reason || '-'}}</template>
				</el-table-column>
				<el-table-column label="用户Id" prop="user_id" align="center" width="90">
					<template #default="scope">{{scope.row.user_id || '-'}}</template>
				</el-table-column>
				<el-table-column label="设备" prop="device" align="center" width="90"></el-table-column>
				<el-table-column label="创建时间" prop="create_time" align="center" width="170"></el-table-column>
				<el-table-column label="操作" fixed="right" align="right" width="140">
					<template #default="scope">
						<el-button-group>
							<el-button text type="primary" size="small" @click="table_show(scope.row)">详情</el-button>
							<el-button v-if="scope.row.result_video" text type="primary" size="small" @click="table_regenerate_segment(scope.row)">局部重跑</el-button>
							<el-button v-if="scope.row.status === 'failed'" text type="warning" size="small" @click="table_resume(scope.row)">断点续跑</el-button>
							<el-popconfirm title="确定删除该任务吗？" @confirm="table_del(scope.row, scope.$index)">
								<template #reference>
									<el-button text type="primary" size="small">删除</el-button>
								</template>
							</el-popconfirm>
						</el-button-group>
					</template>
				</el-table-column>
			</scTable>
		</el-main>
	</el-container>

	<!-- 任务详情弹窗 -->
	<el-dialog v-model="detail.visible" title="任务详情" width="640" destroy-on-close append-to-body>
		<el-descriptions :column="1" border>
			<el-descriptions-item label="任务编号">{{detail.data.task_no}}</el-descriptions-item>
			<el-descriptions-item label="类型">{{typeMap[detail.data.type] || detail.data.type}}</el-descriptions-item>
			<el-descriptions-item label="状态">{{statusMap[detail.data.status]?.label || detail.data.status}}({{detail.data.progress || 0}}%)</el-descriptions-item>
			<el-descriptions-item label="关联模板Id">{{detail.data.template_id || '-'}}</el-descriptions-item>
			<el-descriptions-item label="关联订单号">{{detail.data.order_no || '-'}}</el-descriptions-item>
			<el-descriptions-item label="用户素材">
				<template v-if="detail.data.materials && detail.data.materials.length">
					<div v-for="(url, i) in detail.data.materials" :key="i">
						<el-link :href="url" target="_blank" type="primary">{{url}}</el-link>
					</div>
				</template>
				<span v-else>-</span>
			</el-descriptions-item>
			<el-descriptions-item label="生成参数">
				<pre v-if="detail.data.params" class="json-pre">{{JSON.stringify(detail.data.params, null, 2)}}</pre>
				<span v-else>-</span>
			</el-descriptions-item>
			<el-descriptions-item label="文案备注">{{detail.data.remark || '-'}}</el-descriptions-item>
			<el-descriptions-item label="文本结果">{{detail.data.result_text || '-'}}</el-descriptions-item>
			<el-descriptions-item label="失败原因">{{detail.data.fail_reason || '-'}}</el-descriptions-item>
			<el-descriptions-item label="创建时间">{{detail.data.create_time}}</el-descriptions-item>
		</el-descriptions>
	</el-dialog>

	<!-- 缓存命中统计抽屉 -->
	<el-drawer v-model="cache.visible" title="中间产物缓存命中统计" size="640px" destroy-on-close append-to-body>
		<el-descriptions :column="2" border size="small">
			<el-descriptions-item label="缓存条目">{{cache.data.total ?? '-'}}</el-descriptions-item>
			<el-descriptions-item label="命中次数">{{cache.data.hits ?? '-'}}</el-descriptions-item>
			<el-descriptions-item label="命中率">{{hitRateText}}</el-descriptions-item>
			<el-descriptions-item label="缓存天数">{{cache.data.ttl_days ?? '-'}} 天</el-descriptions-item>
		</el-descriptions>
		<el-alert type="info" :closable="false" show-icon style="margin: 12px 0"
			title="命中率 = 命中次数 / (条目数 + 命中次数):每条缓存首次生成算未命中,之后每次复用 +1。该比例可直接换算成「少调用了几次付费接口」。" />

		<div class="cache-section">按类型分布</div>
		<el-table :data="cache.data.by_type || []" size="small" border v-loading="cache.loading">
			<el-table-column label="产物类型" prop="asset_type" min-width="140"></el-table-column>
			<el-table-column label="条目数" prop="count" align="center" width="90"></el-table-column>
			<el-table-column label="命中次数" prop="hits" align="center" width="100"></el-table-column>
		</el-table>

		<div class="cache-section">复用最多 Top10</div>
		<el-table :data="cache.data.top || []" size="small" border v-loading="cache.loading">
			<el-table-column label="类型" prop="asset_type" width="130"></el-table-column>
			<el-table-column label="任务" prop="task_type" align="center" width="70"></el-table-column>
			<el-table-column label="命中" prop="hit_count" align="center" width="70"></el-table-column>
			<el-table-column label="最近命中" prop="update_time" align="center" width="150"></el-table-column>
			<el-table-column label="内容预览" prop="preview" min-width="180" show-overflow-tooltip></el-table-column>
			<template #empty>
				<span>暂无命中记录 —— 缓存只在「同一份输入再次生成」时才会命中</span>
			</template>
		</el-table>

		<template #footer>
			<el-button @click="loadCacheStats">刷新</el-button>
			<el-popconfirm title="确定清理已过期的缓存吗？" @confirm="cache_clear">
				<template #reference>
					<el-button type="warning">清理过期缓存</el-button>
				</template>
			</el-popconfirm>
		</template>
	</el-drawer>

	<!-- 结果预览弹窗 -->
	<el-dialog v-model="preview.visible" title="生成结果预览" width="480" destroy-on-close append-to-body>
		<video v-if="preview.visible && preview.isVideo" :src="preview.url" controls autoplay style="width: 100%; border-radius: 4px"></video>
		<el-image v-else-if="preview.visible" :src="preview.url" fit="contain" style="width: 100%"></el-image>
	</el-dialog>

	<!-- 局部重跑:改一句台词重生成 -->
	<el-dialog v-model="seg.visible" title="局部重跑(改一句台词重生成)" width="460" destroy-on-close append-to-body>
		<el-form label-width="90px">
			<el-form-item label="任务编号">{{seg.row.task_no}}</el-form-item>
			<el-form-item label="分段下标">
				<el-input-number v-model="seg.index" :min="0" :step="1" />
			</el-form-item>
			<el-form-item label="新口播文案">
				<el-input v-model="seg.text" type="textarea" :rows="3" placeholder="留空则沿用原台词" />
			</el-form-item>
		</el-form>
		<template #footer>
			<el-button @click="seg.visible=false">取消</el-button>
			<el-button type="primary" :loading="seg.loading" @click="submitSeg">提交重跑</el-button>
		</template>
	</el-dialog>
</template>

<script>
	export default {
		name: 'videoTask',
		data() {
			return {
				apiObj: this.$API.video.task.list,
				search: {
					task_no: null,
					type: null,
					status: null
				},
				typeMap: {
					video: '视频',
					digital: '数字人',
					image: '图片',
					audio: '音频',
					text: '文本'
				},
				statusMap: {
					processing: {label: '生成中', type: 'warning'},
					success: {label: '生成成功', type: 'success'},
					failed: {label: '生成失败', type: 'danger'}
				},
				detail: {
					visible: false,
					data: {}
				},
				preview: {
					visible: false,
					url: '',
					isVideo: true
				},
				cache: {
					visible: false,
					loading: false,
					data: {}
				},
				seg: {
					visible: false,
					row: {},
					index: 0,
					text: '',
					loading: false
				}
			}
		},
		computed: {
			hitRateText(){
				const rate = this.cache.data.hit_rate
				if(rate === undefined || rate === null){
					return '-'
				}
				return (Number(rate) * 100).toFixed(1) + '%'
			}
		},
		methods: {
			handlePreview(row){
				this.preview.url = row.result_video
				this.preview.isVideo = row.type === 'video' || row.type === 'digital'
				this.preview.visible = true
			},
			async table_show(row){
				var res = await this.$API.video.task.detail.get({id: row.id});
				if(res.code == 1){
					this.detail.data = res.data
					this.detail.visible = true
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			async table_del(row, index){
				var res = await this.$API.video.task.delete.get({id: row.id});
				if(res.code == 1){
					this.$refs.table.tableData.splice(index, 1);
					this.$message.success("删除成功")
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			async table_resume(row){
				var res = await this.$API.video.task.resume.get({id: row.id});
				if(res.code == 1){
					this.$message.success("已断点续跑，将从上次中断处继续生成")
					this.$refs.table.upData(this.search)
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			table_regenerate_segment(row){
				this.seg.row = row
				this.seg.index = 0
				this.seg.text = ''
				this.seg.visible = true
			},
			async submitSeg(){
				this.seg.loading = true
				try {
					var res = await this.$API.video.task.regenerateSegment.get({
						id: this.seg.row.id,
						segment_index: this.seg.index,
						new_text: this.seg.text,
					})
					if(res.code == 1){
						this.$message.success("已提交局部重跑，将改一句台词后拼回原片")
						this.seg.visible = false
						this.$refs.table.upData(this.search)
					}else{
						this.$alert(res.message, "提示", {type: 'error'})
					}
				} finally {
					this.seg.loading = false
				}
			},
			upsearch(){
				this.$refs.table.upData(this.search)
			},
			// 中间产物缓存命中统计(P2 降本可观测)
			async openCacheStats(){
				this.cache.visible = true
				await this.loadCacheStats()
			},
			async loadCacheStats(){
				this.cache.loading = true
				var res = await this.$API.video.task.cacheStats.get({});
				this.cache.loading = false
				if(res.code == 1){
					this.cache.data = res.data || {}
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			async cache_clear(){
				var res = await this.$API.video.task.cacheClear.get({});
				if(res.code == 1){
					this.$message.success("已清理 " + ((res.data && res.data.removed) || 0) + " 条过期缓存")
					await this.loadCacheStats()
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			}
		}
	}
</script>

<style scoped>
	.json-pre {
		margin: 0;
		white-space: pre-wrap;
		word-break: break-all;
		font-size: 12px;
	}
	.cache-section {
		margin: 14px 0 8px;
		font-weight: bold;
	}
</style>
