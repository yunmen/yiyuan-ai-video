<template>
	<el-dialog :title="titleMap[mode]" v-model="visible" :width="600" destroy-on-close @closed="$emit('closed')">
		<el-form :model="form" :rules="rules" :disabled="mode=='show'" ref="dialogForm" label-width="100px" label-position="left">
			<el-form-item label="名称" prop="name">
				<el-input v-model="form.name" placeholder="请输入数字人名称" maxlength="50" clearable></el-input>
			</el-form-item>
			<el-form-item label="头像" prop="avatar">
				<sc-upload v-model="form.avatar" title="上传头像" :disabled="mode=='show'" cropper :aspectRatio="1" :compress="0.8"></sc-upload>
			</el-form-item>
			<el-form-item label="性别" prop="gender">
				<el-radio-group v-model="form.gender">
					<el-radio value="女">女</el-radio>
					<el-radio value="男">男</el-radio>
				</el-radio-group>
			</el-form-item>
			<el-form-item label="风格" prop="style">
				<el-input v-model="form.style" placeholder="如:知性主播、活力带货" maxlength="50" clearable></el-input>
			</el-form-item>
			<el-form-item label="标签" prop="tags">
				<el-select v-model="form.tags" multiple filterable allow-create default-first-option placeholder="输入后回车创建标签" style="width: 100%"></el-select>
			</el-form-item>
			<el-form-item label="简介" prop="desc">
				<el-input v-model="form.desc" type="textarea" :rows="3" placeholder="请输入简介"></el-input>
			</el-form-item>
			<el-form-item label="预览视频" prop="preview_video">
				<div class="video-box">
					<video v-if="form.preview_video" :src="form.preview_video" controls style="width: 260px; border-radius: 4px"></video>
					<el-upload v-if="mode!='show'" :http-request="uploadVideo" :show-file-list="false" accept="video/mp4,video/webm,video/quicktime">
						<el-button :loading="uploading">{{form.preview_video ? '重新上传' : '上传视频'}}</el-button>
					</el-upload>
					<el-input v-model="form.preview_video" placeholder="或直接填写视频URL" clearable style="margin-top: 8px"></el-input>
				</div>
			</el-form-item>
			<el-form-item label="排序" prop="sort">
				<el-input-number v-model="form.sort" :min="0" :max="9999"></el-input-number>
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
		name: 'digital-save',
		emits: ['success', 'closed'],
		data() {
			return {
				mode: "add",
				titleMap: {
					add: '新增数字人',
					edit: '编辑数字人',
					show: '查看数字人'
				},
				visible: false,
				isSaveing: false,
				uploading: false,
				//表单数据
				form: {
					id: "",
					name: "",
					avatar: "",
					gender: "女",
					style: "",
					desc: "",
					tags: [],
					preview_video: "",
					sort: 0,
					active: true
				},
				//验证规则
				rules: {
					name: [
						{required: true, message: '请输入数字人名称'}
					]
				}
			}
		},
		methods: {
			//显示
			open(mode='add'){
				this.mode = mode;
				this.visible = true;
				return this
			},
			//表单注入数据
			setData(data){
				Object.assign(this.form, data)
			},
			//预览视频上传(走管理端公共上传接口)
			async uploadVideo({file}){
				this.uploading = true
				try {
					var formData = new FormData()
					formData.append('file', file)
					var res = await this.$API.common.upload.post(formData)
					if(res.code == 1){
						this.form.preview_video = res.data.url
						this.$message.success("上传成功")
					}else{
						this.$alert(res.message, "提示", {type: 'error'})
					}
				} finally {
					this.uploading = false
				}
			},
			//表单提交方法
			submit(){
				this.$refs.dialogForm.validate(async (valid) => {
					if (valid) {
						this.isSaveing = true;
						var api = this.mode === 'add' ? this.$API.digital.create : this.$API.digital.update
						var res = await api.get(this.form);
						this.isSaveing = false;
						if(res.code == 1){
							this.$message.success((this.mode === 'add' ? '新增' : '编辑') + '成功')
							this.$emit('success', this.form, this.mode)
							this.visible = false;
						}else{
							this.$alert(res.message, "提示", {type: 'error'})
						}
					}else{
						return false;
					}
				})
			}
		}
	}
</script>

<style scoped>
	.video-box {
		width: 100%;
	}
	.video-box video {
		display: block;
		margin-bottom: 8px;
	}
</style>
