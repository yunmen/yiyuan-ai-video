<template>
	<el-container>
		<el-header>
			<div class="left-panel"></div>
			<div class="right-panel">
				<div class="right-panel-search">
					<el-input v-model="search.task_no" placeholder="任务编号" clearable style="width: 180px"></el-input>
					<el-select v-model="search.type" placeholder="任务类型" clearable style="width: 110px; margin-left: 10px">
						<el-option label="视频" value="video"></el-option>
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

	<!-- 结果预览弹窗 -->
	<el-dialog v-model="preview.visible" title="生成结果预览" width="480" destroy-on-close append-to-body>
		<video v-if="preview.visible && preview.isVideo" :src="preview.url" controls autoplay style="width: 100%; border-radius: 4px"></video>
		<el-image v-else-if="preview.visible" :src="preview.url" fit="contain" style="width: 100%"></el-image>
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
				}
			}
		},
		methods: {
			handlePreview(row){
				this.preview.url = row.result_video
				this.preview.isVideo = row.type === 'video'
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
			upsearch(){
				this.$refs.table.upData(this.search)
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
</style>
