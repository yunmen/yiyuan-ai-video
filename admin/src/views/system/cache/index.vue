<template>
	<el-container>
		<el-header>
			<div class="left-panel">
				<el-button type="danger" icon="el-icon-delete" @click="batch_del">批量强退</el-button>
			</div>
		</el-header>
		<el-main class="nopadding">
			<scTable ref="table" :data="data" row-key="id" @selection-change="selectionChange" stripe>
				<el-table-column type="selection" width="50"></el-table-column>
				<el-table-column type="index" label="#" width="50"></el-table-column>
				<el-table-column label="账号" prop="account"></el-table-column>
				<el-table-column label="昵称" prop="nickname"></el-table-column>
				<el-table-column label="登录时间" prop="last_login_time" width="250"></el-table-column>
				<el-table-column label="登录IP" prop="last_login_ip" width="250"></el-table-column>
				<el-table-column label="登录方式" prop="last_login_type" width="250">
					<template #default="scope">
						{{ scope.row.last_login_type == 1 ? '账号密码登录' : scope.row.last_login_type == 2 ? '手机验证码登录' : '未知类型' }}
					</template>
				</el-table-column>

				<el-table-column label="操作" fixed="right" align="right" width="120">
					<template #default="scope">
						<el-button-group>
							<el-popconfirm title="确定强退吗？" @confirm="table_del(scope.row, scope.$index)">
								<template #reference>
									<el-button text type="danger" size="small" icon="el-icon-delete">强退</el-button>
								</template>
							</el-popconfirm>
						</el-button-group>
					</template>
				</el-table-column>
			</scTable>
		</el-main>
	</el-container>
	
	
</template>

<script>
	export default {
		name: 'system.cache',
		components: {
			
		},
		data() {
			return {
				dialog: {},
				data: [],
				search: {},
				selection: []
			}
		},
		mounted() {
			this.get_admin_token();
		},
		methods: {
			async get_admin_token(){
				var res = await this.$API.system.cache.admin.all.get()
				if (res.code == 1){
					this.data = res.data;
				}
			},
			//表格选择后回调事件
			selectionChange(selection){
				this.selection = selection;
			},
			//批量删除
			async batch_del(){
				this.$confirm(`确定强退选中的 ${this.selection.length} 项吗？`, '提示', {
					type: 'warning'
				}).then(async () => {
					const loading = this.$loading();
					var keys = []
					this.selection.forEach(item => {
						keys.push(item.account)
					})
					var res = await this.$API.system.cache.admin.delete.get({keys: keys})
					if (res.code == 1){
						this.get_admin_token();
						this.$message.success("操作成功")
					}
					loading.close();
				}).catch(() => {

				})
			},
			async table_del(row){
				var reqData = {keys: [row.account]}
				var res = await this.$API.system.cache.admin.delete.get(reqData)
				if (res.code == 1){
					this.get_admin_token();
					this.$message.success("操作成功")
				}
			}
		}
	}
</script>

<style>
</style>
