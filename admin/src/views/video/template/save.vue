<template>
	<el-dialog :title="titleMap[mode]" v-model="visible" :width="640" destroy-on-close @closed="$emit('closed')">
		<el-form :model="form" :rules="rules" :disabled="mode=='show'" ref="dialogForm" label-width="100px" label-position="left">
			<el-form-item label="模板标题" prop="title">
				<el-input v-model="form.title" placeholder="请输入模板标题" maxlength="100" clearable></el-input>
			</el-form-item>
			<el-form-item label="分类" prop="category">
				<el-select v-model="form.category" filterable allow-create default-first-option placeholder="选择或输入分类(在「模板分类」中维护)" style="width: 100%">
					<el-option v-for="item in categoryOptions" :key="item" :label="item" :value="item"></el-option>
				</el-select>
			</el-form-item>
			<el-form-item label="封面图" prop="cover">
				<sc-upload v-model="form.cover" title="上传封面" :disabled="mode=='show'" cropper :aspectRatio="9/16" :compress="0.8"></sc-upload>
			</el-form-item>
			<el-form-item label="示例视频" prop="video_url">
				<div class="video-box">
					<video v-if="form.video_url" :src="form.video_url" controls style="width: 260px; border-radius: 4px"></video>
					<el-upload v-if="mode!='show'" :http-request="uploadVideo" :show-file-list="false" accept="video/mp4,video/webm,video/quicktime">
						<el-button :loading="uploadingVideo">{{form.video_url ? '重新上传' : '上传视频'}}</el-button>
					</el-upload>
					<el-input v-model="form.video_url" placeholder="或直接填写视频URL" clearable style="margin-top: 8px"></el-input>
				</div>
			</el-form-item>
			<el-form-item label="示例图" prop="example_images">
				<div class="video-box">
					<el-upload list-type="picture-card" :file-list="exampleFileList" :http-request="uploadExample" :on-remove="removeExample" accept="image/*" :disabled="mode=='show'">
						<el-icon><el-icon-plus /></el-icon>
					</el-upload>
				</div>
			</el-form-item>
			<el-form-item label="标签" prop="tags">
				<el-select v-model="form.tags" multiple filterable allow-create default-first-option placeholder="输入后回车创建标签" style="width: 100%"></el-select>
			</el-form-item>
			<el-form-item label="模板描述" prop="desc">
				<el-input v-model="form.desc" type="textarea" :rows="3" placeholder="请输入模板描述(同时作为 AI 生成 prompt)"></el-input>
			</el-form-item>
			<el-form-item label="默认文案">
				<div class="text-box">
					<el-input v-model="form.default_text.title" placeholder="大标题(用户进入制作页自动带入)" maxlength="30" clearable></el-input>
					<el-input v-model="form.default_text.subtitle" placeholder="副标题" maxlength="40" clearable style="margin-top: 8px"></el-input>
					<el-input v-model="form.default_text.script" type="textarea" :rows="3" placeholder="口播文案" style="margin-top: 8px"></el-input>
					<div class="text-tip">用户进入「替换素材」页时自动预填,可自行修改</div>
				</div>
			</el-form-item>
			<el-form-item label="视频时长" prop="duration">
				<el-input-number v-model="form.duration" :min="1" :max="600"></el-input-number>
				<span style="margin-left:10px;color:#999;font-size:12px">单位:秒</span>
			</el-form-item>
			<el-form-item label="热度值" prop="hot">
				<el-input-number v-model="form.hot" :min="0" :max="999999"></el-input-number>
			</el-form-item>
			<el-form-item label="排序" prop="sort">
				<el-input-number v-model="form.sort" :min="0" :max="9999"></el-input-number>
			</el-form-item>
			<el-form-item label="首页推荐" prop="recommend">
				<el-switch v-model="form.recommend" :active-value="true" :inactive-value="false"></el-switch>
				<el-input-number v-if="form.recommend" v-model="form.recommend_sort" :min="0" :max="9999" style="margin-left: 16px"></el-input-number>
				<span v-if="form.recommend" style="margin-left:8px;color:#999;font-size:12px">推荐位排序(倒序)</span>
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
		name: 'video-template-save',
		emits: ['success', 'closed'],
		data() {
			return {
				mode: "add",
				titleMap: {
					add: '新增模板',
					edit: '编辑模板',
					show: '查看模板'
				},
				visible: false,
				isSaveing: false,
				uploadingVideo: false,
				//分类下拉来自「模板分类」维护的数据(加载失败时回退默认项)
				categoryOptions: ['美食探店', '零售带货', '美妆个护', '健身运动', '教育培训', '家居生活', '门店宣传'],
				//表单数据
				form: {
					id: "",
					title: "",
					category: "",
					cover: "",
					video_url: "",
					duration: 10,
					hot: 0,
					use_count: 0,
					desc: "",
					tags: [],
					example_images: [],
					default_text: {title: "", subtitle: "", script: ""},
					recommend: false,
					recommend_sort: 0,
					sort: 0,
					active: true
				},
				//验证规则
				rules: {
					title: [
						{required: true, message: '请输入模板标题'}
					],
					category: [
						{required: true, message: '请选择或输入分类'}
					]
				}
			}
		},
		computed: {
			//示例图 el-upload 文件列表(与 form.example_images 双向同步)
			exampleFileList(){
				return (this.form.example_images || []).map((url, index) => ({name: `示例图${index + 1}`, url}))
			}
		},
		methods: {
			//显示
			open(mode='add'){
				this.mode = mode;
				this.visible = true;
				this.loadCategories()
				return this
			},
			//分类下拉:取自管理端「模板分类」
			async loadCategories(){
				try {
					var res = await this.$API.video.category.list.get({pageNum: 1, pageSize: 100})
					if(res.code == 1 && res.data && res.data.length){
						this.categoryOptions = res.data.map(item => item.name)
					}
				} catch (e) {
					//保持默认兜底分类
				}
			},
			//表单注入数据
			setData(data){
				Object.assign(this.form, data)
				this.form.tags = data.tags || []
				this.form.example_images = data.example_images || []
				this.form.default_text = Object.assign({title: "", subtitle: "", script: ""}, data.default_text || {})
				this.form.recommend = !!data.recommend
				this.form.recommend_sort = data.recommend_sort || 0
			},
			//示例视频上传(走管理端公共上传接口)
			async uploadVideo({file}){
				this.uploadingVideo = true
				try {
					var formData = new FormData()
					formData.append('file', file)
					var res = await this.$API.common.upload.post(formData)
					if(res.code == 1){
						this.form.video_url = res.data.url
						this.$message.success("上传成功")
					}else{
						this.$alert(res.message, "提示", {type: 'error'})
					}
				} finally {
					this.uploadingVideo = false
				}
			},
			//示例图上传
			async uploadExample({file}){
				var formData = new FormData()
				formData.append('file', file)
				var res = await this.$API.common.upload.post(formData)
				if(res.code == 1){
					this.form.example_images.push(res.data.url)
				}else{
					this.$alert(res.message, "提示", {type: 'error'})
				}
			},
			//示例图移除
			removeExample(file){
				var index = this.form.example_images.indexOf(file.url)
				if(index > -1){
					this.form.example_images.splice(index, 1)
				}
			},
			//表单提交方法
			submit(){
				this.$refs.dialogForm.validate(async (valid) => {
					if (valid) {
						this.isSaveing = true;
						var api = this.mode === 'add' ? this.$API.video.template.create : this.$API.video.template.update
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
	.text-box {
		width: 100%;
	}
	.text-tip {
		margin-top: 6px;
		font-size: 12px;
		color: #999;
	}
</style>
