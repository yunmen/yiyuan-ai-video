<template>
	<el-container>
		<el-header>
			<div class="left-panel"></div>
			<div class="right-panel">
				<div class="right-panel-search">
					<el-input v-model="search.keyword" placeholder="订单号/商品名" clearable style="width: 180px"></el-input>
					<el-select v-model="search.status" placeholder="订单状态" clearable style="width: 120px; margin-left: 10px">
						<el-option v-for="(item, value) in statusMap" :key="value" :label="item.label" :value="Number(value)"></el-option>
					</el-select>
					<el-button type="primary" icon="el-icon-search" style="margin-left: 10px" @click="upsearch"></el-button>
				</div>
			</div>
		</el-header>
		<el-main class="nopadding">
			<scTable ref="table" :apiObj="apiObj" stripe remoteSort remoteFilter>
				<el-table-column label="#" type="index" width="50"></el-table-column>
				<el-table-column label="订单号" prop="order_no" min-width="180" show-overflow-tooltip></el-table-column>
				<el-table-column label="商品名称" prop="package_name" min-width="140" show-overflow-tooltip></el-table-column>
				<el-table-column label="金额(元)" prop="amount" align="right" width="100"></el-table-column>
				<el-table-column label="网关" prop="gateway" align="center" width="90"></el-table-column>
				<el-table-column label="状态" prop="status" align="center" width="100">
					<template #default="scope">
						<el-tag :type="statusMap[scope.row.status]?.type || 'info'" size="small">{{statusMap[scope.row.status]?.label || scope.row.status}}</el-tag>
					</template>
				</el-table-column>
				<el-table-column label="用户Id" prop="user_id" align="center" width="90"></el-table-column>
				<el-table-column label="支付时间" prop="pay_time" align="center" width="170">
					<template #default="scope">{{scope.row.pay_time || '-'}}</template>
				</el-table-column>
				<el-table-column label="备注" prop="remark" min-width="120" show-overflow-tooltip>
					<template #default="scope">{{scope.row.remark || '-'}}</template>
				</el-table-column>
				<el-table-column label="创建时间" prop="create_time" align="center" width="170"></el-table-column>
				<el-table-column label="操作" fixed="right" align="right" width="150">
					<template #default="scope">
						<el-button-group>
							<el-button v-if="[2,3].includes(scope.row.status)" text type="danger" size="small" @click="handleRefund(scope.row)">退款</el-button>
							<el-button v-if="scope.row.status==5" text type="primary" size="small" @click="handleRefundQuery(scope.row)">退款查询</el-button>
						</el-button-group>
					</template>
				</el-table-column>
			</scTable>
		</el-main>
	</el-container>
</template>

<script>
	export default {
		name: 'paymentOrder',
		data() {
			return {
				apiObj: this.$API.payment.order.list,
				search: {
					keyword: null,
					status: null
				},
				//与后端 OrderStatusEnum 一致:1待支付 2已支付 3已交付 4已取消 5退款中 6已退款
				statusMap: {
					1: {label: '待支付', type: 'warning'},
					2: {label: '已支付', type: 'success'},
					3: {label: '已交付', type: 'success'},
					4: {label: '已取消', type: 'info'},
					5: {label: '退款中', type: 'danger'},
					6: {label: '已退款', type: 'info'}
				}
			}
		},
		methods: {
			//发起退款
			async handleRefund(row){
				try {
					var {value} = await this.$prompt('请输入退款原因(可留空)', `退款 - ${row.order_no}`, {
						confirmButtonText: '确认退款',
						cancelButtonText: '取消',
						inputPlaceholder: '退款原因'
					})
				} catch (e) {
					return
				}
				var res = await this.$API.payment.order.refund.get({order_no: row.order_no, reason: value || null});
				if(res.code == 1){
					this.$message.success("退款申请已提交")
					this.$refs.table.refresh()
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			//退款查询(回调丢失兜底)
			async handleRefundQuery(row){
				var res = await this.$API.payment.order.refundQuery.get({order_no: row.order_no});
				if(res.code == 1){
					this.$message.success(`退款状态已同步:${this.statusMap[res.data.status]?.label || res.data.status}`)
					this.$refs.table.refresh()
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
</style>
