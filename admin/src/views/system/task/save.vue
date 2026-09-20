<!--
 * @Descripttion: 系统计划任务配置
 * @version: 1.2
 * @Author: sakuya
 * @Date: 2021年7月7日09:28:32
 * @LastEditors: sakuya
 * @LastEditTime: 2021年7月10日20:56:47
-->

<template>
	<el-dialog :title="titleMap[mode]" v-model="visible" :width="800" destroy-on-close @closed="$emit('closed')">
		<el-form :model="form" :rules="rules" :disabled="mode=='show'" ref="dialogForm" label-width="100px" label-position="right">
			<el-row :gutter="15">
				<el-col :span="12">
					<el-form-item label="任务名称" prop="name">
						<el-input v-model="form.name" placeholder="请输入任务名称" clearable></el-input>
					</el-form-item>
					<el-form-item label="位置参数" prop="args">
						<el-input v-model="form.args" placeholder="请输入位置参数" clearable></el-input>
					</el-form-item>
					<el-form-item label="存储器" prop="jobstore">
						<el-select v-model="form.jobstore" placeholder="请选择存储器" clearable style="width: 100%">
							<el-option key="default" label="默认执行器" value="default"/>
							<el-option key="memory" label="内存存储器" value="memory"/>
							<el-option key="redis" label="Redis存储器" value="redis"/>
						</el-select>
					</el-form-item>
					<el-form-item label="触发器" prop="trigger">
						<el-select v-model="form.trigger" placeholder="请选择触发器" clearable style="width: 100%">
							<el-option key="date" label="定时触发器" value="date"/>
							<el-option key="interval" label="间隔触发器" value="interval"/>
							<el-option key="cron" label="Cron触发器" value="cron"/>
						</el-select>
					</el-form-item>
					<el-form-item label="开始时间" prop="start_date" v-if="form.trigger != 'date'">
						<el-date-picker v-model="form.start_date" type="datetime" format="YYYY-MM-DD HH:mm:ss" value-format="YYYY-MM-DD HH:mm:ss" placeholder="请选择开始日期" clearable style="width: 100%;"/>
					</el-form-item>
				</el-col>
				<el-col :span="12">
					<el-form-item label="执行方法" prop="func">
						<el-input v-model="form.func" placeholder="请输入执行方法" clearable></el-input>
					</el-form-item>
					<el-form-item label="关键字参数" prop="kwargs">
						<el-input v-model="form.kwargs" placeholder="请输入关键字参数" clearable></el-input>
					</el-form-item>
					<el-form-item label="执行器" prop="executor">
						<el-select v-model="form.executor" placeholder="请选择执行器" clearable style="width: 100%">
							<el-option key="default" label="默认执行器" value="default"/>
							<el-option key="asyncio" label="异步执行器" value="asyncio"/>
							<el-option key="thread" label="线程执行器" value="thread"/>
							<el-option key="process" label="进行执行器" value="process"/>
						</el-select>
					</el-form-item>
					<el-form-item label="定时规则" prop="trigger_args" v-if="form.trigger != 'date'">
						<sc-cron v-model="form.trigger_args" placeholder="请输入定时规则" clearable :shortcuts="shortcuts"></sc-cron>
					</el-form-item>
					<el-form-item label="定时规则" prop="trigger_args" v-else>
						<el-date-picker v-model="form.trigger_args" type="datetime" format="YYYY-MM-DD HH:mm:ss" value-format="YYYY-MM-DD HH:mm:ss" placeholder="请选择运行时间" clearable style="width: 100%;"/>
					</el-form-item>
					<el-form-item label="结束时间" prop="end_date" v-if="form.trigger != 'date'">
						<el-date-picker v-model="form.end_date" type="datetime" format="YYYY-MM-DD HH:mm:ss" value-format="YYYY-MM-DD HH:mm:ss" placeholder="请选择结束日期" clearable style="width: 100%;"/>
					</el-form-item>
				</el-col>
			</el-row>
			<el-form-item label="任务说明" prop="desc">
				<el-input type="textarea" :rows="4" v-model="form.desc" placeholder="请输入任务说明" clearable></el-input>
			</el-form-item>

		</el-form>
		<template #footer>
			<el-button @click="visible=false" >取 消</el-button>
			<el-button type="primary" v-if="mode!='show'" :loading="isSaveing" @click="submit()">保 存</el-button>
		</template>
	</el-dialog>
</template>

<script>
	import scCron from '@/components/scCron/index.vue';
	
	export default {
		components: {
			scCron
		},
		emits: ['success', 'closed'],
		data() {
			return {
				mode: "add",
				titleMap: {
					add: '新增计划任务',
					edit: '编辑计划任务',
					show: '查看计划任务'
				},
				// form: {
				// 	id:"",
				// 	trigger: "",
				// 	executor: "default",
				// 	jobstore: "default",
				// },
				form: {
					jobstore: 'memory',
					args: '张三,23',
					create_time: '2025-09-10 14:23:42',
					trigger_args: '2025-09-24 00:00:00',
					kwargs: 'age=23&name=张三',
					trigger: 'date',
					update_time: '2025-09-10 14:23:42',
					func: 'app.tasks.demo.test_task',
					name: '测试',
					desc: 'ce',
					executor: 'asyncio'
				},
				rules: {
					name:[
						{required: true, message: '请填写任务名称'}
					],
					func:[
						{required: true, message: '请填写执行类'}
					],
					args:[
						{message: '请填写位置参数'}
					],
					kwargs:[
						{message: '请填写关键字参数'}
					],
					trigger:[
						{required: true, message: '请选择触发器'}
					],
					executor:[
						{required: true, message: '请选择执行器'}
					],
					jobstore:[
						{required: true, message: '请选择存储器'}
					],
					start_date:[
						{message: '请填写任务开始时间'}
					],
					end_date:[
						{message: '请填写任务结束时间'}
					],
					trigger_args:[
						{required: true, message: '请填写运行规则'}
					],
				},
				visible: false,
				isSaveing: false,
				shortcuts: [
					{
						text: "每天8点和12点 (自定义追加)",
						value: "0 0 8,12 * * ?"
					}
				]
			}
		},
		mounted() {

		},
		methods: {
			//显示
			open(mode='add'){
				this.mode = mode;
				this.visible = true;
				return this;
			},
			//表单提交方法
			submit(){
				this.$refs.dialogForm.validate(async (valid) => {
					if (valid) {
						this.isSaveing = true;
						var res = null;
						if(this.mode=='add'){
							res = await this.$API.system.task.create.get(this.form);
						}else{
							res = await this.$API.system.task.update.get(this.form);
						}
						this.isSaveing = false;
						if(res.code == 1){
							this.$emit('success', res.data, this.mode)
							this.visible = false;
							this.$message.success("操作成功")
						}
					}
				})
			},
			//表单注入数据
			setData(data){
				Object.assign(this.form, data)
			}
		}
	}
</script>

<style>
</style>
