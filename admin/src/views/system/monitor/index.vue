<!--
 * @Descripttion: 系统计划任务配置
 * @version: 1.2
 * @Author: sakuya
 * @Date: 2021年7月7日09:28:32
 * @LastEditors: sakuya
 * @LastEditTime: 2021年7月10日20:56:47
-->

<template>
	<el-main>
        <el-row :gutter="15">
            <el-col :span="12">
                <el-card  shadow="hover" header="CPU使用情况">
                    <el-row :gutter="15">
                        <el-col :span="12">
                            <el-card  shadow="hover" header="核心数">
                                <div class="progress">
                                    <el-progress type="circle" :percentage="100" :width="160">
                                        <template #default="{ percentage }">
                                            <div class="percentage-value">{{ percentage }}%</div>
                                            <div class="percentage-label">当前进度</div>
                                        </template>
                                    </el-progress>
                                </div>
                                <el-descriptions :column="1" border size="small">
                                    <el-descriptions-item label="总核心数">{{ cpu.count }}</el-descriptions-item>
                                    <el-descriptions-item label="已用核心数">{{ Math.floor((cpu?.used || 0) * cpu?.count / 100) }}</el-descriptions-item>
                                    <el-descriptions-item label="空闲核心数">{{ Math.floor((cpu?.free || 0) * cpu?.count / 100) }}</el-descriptions-item>
                                </el-descriptions>
                            </el-card>
                        </el-col>
                        <el-col :span="12">
                            <el-card  shadow="hover" header="使用率">
                                <div class="progress">
                                    <el-progress type="circle" :percentage="cpu?.used || 0" :width="160">
                                        <template #default="{ percentage }">
                                            <div class="percentage-value">{{ percentage }}%</div>
                                            <div class="percentage-label">当前进度</div>
                                        </template>
                                    </el-progress>
                                </div>
                                <el-descriptions :column="1" border size="small">
                                    <el-descriptions-item label="用户使用率">{{(cpu?.used || 0).toFixed(1) + '%'}}</el-descriptions-item>
                                    <el-descriptions-item label="系统使用率">{{(cpu?.sys || 0).toFixed(1) + '%'}}</el-descriptions-item>
                                    <el-descriptions-item label="当前空闲率">{{(cpu?.free || 0).toFixed(1) + '%'}}</el-descriptions-item>
                                </el-descriptions>
                            </el-card>
                        </el-col>
                    </el-row>
                </el-card>
            </el-col>
            <el-col :span="12">
                <el-card  shadow="hover" header="内存使用情况">
                    <el-row :gutter="15">
                        <el-col :span="12">
                            <el-card  shadow="hover" header="系统内存">
                                <div class="progress">
                                    <el-progress type="dashboard" :percentage="memory.usage" :width="160">
                                        <template #default="{ percentage }">
                                            <div class="percentage-value">{{ percentage }}%</div>
                                            <div class="percentage-label">使用率</div>
                                        </template>
                                    </el-progress>
                                </div>
                                <el-descriptions :column="1" border size="small">
                                    <el-descriptions-item label="总内存">{{ memory.total }}</el-descriptions-item>
                                    <el-descriptions-item label="已用内存">{{ memory.used }}</el-descriptions-item>
                                    <el-descriptions-item label="空闲内存">{{ memory.free }}</el-descriptions-item>
                                </el-descriptions>
                            </el-card>
                        </el-col>
                        <el-col :span="12">
                            <el-card  shadow="hover" header="Python内存">
                                <div class="progress">
                                    <el-progress type="dashboard" :percentage="python.usage" :width="160">
                                        <template #default="{ percentage }">
                                            <div class="percentage-value">{{ percentage }}%</div>
                                            <div class="percentage-label">使用率</div>
                                        </template>
                                    </el-progress>
                                </div>
                                <el-descriptions :column="1" border size="small">
                                    <el-descriptions-item label="总内存">{{ python.total }}</el-descriptions-item>
                                    <el-descriptions-item label="已用内存">{{ python.used }}</el-descriptions-item>
                                    <el-descriptions-item label="空闲内存">{{  python.free }}</el-descriptions-item>
                                </el-descriptions>
                            </el-card>
                        </el-col>
                    </el-row>
                </el-card>
            </el-col>
        </el-row>
        <el-card  shadow="hover" header="服务器基本信息" class="card">
		    <el-descriptions :column="2" border size="small">
				<el-descriptions-item label="服务器名称	">{{ sys.computer_name }}</el-descriptions-item>
                <el-descriptions-item label="操作系统">{{ sys.os_name}}</el-descriptions-item>
                <el-descriptions-item label="服务器IP">{{ sys.computer_ip }}</el-descriptions-item>
                <el-descriptions-item label="系统架构">{{  sys.os_arch }}</el-descriptions-item>
			</el-descriptions>
        </el-card>
        <el-card  shadow="hover" header="Python运行环境" class="card">
		    <el-descriptions :column="3" border size="small">
				<el-descriptions-item label="Python名称	">{{ python.name }}</el-descriptions-item>
                <el-descriptions-item label="Python版本">{{ python.version }}</el-descriptions-item>
                <el-descriptions-item label="启动时间">{{ python.start_time}}</el-descriptions-item>
                <el-descriptions-item label="安装路径">{{ python.home }}</el-descriptions-item>
                <el-descriptions-item label="项目路径">{{ sys.user_dir}}</el-descriptions-item>
                <el-descriptions-item label="运行时长">{{ python.run_time }}</el-descriptions-item>
			</el-descriptions>
        </el-card>
        <el-card  shadow="hover" header="磁盘使用情况" class="card">
		    <scTable ref="table" :data="disk" row-key="id" hidePagination hideDo>
				<el-table-column label="盘符路径" prop="path" ></el-table-column>
				<el-table-column label="文件系统" prop="fstype"  ></el-table-column>
				<el-table-column label="使用率" prop="percent"  >
                    <template #default="scope">
                        <el-progress
                        :text-inside="true"
                        :stroke-width="24"
                        :percentage="scope.row.percent"
                        status="success"
                        />
                    </template>
                </el-table-column>
				<el-table-column label="总大小" prop="total"  ></el-table-column>
				<el-table-column label="可用大小" prop="free"  ></el-table-column>
                <el-table-column label="已用大小" prop="used"  ></el-table-column>
			</scTable>
        </el-card>
	</el-main>


</template>

<script>
	export default {
		name: 'system.monitor',
		components: {},

		data() {
			return {
                cpu: {},
                memory: {},
                sys: {},
                python: {},
                disk: []
			}
		},
		mounted() {
            this.get_detail()
		},
		methods: {
			async get_detail(){
                var res = await this.$API.system.monitor.detail.get();
                if (res.code == 1){
                    this.cpu = res.data.cpu;
                    this.memory = res.data.memory;
                    this.sys = res.data.sys;
                    this.python = res.data.python;
                    this.disk = res.data.disk;
                }
            },
		}
	}
</script>

<style scoped>
	.progress {text-align: center;}
	.progress .percentage-value {font-size: 28px;}
	.progress .percentage-label {font-size: 12px;margin-top: 10px;}
    .card {
        margin-bottom: 10px;
    }
</style>
