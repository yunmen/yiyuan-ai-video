<template>
	<el-container>
		<el-header>
			<div class="left-panel">
				<el-button type="primary" icon="el-icon-plus" @click="add">新增分类</el-button>
			</div>
			<div class="right-panel">
				<div class="right-panel-search">
					<el-input v-model="search.keyword" placeholder="分类名称" clearable style="width: 180px"></el-input>
					<el-button type="primary" icon="el-icon-search" style="margin-left: 10px" @click="upsearch"></el-button>
				</div>
			</div>
		</el-header>
		<el-main class="nopadding">
			<scTable ref="table" :apiObj="apiObj" stripe>
				<el-table-column label="#" type="index" width="50"></el-table-column>
				<el-table-column label="分类名称" prop="name" min-width="140"></el-table-column>
				<el-table-column label="图标" prop="cover" align="center" width="90">
					<template #default="scope">
						<el-image v-if="scope.row.cover" :src="scope.row.cover" style="width:40px;height:40px;border-radius:6px" fit="cover"></el-image>
						<span v-else>-</span>
					</template>
				</el-table-column>
				<el-table-column label="模板数" prop="template_count" align="center" width="90"></el-table-column>
				<el-table-column label="排序" prop="sort" align="center" width="80"></el-table-column>
				<el-table-column label="状态" prop="active" align="center" width="90">
					<template #default="scope">
						<el-tag :type="scope.row.active ? 'success' : 'info'" size="small">{{scope.row.active ? '启用' : '停用'}}</el-tag>
					</template>
				</el-table-column>
				<el-table-column label="备注" prop="remark" min-width="120" show-overflow-tooltip>
					<template #default="scope">{{scope.row.remark || '-'}}</template>
				</el-table-column>
				<el-table-column label="创建时间" prop="create_time" align="center" width="170"></el-table-column>
				<el-table-column label="操作" fixed="right" align="right" width="140">
					<template #default="scope">
						<el-button-group>
							<el-button text type="primary" size="small" @click="edit(scope.row)">编辑</el-button>
							<el-popconfirm title="确定删除该分类吗？" @confirm="del(scope.row)">
								<template #reference>
									<el-button text type="danger" size="small">删除</el-button>
								</template>
							</el-popconfirm>
						</el-button-group>
					</template>
				</el-table-column>
			</scTable>
		</el-main>
	</el-container>

	<save-dialog v-if="dialog.save" ref="saveDialog" @success="handleSaveSuccess" @closed="dialog.save=false"></save-dialog>
</template>

<script>
	import saveDialog from './save.vue'

	export default {
		name: 'videoCategory',
		components: {saveDialog},
		data() {
			return {
				apiObj: this.$API.video.category.list,
				search: {keyword: null},
				dialog: {save: false}
			}
		},
		methods: {
			add(){
				this.dialog.save = true
				this.$nextTick(() => { this.$refs.saveDialog.open('add') })
			},
			edit(row){
				this.dialog.save = true
				this.$nextTick(() => { this.$refs.saveDialog.open('edit').setData(row) })
			},
			async del(row){
				var res = await this.$API.video.category.delete.get({id: row.id})
				if(res.code == 1){
					this.$message.success("删除成功")
					this.refresh()
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			handleSaveSuccess(){ this.refresh() },
			refresh(){ this.$refs.table.refresh() },
			upsearch(){ this.$refs.table.upData(this.search) }
		}
	}
</script>

<style scoped>
</style>
