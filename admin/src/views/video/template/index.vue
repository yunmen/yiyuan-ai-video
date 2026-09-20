<template>
	<el-container>
		<el-header>
			<div class="left-panel">
				<el-button type="primary" icon="el-icon-plus" @click="add">新增模板</el-button>
			</div>
			<div class="right-panel">
				<div class="right-panel-search">
					<el-input v-model="search.keyword" placeholder="标题关键词" clearable style="width: 160px"></el-input>
					<el-input v-model="search.category" placeholder="分类" clearable style="width: 120px; margin-left: 10px"></el-input>
					<el-select v-model="search.active" placeholder="状态" clearable style="width: 110px; margin-left: 10px">
						<el-option label="已上架" :value="true"></el-option>
						<el-option label="已下架" :value="false"></el-option>
					</el-select>
					<el-button type="primary" icon="el-icon-search" style="margin-left: 10px" @click="upsearch"></el-button>
				</div>
			</div>
		</el-header>
		<el-main class="nopadding">
			<scTable ref="table" :apiObj="apiObj" stripe remoteSort remoteFilter>
				<el-table-column label="#" type="index" width="50"></el-table-column>
				<el-table-column label="封面" prop="cover" align="center" width="90">
					<template #default="scope">
						<el-image v-if="scope.row.cover" :src="scope.row.cover" :preview-src-list="[scope.row.cover]" fit="cover" style="width: 48px; height: 48px; border-radius: 4px" hide-on-click-modal preview-teleported></el-image>
						<span v-else>-</span>
					</template>
				</el-table-column>
				<el-table-column label="模板标题" prop="title" min-width="140" show-overflow-tooltip></el-table-column>
				<el-table-column label="分类" prop="category" align="center" width="110"></el-table-column>
				<el-table-column label="标签" prop="tags" align="center" min-width="150">
					<template #default="scope">
						<template v-if="scope.row.tags && scope.row.tags.length">
							<el-tag v-for="tag in scope.row.tags" :key="tag" size="small" style="margin-right: 4px">{{tag}}</el-tag>
						</template>
						<span v-else>-</span>
					</template>
				</el-table-column>
				<el-table-column label="时长" prop="duration" align="center" width="70">
					<template #default="scope">{{scope.row.duration}}s</template>
				</el-table-column>
				<el-table-column label="热度" prop="hot" align="center" width="80" sortable="custom"></el-table-column>
				<el-table-column label="使用次数" prop="use_count" align="center" width="90" sortable="custom"></el-table-column>
				<el-table-column label="示例视频" prop="video_url" align="center" width="90">
					<template #default="scope">
						<el-link v-if="scope.row.video_url" type="primary" @click="handlePreview(scope.row)">预览</el-link>
						<span v-else>-</span>
					</template>
				</el-table-column>
				<el-table-column label="首页推荐" prop="recommend" align="center" width="110">
					<template #default="scope">
						<el-switch v-model="scope.row.recommend" @change="changeRecommend($event, scope.row)" :loading="scope.row.$recommend_status" :active-value="true" :inactive-value="false" inline-prompt active-text="推荐" inactive-text="普通"></el-switch>
					</template>
				</el-table-column>
				<el-table-column label="状态" prop="active" align="center" width="90">
					<template #default="scope">
						<el-switch v-model="scope.row.active" @change="changeSwitch($event, scope.row)" :loading="scope.row.$switch_status" :active-value="true" :inactive-value="false" inline-prompt active-text="上架" inactive-text="下架"></el-switch>
					</template>
				</el-table-column>
				<el-table-column label="创建时间" prop="create_time" align="center" width="170"></el-table-column>
				<el-table-column label="操作" fixed="right" align="right" width="200">
					<template #default="scope">
						<el-button-group>
							<el-button text type="primary" size="small" @click="table_show(scope.row)">查看</el-button>
							<el-button text type="primary" size="small" @click="table_edit(scope.row)">编辑</el-button>
							<el-popconfirm title="确定删除该模板吗？" @confirm="table_del(scope.row, scope.$index)">
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

	<save-dialog v-if="dialog.save" ref="saveDialog" @success="handleSuccess" @closed="dialog.save=false"></save-dialog>

	<!-- 预览视频弹窗 -->
	<el-dialog v-model="preview.visible" :title="`预览 - ${preview.name}`" width="480" destroy-on-close append-to-body>
		<video v-if="preview.visible" :src="preview.url" controls autoplay style="width: 100%; border-radius: 4px"></video>
	</el-dialog>
</template>

<script>
	import saveDialog from './save.vue'

	export default {
		name: 'videoTemplate',
		components: {
			saveDialog
		},
		data() {
			return {
				dialog: {
					save: false
				},
				apiObj: this.$API.video.template.list,
				search: {
					keyword: null,
					category: null,
					active: null
				},
				preview: {
					visible: false,
					url: '',
					name: ''
				}
			}
		},
		methods: {
			handlePreview(row){
				this.preview.url = row.video_url
				this.preview.name = row.title
				this.preview.visible = true
			},
			add(){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open()
				})
			},
			table_edit(row){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open('edit').setData(row)
				})
			},
			table_show(row){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open('show').setData(row)
				})
			},
			async table_del(row, index){
				var res = await this.$API.video.template.delete.get({id: row.id});
				if(res.code == 1){
					this.$refs.table.tableData.splice(index, 1);
					this.$message.success("删除成功")
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			//上架/下架切换(后端接口为取反切换,仅传 id)
			async changeSwitch(val, row){
				row.$switch_status = true;
				var res = await this.$API.video.template.active.get({id: row.id});
				delete row.$switch_status;
				if (res.code == 1) {
					row.active = res.data.active
					this.$message.success("操作成功")
				}else{
					row.active = !val
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			//首页推荐位开关(后端接口为取反切换,仅传 id)
			async changeRecommend(val, row){
				row.$recommend_status = true;
				var res = await this.$API.video.template.recommend.get({id: row.id});
				delete row.$recommend_status;
				if (res.code == 1) {
					row.recommend = res.data.recommend
					this.$message.success("操作成功")
				}else{
					row.recommend = !val
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			upsearch(){
				this.$refs.table.upData(this.search)
			},
			handleSuccess(data, mode){
				if(mode=='add'){
					this.$refs.table.refresh()
				}else if(mode=='edit'){
					Object.assign(this.$refs.table.tableData.find(item => item.id===data.id) || {}, data)
				}
			}
		}
	}
</script>

<style scoped>
</style>
