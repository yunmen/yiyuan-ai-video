<template>
	<el-container>
		<el-header>
			<div class="left-panel">
				<el-button type="primary" icon="el-icon-plus" @click="add">新增</el-button>
			</div>
			<div class="right-panel">
				<div class="right-panel-search">
					<el-button type="primary" icon="el-icon-search" @click="upsearch"></el-button>
				</div>
			</div>
		</el-header>
		<el-main class="nopadding">
			<scTable ref="table" :apiObj="apiObj" row-key="id" hidePagination>
				<el-table-column label="#" type="index"></el-table-column>
				<el-table-column label="名称" prop="name" align="center"></el-table-column>
				<el-table-column label="排序" prop="order" align="center"></el-table-column>
				<el-table-column label="状态" prop="active" align="center">
					<template #default="scope">
						<el-switch v-model="scope.row.active" @change="changeSwitch($event, scope.row)" :loading="scope.row.$switch_status" :active-value="true" :inactive-value="false"></el-switch>
					</template>
				</el-table-column>
				<el-table-column label="创建时间" prop="create_time" align="center"></el-table-column>
				<el-table-column label="说明" prop="desc" align="center"></el-table-column>
				<el-table-column label="操作" fixed="right" align="right" width="170">
					<template #default="scope">
						<el-button-group>
							<el-button text type="primary" size="small" @click="table_show(scope.row, scope.$index)">查看</el-button>
							<el-button text type="primary" size="small" @click="table_edit(scope.row, scope.$index)">编辑</el-button>
							<el-popconfirm title="确定删除吗？" @confirm="table_del(scope.row, scope.$index)">
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

	<save-dialog v-if="dialog.save" ref="saveDialog" @success="handleSaveSuccess" @closed="dialog.save=false"></save-dialog>

</template>

<script>
	import saveDialog from './save.vue'

	export default {
		name: 'system.dept',
		components: {
			saveDialog
		},
		data() {
			return {
				dialog: {
					save: false
				},
				apiObj: this.$API.system.dept.tree,
				search: {}
			}
		},
		methods: {
			//添加
			add(){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open()
				})
			},
			//编辑
			table_edit(row){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open('edit').setData(row)
				})
			},
			//查看
			table_show(row){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open('show').setData(row)
				})
			},
			//删除
			async table_del(row){
				var reqData = {id: row.id}
				var res = await this.$API.system.dept.delete.get(reqData);
				if(res.code == 1){
					this.$refs.table.refresh()
					this.$message.success("删除成功")
				}
			},
			//表格内开关
			async changeSwitch(val, row){
				row.$switch_status = true;
				let data = { id: row.id}
				var res = await this.$API.system.dept.active.get(data);
				if (res.code == 1) {
					delete row.$switch_status;
					this.$message.success("操作成功")
				}
			},
			//搜索
			upsearch(){
				this.$refs.table.upData(this.search)
			},
			//根据ID获取树结构
			filterTree(id){
				var target = null;
				function filter(tree){
					tree.forEach(item => {
						if(item.id == id){
							target = item
						}
						if(item.children){
							filter(item.children)
						}
					})
				}
				filter(this.$refs.table.tableData)
				return target
			},
			//本地更新数据
			handleSaveSuccess(){
				this.$refs.table.refresh()
			}
		}
	}
</script>

<style>
</style>
