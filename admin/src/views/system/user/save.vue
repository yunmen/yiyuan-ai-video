<template>
	<el-dialog :title="titleMap[mode]" v-model="visible" :width="500" destroy-on-close @closed="$emit('closed')">
		<el-form :model="form" :rules="rules" :disabled="mode=='show'" ref="dialogForm" label-width="100px" label-position="left">
			<el-form-item label="头像" prop="avatar">
				<sc-upload v-model="form.avatar" title="上传头像"></sc-upload>
			</el-form-item>
			<template v-if="mode=='add'">
				<el-form-item label="登录账号" prop="account">
					<el-input v-model="form.account" placeholder="用于登录系统" clearable></el-input>
				</el-form-item>
			</template>
			<el-form-item label="所属部门" prop="dept">
				<el-cascader v-model="form.dept" :options="depts" :props="deptsProps" clearable style="width: 100%;"></el-cascader>
			</el-form-item>
			<el-form-item label="所属角色" prop="roles">
				<el-select v-model="form.roles" multiple filterable style="width: 100%">
					<el-option v-for="item, index in groups" :key="index" :label="item.label" :value="item.value"/>
				</el-select>
			</el-form-item>
			<el-form-item label="数据权限" prop="permission">
				<el-select v-model="form.permission" filterable style="width: 100%">
					<el-option label="全部可见" :value="1"/>
					<el-option label="仅自己可见" :value="2"/>
					<el-option label="所在部门可见" :value="3"/>
					<el-option label="所在部门及子部门可见" :value="4"/>
				</el-select>
			</el-form-item>
			<el-form-item label="姓名" prop="realname">
				<el-input v-model="form.realname" placeholder="请输入姓名" clearable></el-input>
			</el-form-item>
			<el-form-item label="昵称" prop="nickname">
				<el-input v-model="form.nickname" placeholder="请输入昵称" clearable></el-input>
			</el-form-item>
			<el-form-item label="电话" prop="phone">
				<el-input v-model="form.phone" placeholder="请输入电话" clearable></el-input>
			</el-form-item>
			<el-form-item label="邮箱" prop="email">
				<el-input v-model="form.email" placeholder="请输入邮箱" clearable></el-input>
			</el-form-item>
			<template v-if="mode=='add'">
				<el-form-item label="登录密码" prop="password">
					<el-input type="password" v-model="form.password" clearable show-password></el-input>
				</el-form-item>
				<el-form-item label="确认密码" prop="password2">
					<el-input type="password" v-model="form.password2" clearable show-password></el-input>
				</el-form-item>
			</template>
			
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
					add: '新增用户',
					edit: '编辑用户',
					show: '查看'
				},
				visible: false,
				isSaveing: false,
				//表单数据
				form: {
					id:"",
					password2:""
				},
				//验证规则
				rules: {
					avatar:[
						{message: '请上传头像'}
					],
					account: [
						{required: true, message: '请输入登录账号'}
					],
					realname: [
						{required: true, message: '请输入姓名'}
					],
					nickname: [
						{required: true, message: '请输入昵称'}
					],
					phone: [
						{required: true, message: '请输入电话'}
					],
					email: [
						{required: true, message: '请输入邮箱'}
					],
					password: [
						{required: true, message: '请输入登录密码'},
						{validator: (rule, value, callback) => {
							if (this.form.password2 !== '') {
								this.$refs.dialogForm.validateField('password2');
							}
							callback();
						}}
					],
					password2: [
						{required: true, message: '请再次输入密码'},
						{validator: (rule, value, callback) => {
							if (value !== this.form.password) {
								callback(new Error('两次输入密码不一致!'));
							}else{
								callback();
							}
						}}
					],
					permission: [
						{required: true, message: '请选择数据权限'}
					],
					dept: [
						{required: true, message: '请选择所属部门'}
					],
					roles: [
						{required: true, message: '请选择所属角色', trigger: 'change'}
					]
				},
				//所需数据选项
				groups: [],
				depts: [],
				deptsProps: {
					value: "id",
					label: "name",
					checkStrictly: true,
					emitPath: false
					
				}
			}
		},
		mounted() {
			this.getGroup()
			this.getDept()
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
				var res = await this.$API.system.role.all.get();
				this.groups = res.data;
			},
			async getDept(){
				var res = await this.$API.system.dept.tree.get();
				this.depts = res.data;
			},
			//表单提交方法
			submit(){
				this.$refs.dialogForm.validate(async (valid) => {
					if (valid) {
						this.isSaveing = true;
						var res = null;
						if(this.mode == 'add'){
						    res = await this.$API.system.user.create.get(this.form);
						}else{
							res = await this.$API.system.user.update.get(this.form);
						}
						this.isSaveing = false;
						if(res.code == 1){
							this.$emit('success', this.form, this.mode)
							this.visible = false;
							this.$message.success("操作成功")
						}
					}else{
						return false;
					}
				})
			},
			//表单注入数据
			setData(data){
				// this.form.id = data.id
				// this.form.userName = data.userName
				// this.form.avatar = data.avatar
				// this.form.name = data.name
				// this.form.group = data.group
				// this.form.dept = data.dept

				//可以和上面一样单个注入，也可以像下面一样直接合并进去
				Object.assign(this.form, data)
				this.form.roles = data.roles.map(dict=>dict.id)
				this.form.dept = data.dept.id
			}
		}
	}
</script>

<style>
</style>
