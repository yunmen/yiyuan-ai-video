<template>
	<el-dialog :title="titleMap[mode]" v-model="visible" :width="480" destroy-on-close @closed="$emit('closed')">
		<el-form :model="form" :rules="rules" :disabled="mode=='show'" ref="dialogForm" label-width="90px" label-position="left">
			<el-form-item label="分类名称" prop="name">
				<el-input v-model="form.name" placeholder="如:美食探店" maxlength="50" clearable></el-input>
			</el-form-item>
			<el-form-item label="分类图标" prop="cover">
				<sc-upload v-model="form.cover" title="上传图标" :disabled="mode=='show'"></sc-upload>
			</el-form-item>
			<el-form-item label="排序" prop="sort">
				<el-input-number v-model="form.sort" :min="0" :max="9999"></el-input-number>
				<span style="margin-left:10px;color:#999;font-size:12px">倒序,越大越靠前</span>
			</el-form-item>
			<el-form-item label="是否启用" prop="active">
				<el-switch v-model="form.active" :active-value="true" :inactive-value="false"></el-switch>
			</el-form-item>
			<el-form-item label="备注" prop="remark">
				<el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填" maxlength="255"></el-input>
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
		name: 'video-category-save',
		emits: ['success', 'closed'],
		data() {
			return {
				mode: "add",
				titleMap: {add: '新增分类', edit: '编辑分类', show: '查看分类'},
				visible: false,
				isSaveing: false,
				form: {
					id: "",
					name: "",
					cover: "",
					sort: 0,
					active: true,
					remark: ""
				},
				rules: {
					name: [{required: true, message: '请输入分类名称'}]
				}
			}
		},
		methods: {
			open(mode='add'){
				this.mode = mode
				this.visible = true
				return this
			},
			setData(data){
				this.form = {
					id: data.id || "",
					name: data.name || "",
					cover: data.cover || "",
					sort: data.sort || 0,
					active: data.active !== false,
					remark: data.remark || ""
				}
			},
			submit(){
				this.$refs.dialogForm.validate(async (valid) => {
					if (!valid) return false
					this.isSaveing = true
					var payload = {...this.form}
					if(this.mode === 'add'){
						delete payload.id
					}
					var res = await this.$API.video.category.save.get(payload)
					this.isSaveing = false
					if(res.code == 1){
						this.$message.success("保存成功")
						this.$emit('success', this.form, this.mode)
						this.visible = false
					}else{
						this.$alert(res.message, "提示", {type: 'error'})
					}
				})
			}
		}
	}
</script>

<style scoped>
</style>
