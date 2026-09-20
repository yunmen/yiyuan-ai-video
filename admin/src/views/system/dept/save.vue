<template>
	<el-dialog :title="titleMap[mode]" v-model="visible" :width="500" destroy-on-close @closed="$emit('closed')">
		<el-form :model="form" :rules="rules" :disabled="mode=='show'" ref="dialogForm" label-width="100px">
			<el-form-item label="上级部门" prop="parent_id">
				<el-cascader v-model="form.parent_id" :options="groups" :props="groupsProps" :show-all-levels="false" clearable style="width: 100%;"></el-cascader>
			</el-form-item>
			<el-form-item label="部门名称" prop="name">
				<el-input v-model="form.name" placeholder="请输入部门名称" clearable></el-input>
			</el-form-item>
			<el-form-item label="排序" prop="order">
				<el-input-number v-model="form.order" controls-position="right" :min="1" style="width: 100%;"></el-input-number>
			</el-form-item>
			<el-form-item label="说明" prop="desc">
				<el-input v-model="form.desc" clearable type="textarea"></el-input>
			</el-form-item>
		</el-form>
		<template #footer>
			<el-button @click="visible=false" >取 消</el-button>
			<el-button v-if="mode!='show'" type="primary" :loading="isSaveing" @click="submit()">保 存</el-button>
		</template>
	</el-dialog>
</template>

<script>
	export default {
		emits: ['success', 'closed'],
		data() {
			return {
				mode: "add",
				titleMap: {
					add: '新增',
					edit: '编辑',
					show: '查看'
				},
				visible: false,
				isSaveing: false,
				//表单数据
				form: {
					id:"",
					parent_id: 0,
					name: "",
					order: 1,
					desc: ""
				},
				//验证规则
				rules: {
					name: [
						{required: true, message: '请输入部门名称'}
					]
				},
				//所需数据选项
				groups: [],
				groupsProps: {
					value: "id",
					label: "name",
					emitPath: false,
					checkStrictly: true
				}
			}
		},
		mounted() {
			this.getGroup()
		},
		methods: {
			//显示
			open(mode='add'){
				this.mode = mode;
				this.visible = true;
				return this
			},
			//加载树数据
			async getGroup(){
				var res = await this.$API.system.dept.tree.get();
				this.groups = res.data;
			},
			//表单提交方法
			submit(){
				this.$refs.dialogForm.validate(async (valid) => {
					if (valid) {
						this.isSaveing = true;
						var res = null;
						if(this.mode=='add'){
							res = await this.$API.system.dept.create.get(this.form);
						}else{
							res = await this.$API.system.dept.update.get(this.form);
						}
						this.isSaveing = false;
						if(res.code == 1){
							this.$emit('success')
							this.visible = false;
							this.$message.success("操作成功")
						}
					}
				})
			},
			//表单注入数据
			setData(data){
				// this.form.id = data.id
				// this.form.name = data.name
				// this.form.order = data.order
				// this.form.parent_id = data.parent_id
				// this.form.desc = data.desc

				//可以和上面一样单个注入，也可以像下面一样直接合并进去
				Object.assign(this.form, data)
			}
		}
	}
</script>

<style>
</style>
