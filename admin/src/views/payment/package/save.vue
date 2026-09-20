<template>
	<el-dialog :title="titleMap[mode]" v-model="visible" :width="520" destroy-on-close @closed="$emit('closed')">
		<el-form :model="form" :rules="rules" :disabled="mode=='show'" ref="dialogForm" label-width="100px" label-position="left">
			<el-form-item label="套餐名称" prop="name">
				<el-input v-model="form.name" placeholder="如:进阶包" maxlength="50" clearable></el-input>
			</el-form-item>
			<el-form-item label="副标题" prop="sub_title">
				<el-input v-model="form.sub_title" placeholder="如:高频制作首选" maxlength="100" clearable></el-input>
			</el-form-item>
			<el-form-item label="到账额度" prop="credits">
				<el-input-number v-model="form.credits" :min="1" :max="99999"></el-input-number>
				<span style="margin-left:10px;color:#999;font-size:12px">次</span>
			</el-form-item>
			<el-form-item label="售价" prop="price">
				<el-input-number v-model="form.price" :min="0" :max="99999" :precision="2" :step="1"></el-input-number>
				<span style="margin-left:10px;color:#999;font-size:12px">元</span>
			</el-form-item>
			<el-form-item label="角标文案" prop="tag">
				<el-input v-model="form.tag" placeholder="如:推荐 / 热卖(留空不展示)" maxlength="20" clearable></el-input>
			</el-form-item>
			<el-form-item label="排序" prop="sort">
				<el-input-number v-model="form.sort" :min="0" :max="9999"></el-input-number>
				<span style="margin-left:10px;color:#999;font-size:12px">倒序,越大越靠前</span>
			</el-form-item>
			<el-form-item label="是否上架" prop="active">
				<el-switch v-model="form.active" :active-value="true" :inactive-value="false"></el-switch>
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
		name: 'payment-package-save',
		emits: ['success', 'closed'],
		data() {
			return {
				mode: "add",
				titleMap: {
					add: '新增套餐',
					edit: '编辑套餐',
					show: '查看套餐'
				},
				visible: false,
				isSaveing: false,
				form: {
					id: "",
					name: "",
					sub_title: "",
					credits: 10,
					price: 9.9,
					tag: "",
					sort: 0,
					active: true
				},
				rules: {
					name: [{required: true, message: '请输入套餐名称'}],
					credits: [{required: true, message: '请输入到账额度'}],
					price: [{required: true, message: '请输入售价'}]
				}
			}
		},
		methods: {
			open(mode='add'){
				this.mode = mode;
				this.visible = true;
				return this
			},
			setData(data){
				this.form = {
					id: data.id || "",
					name: data.name || "",
					sub_title: data.sub_title || "",
					credits: data.credits || 1,
					price: Number(data.price || 0),
					tag: data.tag || "",
					sort: data.sort || 0,
					active: data.active !== false
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
					var res = await this.$API.payment.package.save.get(payload)
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
