<template>
	<el-container>
		<el-header>
			<div class="left-panel"></div>
			<div class="right-panel">
				<div class="right-panel-search">
					<el-input v-model="search.keyword" placeholder="手机号/昵称" clearable style="width: 180px"></el-input>
					<el-button type="primary" icon="el-icon-search" style="margin-left: 10px" @click="upsearch"></el-button>
				</div>
			</div>
		</el-header>
		<el-main class="nopadding">
			<scTable ref="table" :apiObj="apiObj" stripe>
				<el-table-column label="#" type="index" width="50"></el-table-column>
				<el-table-column label="用户Id" prop="id" align="center" width="80"></el-table-column>
				<el-table-column label="手机号" prop="account" min-width="130"></el-table-column>
				<el-table-column label="昵称" prop="nickname" min-width="120" show-overflow-tooltip></el-table-column>
				<el-table-column label="免费额度" prop="free_credits" align="right" width="100"></el-table-column>
				<el-table-column label="付费额度" prop="credits" align="right" width="100"></el-table-column>
				<el-table-column label="合计" prop="total" align="right" width="90">
					<template #default="scope">
						<b>{{scope.row.total}}</b>
					</template>
				</el-table-column>
				<el-table-column label="状态" prop="status" align="center" width="80">
					<template #default="scope">
						<el-tag :type="scope.row.status ? 'success' : 'danger'" size="small">{{scope.row.status ? '正常' : '禁用'}}</el-tag>
					</template>
				</el-table-column>
				<el-table-column label="注册时间" prop="create_time" align="center" width="170"></el-table-column>
				<el-table-column label="操作" fixed="right" align="right" width="180">
					<template #default="scope">
						<el-button-group>
							<el-button text type="primary" size="small" @click="handleGrant(scope.row)">赠送</el-button>
							<el-button text type="primary" size="small" @click="handleLogs(scope.row)">流水</el-button>
						</el-button-group>
					</template>
				</el-table-column>
			</scTable>
		</el-main>
	</el-container>

	<!-- 赠送额度 -->
	<el-dialog v-model="grant.visible" title="赠送额度" width="420" destroy-on-close append-to-body>
		<el-form label-width="90px" label-position="left">
			<el-form-item label="用户">
				<span>{{grant.row?.account}} {{grant.row?.nickname ? `(${grant.row.nickname})` : ''}}</span>
			</el-form-item>
			<el-form-item label="赠送次数">
				<el-input-number v-model="grant.amount" :min="1" :max="100000"></el-input-number>
			</el-form-item>
			<el-form-item label="备注">
				<el-input v-model="grant.remark" placeholder="如:活动补偿" maxlength="255" clearable></el-input>
			</el-form-item>
		</el-form>
		<template #footer>
			<el-button @click="grant.visible=false">取 消</el-button>
			<el-button type="primary" :loading="grant.saving" @click="submitGrant">确 定</el-button>
		</template>
	</el-dialog>

	<!-- 额度流水 -->
	<el-drawer v-model="logs.visible" :title="`额度流水 - ${logs.account}`" size="620px" destroy-on-close append-to-body>
		<el-table :data="logs.data" v-loading="logs.loading" size="small" stripe>
			<el-table-column label="类型" prop="type_label" width="100"></el-table-column>
			<el-table-column label="变动" align="right" width="80">
				<template #default="scope">
					<span :style="{color: scope.row.change >= 0 ? '#67C23A' : '#F56C6C', fontWeight: 600}">
						{{scope.row.change > 0 ? '+' : ''}}{{scope.row.change}}
					</span>
				</template>
			</el-table-column>
			<el-table-column label="变动后余额" prop="balance" align="right" width="100"></el-table-column>
			<el-table-column label="备注" prop="remark" min-width="140" show-overflow-tooltip>
				<template #default="scope">{{scope.row.remark || '-'}}</template>
			</el-table-column>
			<el-table-column label="时间" prop="create_time" width="160"></el-table-column>
		</el-table>
		<el-pagination
			v-if="logs.total > logs.pageSize"
			style="margin-top: 12px; justify-content: center"
			layout="prev, pager, next"
			:total="logs.total"
			:page-size="logs.pageSize"
			v-model:current-page="logs.pageNum"
			@current-change="loadLogs"
		></el-pagination>
	</el-drawer>
</template>

<script>
	export default {
		name: 'creditUser',
		data() {
			return {
				apiObj: this.$API.credit.user.list,
				search: {keyword: null},
				grant: {visible: false, saving: false, row: null, amount: 10, remark: ""},
				logs: {visible: false, loading: false, data: [], total: 0, pageNum: 1, pageSize: 10, userId: null, account: ""}
			}
		},
		methods: {
			upsearch(){
				this.$refs.table.upData(this.search)
			},
			handleGrant(row){
				this.grant.row = row
				this.grant.amount = 10
				this.grant.remark = ""
				this.grant.visible = true
			},
			async submitGrant(){
				this.grant.saving = true
				var res = await this.$API.credit.user.grant.get({
					user_id: this.grant.row.id,
					amount: this.grant.amount,
					remark: this.grant.remark || ""
				})
				this.grant.saving = false
				if(res.code == 1){
					this.$message.success("赠送成功")
					this.grant.visible = false
					this.$refs.table.refresh()
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			handleLogs(row){
				this.logs.userId = row.id
				this.logs.account = row.account
				this.logs.pageNum = 1
				this.logs.visible = true
				this.loadLogs()
			},
			async loadLogs(){
				this.logs.loading = true
				var res = await this.$API.credit.user.logs.get({
					user_id: this.logs.userId,
					pageNum: this.logs.pageNum,
					pageSize: this.logs.pageSize
				})
				this.logs.loading = false
				if(res.code == 1){
					this.logs.data = res.data || []
					this.logs.total = res.total || 0
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			}
		}
	}
</script>

<style scoped>
</style>
