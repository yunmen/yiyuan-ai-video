<template>
	<el-container>
		<el-aside width="200px" v-loading="showGrouploading">
			<el-container>
				<el-header>
					<el-input placeholder="输入关键字进行过滤" v-model="groupFilterText" clearable></el-input>
				</el-header>
				<el-main class="nopadding">
					<el-tree ref="group" class="menu" node-key="id" :data="group" :props="deptProps" :current-node-key="''" :highlight-current="true" :expand-on-click-node="false" :filter-node-method="groupFilterNode" @node-click="groupClick"></el-tree>
				</el-main>
			</el-container>
		</el-aside>
		<el-container>
				<el-header>
					<div class="left-panel">
						<el-button type="primary" icon="el-icon-plus" @click="add"></el-button>
					</div>
					<div class="right-panel">
						<div class="right-panel-search">
							<el-input v-model="search.account" placeholder="登录账号" clearable></el-input>
							<el-input v-model="search.realName" placeholder="姓名" clearable></el-input>
							<el-button type="primary" icon="el-icon-search" @click="upsearch"></el-button>
						</div>
					</div>
				</el-header>
				<el-main class="nopadding">
					<scTable ref="table" :apiObj="apiObj"  stripe remoteSort remoteFilter>
						<el-table-column label="#" type="index" ></el-table-column>
						<el-table-column label="头像" align="center">
							<template #default="scope">
								<el-avatar :src="scope.row.avatar" size="small"></el-avatar>
							</template>
						</el-table-column>
						<el-table-column label="账号" prop="account" align="center"></el-table-column>
						<el-table-column label="姓名" prop="realname" align="center"></el-table-column>
						<el-table-column label="昵称" prop="nickname" align="center"></el-table-column>
						<el-table-column label="电话" prop="phone" align="center"></el-table-column>
						<el-table-column label="邮箱" prop="email" align="center"></el-table-column>
						<el-table-column label="所属角色" align="center">
							<template #default="scope">
								<el-tag v-for="item,index in scope.row.roles" :key="index" size="small">{{item.name}}</el-tag>
							</template>
						</el-table-column>
						<el-table-column label="状态" prop="active" align="center">
							<template #default="scope">
								<el-switch v-model="scope.row.active" @change="changeSwitch($event, scope.row)" :loading="scope.row.$switch_status" :active-value="true" :inactive-value="false"></el-switch>
							</template>
						</el-table-column>
						<el-table-column label="最后登录IP" prop="last_login_ip" align="center" show-overflow-tooltip></el-table-column>
						<el-table-column label="最后登录时间" prop="last_login_time" align="center" show-overflow-tooltip></el-table-column>
						<el-table-column label="操作" fixed="right" align="right" width="240">
							<template #default="scope">
								<el-button-group>
									<el-button text type="primary" size="small" @click="table_show(scope.row, scope.$index)">查看</el-button>
									<el-button text type="primary" size="small" @click="table_edit(scope.row, scope.$index)">编辑</el-button>
									<el-popconfirm title="确定重置密码吗？" @confirm="table_reset(scope.row)">
										<template #reference>
											<el-button text type="primary" size="small">重置密码</el-button>
										</template>
									</el-popconfirm>
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
	</el-container>

	<save-dialog v-if="dialog.save" ref="saveDialog" @success="handleSuccess" @closed="dialog.save=false"></save-dialog>

</template>

<script>
	import saveDialog from './save.vue'

	export default {
		name: 'system.user',
		components: {
			saveDialog
		},
		data() {
			return {
				dialog: {
					save: false
				},
				showGrouploading: false,
				groupFilterText: '',
				group: [],
				deptProps:{
					label: (data)=>{
						return data.name
					}
				},
				apiObj: this.$API.system.user.list,
				search: {}
			}
		},
		watch: {
			groupFilterText(val) {
				this.$refs.group.filter(val);
			}
		},
		mounted() {
			this.getGroup()
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
			async table_del(row, index){
				var reqData = {id: row.id}
				var res = await this.$API.system.user.delete.get(reqData);
				if(res.code == 1){
					//这里选择刷新整个表格 OR 插入/编辑现有表格数据
					this.$refs.table.tableData.splice(index, 1);
					this.$message.success("删除成功")
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			//重置密码
			async table_reset(row){
				var reqData = {id: row.id}
				var res = await this.$API.system.user.repwd.get(reqData);
				if(res.code == 1){
					//这里选择刷新整个表格 OR 插入/编辑现有表格数据
					this.$message.success(res.message)
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			//加载树数据
			async getGroup(){
				this.showGrouploading = true;
				var res = await this.$API.system.dept.tree.get();
				this.showGrouploading = false;
				var allNode ={id: null, name: '所有'}
				res.data.unshift(allNode);
				this.group = res.data;
			},
			//树过滤
			groupFilterNode(value, data){
				if (!value) return true;
				return data.name.indexOf(value) !== -1;
			},
			//树点击事件
			groupClick(data){
				var params = {
					dept_id: data.id
				}
				this.$refs.table.reload(params)
			},
			//表格内开关
			async changeSwitch(val, row){
				row.$switch_status = true;
				let data = { id: row.id, active: row.active }
				var res = await this.$API.system.user.active.get(data);
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
			handleSuccess(data, mode){
				if(mode=='add'){
					data.id = new Date().getTime()
					this.$refs.table.tableData.unshift(data)
				}else if(mode=='edit'){
					this.$refs.table.tableData.filter(item => item.id===data.id ).forEach(item => {
						Object.assign(item, data)
					})
				}
			}
		}
	}
</script>

<style>
</style>
