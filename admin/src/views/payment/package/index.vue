<template>
	<el-container>
		<el-header>
			<div class="left-panel">
				<el-button type="primary" icon="el-icon-plus" @click="add">新增套餐</el-button>
			</div>
			<div class="right-panel">
				<div class="right-panel-search">
					<el-button icon="el-icon-refresh" @click="refresh"></el-button>
				</div>
			</div>
		</el-header>
		<el-main class="nopadding">
			<scTable ref="table" :apiObj="apiObj" stripe>
				<el-table-column label="#" type="index" width="50"></el-table-column>
				<el-table-column label="套餐名称" prop="name" min-width="120"></el-table-column>
				<el-table-column label="副标题" prop="sub_title" min-width="140" show-overflow-tooltip>
					<template #default="scope">{{scope.row.sub_title || '-'}}</template>
				</el-table-column>
				<el-table-column label="到账额度" prop="credits" align="right" width="100">
					<template #default="scope">{{scope.row.credits}} 次</template>
				</el-table-column>
				<el-table-column label="售价(元)" prop="price" align="right" width="100"></el-table-column>
				<el-table-column label="单价(元/次)" align="right" width="110">
					<template #default="scope">
						{{scope.row.credits ? (Number(scope.row.price) / scope.row.credits).toFixed(2) : '-'}}
					</template>
				</el-table-column>
				<el-table-column label="角标" prop="tag" align="center" width="90">
					<template #default="scope">
						<el-tag v-if="scope.row.tag" type="danger" size="small">{{scope.row.tag}}</el-tag>
						<span v-else>-</span>
					</template>
				</el-table-column>
				<el-table-column label="排序" prop="sort" align="center" width="80"></el-table-column>
				<el-table-column label="状态" prop="active" align="center" width="90">
					<template #default="scope">
						<el-tag :type="scope.row.active ? 'success' : 'info'" size="small">{{scope.row.active ? '上架' : '下架'}}</el-tag>
					</template>
				</el-table-column>
				<el-table-column label="创建时间" prop="create_time" align="center" width="170"></el-table-column>
				<el-table-column label="操作" fixed="right" align="right" width="140">
					<template #default="scope">
						<el-button-group>
							<el-button text type="primary" size="small" @click="edit(scope.row)">编辑</el-button>
							<el-popconfirm title="确定删除该套餐吗？" @confirm="del(scope.row)">
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
		name: 'paymentPackage',
		components: {saveDialog},
		data() {
			return {
				apiObj: this.$API.payment.package.list,
				dialog: {save: false}
			}
		},
		methods: {
			add(){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open('add')
				})
			},
			edit(row){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open('edit').setData(row)
				})
			},
			async del(row){
				var res = await this.$API.payment.package.delete.get({id: row.id})
				if(res.code == 1){
					this.$message.success("删除成功")
					this.refresh()
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			handleSaveSuccess(){
				this.refresh()
			},
			refresh(){
				this.$refs.table.refresh()
			}
		}
	}
</script>

<style scoped>
</style>
