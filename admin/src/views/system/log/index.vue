<template>
	<el-container>
		<el-header>
			<div class="left-panel">
			</div>
			<div class="right-panel">
				<div class="right-panel-search">
					<el-input v-model="search.request_id" placeholder="请求编号" clearable></el-input>
					<el-input v-model="search.summary" placeholder="请求名称" clearable></el-input>
					<el-input v-model="search.url" placeholder="请求地址" clearable></el-input>
					<el-input v-model="search.client_ip" placeholder="请求IP" clearable></el-input>
					<el-input v-model="search.status_code" placeholder="状态码" clearable></el-input>
					<el-input v-model="search.operator_account" placeholder="操作人账号" clearable></el-input>
					<el-input v-model="search.operator_nickname" placeholder="操作人昵称" clearable></el-input>
					<el-button type="primary" icon="el-icon-search" @click="upsearch"></el-button>
				</div>
			</div>
		</el-header>
		<el-main class="nopadding">
			<scTable ref="table" :apiObj="apiObj" row-key="id" stripe>
				<el-table-column label="#" type="index" width="50"></el-table-column>
				<el-table-column label="创建时间" prop="create_time" width="160"></el-table-column>
				<el-table-column label="请求编号" prop="request_id" width="260"></el-table-column>
				<el-table-column label="请求名称" prop="summary" width="120"></el-table-column>
				<el-table-column label="请求地址" prop="url" width="300" show-overflow-tooltip></el-table-column>
				<el-table-column label="请求类型" prop="method" width="80"></el-table-column>
				<el-table-column label="请求IP" prop="client_ip" width="120"></el-table-column>
				<el-table-column label="状态码" prop="status_code" width="80"></el-table-column>
				<el-table-column label="响应时间" prop="process_time" width="90"></el-table-column>
				<el-table-column label="客户端" prop="client_type" width="90"></el-table-column>
				<el-table-column label="操作人账号" prop="operator_account" width="120"></el-table-column>
				<el-table-column label="操作人昵称" prop="operator_nickname" width="120"></el-table-column>
				<el-table-column label="操作" fixed="right" align="right" width="60">
					<template #default="scope">
						<el-button-group>
							<el-button text type="primary" size="small" @click="table_show(scope.row, scope.$index)">查看</el-button>
						</el-button-group>
					</template>
				</el-table-column>

			</scTable>
		</el-main>
	</el-container>

	<info-dialog v-if="dialog.info" ref="infoDialog" @closed="dialog.info=false"></info-dialog>


</template>

<script>
	import infoDialog from './info.vue'

	export default {
		name: 'system.log',
		components: {
			infoDialog
		},
		data() {
			return {
				dialog: {
					info: false
				},
				apiObj: this.$API.system.log.list,
				search: {}
			}
		},
		methods: {
			//查看
			table_show(row){
				this.dialog.info = true
				this.$nextTick(() => {
					this.$refs.infoDialog.open(row);
				})
			},
			//搜索
			upsearch(){
				this.$refs.table.upData(this.search)
			},
		}
	}
</script>

<style>
</style>
