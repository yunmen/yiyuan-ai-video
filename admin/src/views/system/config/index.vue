<template>
	<el-container>
		<el-container>
				<el-header>
					<div class="left-panel">
						<el-button type="primary" icon="el-icon-plus" @click="add"></el-button>
					</div>
					<div class="right-panel">
						<div class="right-panel-search">
							<el-input v-model="search.keyword" placeholder="配置键/说明" clearable></el-input>
							<el-button type="primary" icon="el-icon-search" @click="upsearch"></el-button>
						</div>
					</div>
				</el-header>
				<el-main class="nopadding">
					<scTable ref="table" :apiObj="apiObj" stripe remoteSort remoteFilter>
						<el-table-column label="#" type="index"></el-table-column>
						<el-table-column label="配置键" prop="key" width="220" show-overflow-tooltip></el-table-column>
						<el-table-column label="配置值" prop="value" show-overflow-tooltip></el-table-column>
						<el-table-column label="分组" prop="group" align="center" width="100"></el-table-column>
						<el-table-column label="说明" prop="remark" show-overflow-tooltip></el-table-column>
						<el-table-column label="公开" prop="is_public" align="center" width="80">
							<template #default="scope">
								<el-tag v-if="scope.row.is_public" type="success" size="small">公开</el-tag>
								<el-tag v-else type="info" size="small">私有</el-tag>
							</template>
						</el-table-column>
						<el-table-column label="操作" fixed="right" align="right" width="160">
							<template #default="scope">
								<el-button-group>
									<el-button text type="primary" size="small" @click="table_show(scope.row)">查看</el-button>
									<el-button text type="primary" size="small" @click="table_edit(scope.row)">编辑</el-button>
								</el-button-group>
							</template>
						</el-table-column>
					</scTable>
				</el-main>
		</el-container>
	</el-container>

	<save-dialog v-if="dialog.save" ref="saveDialog" @success="handleSuccess" @closed="dialog.save=false"></save-dialog>

</template>

<script>
	import saveDialog from './save.vue'

	export default {
		name: 'system.config',
		components: {
			saveDialog
		},
		data() {
			return {
				dialog: {
					save: false
				},
				apiObj: this.$API.system.config.list,
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
			//搜索
			upsearch(){
				this.$refs.table.upData(this.search)
			},
			//本地更新数据
			handleSuccess(data, mode){
				if(mode=='add'){
					this.$refs.table.refresh()
				}else if(mode=='edit'){
					this.$refs.table.tableData.filter(item => item.key===data.key ).forEach(item => {
						Object.assign(item, data)
					})
				}
			}
		}
	}
</script>

<style>
</style>
