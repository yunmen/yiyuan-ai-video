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
			<el-form-item label="形象图" prop="image">
				<sc-upload v-model="form.image" title="上传口播形象图" :disabled="mode=='show'" :compress="0.8"></sc-upload>
				<div class="tip">口型驱动的底图,建议正方形半身照;留空则使用头像</div>
			</el-form-item>
			<el-form-item label="派生视图" prop="pose_variants">
				<div class="pose-list">
					<div class="pose-item" v-for="(item, index) in form.pose_variants" :key="index">
						<el-input v-model="item.name" placeholder="姿势名,如 挥手" maxlength="20" style="width: 160px"></el-input>
						<el-input v-model="item.image" placeholder="派生形象图URL" clearable style="flex: 1"></el-input>
						<el-upload :http-request="(opt) => uploadPose(opt, item)" :show-file-list="false" accept="image/*" :disabled="mode=='show'">
							<el-button size="small">上传</el-button>
						</el-upload>
						<el-button size="small" type="danger" plain @click="removePose(index)" :disabled="mode=='show'">删除</el-button>
					</div>
					<el-button size="small" @click="addPose" :disabled="mode=='show'">+ 添加派生视图</el-button>
					<div class="tip">同一形象的不同姿势/景别;生成时以「主视图」为参考形象,避免换个姿势就变脸</div>
				</div>
			</el-form-item>
			<el-form-item label="音色" prop="voice">
				<el-input v-model="form.voice" placeholder="TTS 音色标识,如 alloy;留空用网关默认音色" maxlength="100" clearable></el-input>
			</el-form-item>
			<el-form-item label="声纹样本" prop="voice_reference">
				<div class="audio-box">
					<audio v-if="form.voice_reference" :src="form.voice_reference" controls style="width: 260px"></audio>
					<el-upload v-if="mode!='show'" :http-request="uploadVoice" :show-file-list="false" accept="audio/*">
						<el-button :loading="uploadingVoice">{{form.voice_reference ? '重新上传' : '上传声纹'}}</el-button>
					</el-upload>
					<el-input v-model="form.voice_reference" placeholder="或填写声纹样本音频URL(可复用声纹,优先级高于音色)" clearable style="margin-top: 8px"></el-input>
				</div>
				<div class="tip">一段约 5s 的试音音频;绑定后同一数字人跨任务/跨镜头复用同一声音(出镜表演与旁白同源)</div>
			</el-form-item>
			<el-form-item label="生成模型" prop="model">
				<el-input v-model="form.model" placeholder="留空使用业务配置 gen.digital_model" maxlength="100" clearable></el-input>
			</el-form-item>
			<el-form-item label="默认口播" prop="default_text">
				<el-input v-model="form.default_text" type="textarea" :rows="3" placeholder="用户未填写口播文案时使用的默认台词"></el-input>
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
	import { uploadFile } from "@/api/model/common"

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
				uploadingVoice: false,
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
					image: "",
					voice: "",
					voice_reference: "",
					model: "",
					default_text: "",
					pose_variants: [],
					sort: 0,
					// 默认不上架:新建的公开形象需运营在「是否上架」显式开启后才进入公开选人列表
					active: false
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
				this.form.pose_variants = (data.pose_variants || []).map(item => ({name: item.name || "", image: item.image || ""}))
			},
			//派生视图:新增一行
			addPose(){
				this.form.pose_variants.push({name: "", image: ""})
			},
			//派生视图:删除一行
			removePose(index){
				this.form.pose_variants.splice(index, 1)
			},
			//派生视图:上传图片后回填该行 URL
			async uploadPose({file}, item){
				try {
					item.image = await uploadFile(file)
					this.$message.success("上传成功")
				} catch (e) {
					this.$alert(e.message || "上传失败", "提示", {type: 'error'})
				}
			},
			//预览视频上传(直传对象存储,避开跨境中转)
			async uploadVideo({file}){
				this.uploading = true
				try {
					this.form.preview_video = await uploadFile(file)
					this.$message.success("上传成功")
				} catch (e) {
					this.$alert(e.message || "上传失败", "提示", {type: 'error'})
				} finally {
					this.uploading = false
				}
			},
			// 声纹样本上传(直传对象存储,避开跨境中转)
			async uploadVoice({file}){
				this.uploadingVoice = true
				try {
					this.form.voice_reference = await uploadFile(file)
					this.$message.success("上传成功")
				} catch (e) {
					this.$alert(e.message || "上传失败", "提示", {type: 'error'})
				} finally {
					this.uploadingVoice = false
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
	.pose-list {
		width: 100%;
	}
	.pose-item {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 8px;
	}
	.tip {
		font-size: 12px;
		color: var(--el-text-color-secondary);
		line-height: 1.5;
		margin-top: 4px;
	}
</style>
