<template>
    <el-drawer v-model="visible" direction="rtl" size="800" destroy-on-close @closed="$emit('closed')">
		<template #header>
			<h4>日志详情</h4>
		</template>
		<div class="content">
			<el-descriptions :column="1" border size="small">
				<el-descriptions-item label="请求编号">{{info.request_id}}</el-descriptions-item>
				<el-descriptions-item label="请求地址">{{info.url}}</el-descriptions-item>
				<el-descriptions-item label="请求名称">{{info.summary}}</el-descriptions-item>
				<el-descriptions-item label="请求方法">{{info.method}}</el-descriptions-item>
				<el-descriptions-item label="请求来源">{{info.client_ip}}</el-descriptions-item>
				<el-descriptions-item label="响应状态">{{info.status_code}}</el-descriptions-item>
				<el-descriptions-item label="响应时间">{{info.process_time}}</el-descriptions-item>
				<el-descriptions-item label="客户端">{{info.client_type}}</el-descriptions-item>
				<el-descriptions-item label="操作人账号">{{info.operator_account}}</el-descriptions-item>
				<el-descriptions-item label="操作人昵称">{{info.operator_nickName}}</el-descriptions-item>
				<el-descriptions-item label="请求时间">{{info.create_time}}</el-descriptions-item>
			</el-descriptions>
			<el-collapse v-model="activeNames" style="margin-top: 20px;">
				<el-collapse-item title="请求数据" name="1">
					<div class="code">
						{{ info.payload ? info.payload : '暂无' }}
					</div>
				</el-collapse-item>
				<el-collapse-item title="响应结果" name="2">
					<div class="code">
						{{ info.result ? info.result : '暂无' }}
					</div>
				</el-collapse-item>
				<el-collapse-item title="请求头" name="3">
					<div class="code">
						{{ info.headers ? info.headers : '暂无' }}
					</div>
				</el-collapse-item>
				<el-collapse-item title="错误日志" name="4">
					<div class="code">
						{{ info.error_log ? info.error_log : '暂无' }}
					</div>
				</el-collapse-item>
			</el-collapse>
		</div>
  </el-drawer>
</template>

<script>
export default {
    data(){
        return {
            visible: false,
			activeNames: ['2'],
			info: {}
        }
    },
    mounted(){},
    methods:{
        open(row){
            this.visible = true;
			this.getInfo(row.id);
            return this;
        },
		//获取自己所拥有的所有菜单
        async getInfo(logId){
			var reqData = {id: logId}
            var res = await this.$API.system.log.detail.get(reqData);
            if(res.code == 1){
                this.info = res.data;
            }
        },

    }
}
</script>

<style scoped>
	.content {margin: 0 20px 20px 20px;}
	.code {background: #848484;padding:15px;color: #fff;font-size: 12px;border-radius: 4px;}
</style>