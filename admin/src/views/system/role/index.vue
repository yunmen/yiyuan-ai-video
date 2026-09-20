<template>
	<el-container>
		<el-header>
			<div class="left-panel">
				<el-button type="primary" icon="el-icon-plus" @click="add">新增</el-button>
			</div>
			<div class="right-panel">
				<div class="right-panel-search">
					<el-input v-model="search.name" placeholder="角色名称" clearable></el-input>
					<el-select v-model="search.active" placeholder="状态" style="width: 100%" clearable>
						<el-option v-for="item in options" :key="item.value" :label="item.label" :value="item.value"></el-option>
					</el-select>
					<el-button type="primary" icon="el-icon-search" @click="upsearch"></el-button>
				</div>
			</div>
		</el-header>
		<el-main class="nopadding">
			<scTable ref="table" :apiObj="apiObj" row-key="id" stripe>
				<el-table-column label="#" type="index" ></el-table-column>
				<el-table-column label="名称" prop="name" align="center"></el-table-column>
				<el-table-column label="别名" prop="alias" align="center"></el-table-column>
				<el-table-column label="状态" prop="active" align="center">
					<template #default="scope">
						<el-switch v-model="scope.row.active" @change="changeSwitch($event, scope.row)" :loading="scope.row.$switch_status" :active-value="true" :inactive-value="false"></el-switch>
					</template>
				</el-table-column>
				<el-table-column label="备注" prop="desc" align="center"></el-table-column>
				<el-table-column label="创建时间" prop="create_time" align="center"></el-table-column>
				<el-table-column label="操作" fixed="right" align="right" >
					<template #default="scope">
						<el-button-group>
							<el-button text type="primary" size="small" @click="permission(scope.row, scope.$index)">权限</el-button>
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

	<permission-dialog v-if="dialog.permission" ref="permissionDialog" @closed="dialog.permission=false"></permission-dialog>

</template>

<script>
	import saveDialog from './save.vue'
	import permissionDialog from './permission.vue'

	export default {
		name: 'system.role',
		components: {
			saveDialog,
			permissionDialog
		},
		data() {
			return {
				dialog: {
					save: false,
					permission: false
				},
				options: [
					{ value: true, label: "启用" },
					{ value: false, label: "禁用" },
				],
				apiObj: this.$API.system.role.list,
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
			//权限设置
			permission(row){
				this.dialog.permission = true
				this.$nextTick(() => {
					this.$refs.permissionDialog.open().setData(row)
				})
			},
			//删除
			async table_del(row){
				var reqData = {id: row.id}
				var res = await this.$API.system.role.delete.get(reqData);
				if(res.code == 1){
					this.$refs.table.refresh()
					this.$message.success("删除成功")
				}
			},
			//表格内开关
			async changeSwitch(val, row){
				row.$switch_status = true;
				let data = { id: row.id}
				var res = await this.$API.system.role.active.get(data);
				if (res.code == 1) {
					delete row.$switch_status;
					this.$message.success("操作成功")
				}
			},
			//搜索
			upsearch(){
				this.$refs.table.upData(this.search)
			},
			//本地更新数据
			handleSaveSuccess(data, mode){
				if(mode=='add'){
					this.$refs.table.refresh()
				}else if(mode=='edit'){
					this.$refs.table.refresh()
				}
			}
		}
	}
</script>

<style>
</style>
