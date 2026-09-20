<template>
	<el-dialog :title="titleMap[mode]" v-model="visible" :width="560" destroy-on-close @closed="$emit('closed')">
		<el-form :model="form" :rules="rules" :disabled="mode=='show'" ref="dialogForm" label-width="100px">
			<el-form-item label="配置键" prop="key">
				<el-input v-model="form.key" :disabled="mode!='add'" placeholder="如 gen.video_model_r2v" clearable></el-input>
			</el-form-item>
			<el-form-item label="配置值" prop="value">
				<el-input v-model="form.value" type="textarea" :rows="3" placeholder="请输入配置值" clearable></el-input>
			</el-form-item>
			<el-form-item label="分组" prop="group">
				<el-input v-model="form.group" placeholder="默认 gen" clearable></el-input>
			</el-form-item>
			<el-form-item label="说明" prop="remark">
				<el-input v-model="form.remark" placeholder="请输入配置说明" clearable></el-input>
			</el-form-item>
			<el-form-item label="允许公开" prop="is_public">
				<el-switch v-model="form.is_public" :active-value="true" :inactive-value="false"></el-switch>
				<span style="margin-left:10px;color:#999;font-size:12px">公开配置无需登录即可读取(供用户端/worker 使用)</span>
			</el-form-item>
		</el-form>
		<template #footer>
			<el-button @click="visible=false">取 消</el-button>
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
					key: "",
					value: "",
					group: "gen",
					remark: "",
					is_public: true
				},
				//验证规则
				rules: {
					key: [
						{required: true, message: '请输入配置键'}
					]
				}
			}
		},
		methods: {
			//显示
			open(mode='add'){
				this.mode = mode;
				this.visible = true;
				return this;
			},
			//表单注入数据
			setData(data){
				Object.assign(this.form, data)
			},
			//表单提交
			async submit(){
				var valid = await this.$refs.dialogForm.validate().catch(() => false);
				if(!valid) return;

				this.isSaveing = true;
				var res = await this.$API.system.config.upsert.get(this.form);
				this.isSaveing = false;

				if(res.code == 1){
					this.$emit('success', res.data, this.mode)
					this.visible = false;
					this.$message.success("操作成功")
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			}
		}
	}
</script>

<style>
</style>
