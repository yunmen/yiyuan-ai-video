<template>
	<el-container>
		<el-container>
				<el-header>
					<div class="left-panel">
						<el-button type="primary" icon="el-icon-plus" @click="add"></el-button>
					</div>
					<div class="right-panel">
						<div class="right-panel-search">
							<el-input v-model="search.keyword" placeholder="配置键/说明" clearable></el-input>
							<el-button type="primary" icon="el-icon-search" @click="upsearch"></el-button>
						</div>
					</div>
				</el-header>
				<el-main class="nopadding">
					<el-tabs v-model="activeTab" class="config-tabs">
						<el-tab-pane v-for="t in tabs" :key="t.key" :name="t.key" :label="tabLabel(t)"></el-tab-pane>
					</el-tabs>
					<scTable ref="table" :apiObj="apiObj" stripe hide-pagination>
						<el-table-column label="#" type="index"></el-table-column>
						<el-table-column label="配置键" prop="key" width="220" show-overflow-tooltip></el-table-column>
						<el-table-column label="配置值" prop="value" show-overflow-tooltip></el-table-column>
						<el-table-column label="分组" prop="group" align="center" width="100"></el-table-column>
						<el-table-column label="说明" prop="remark" show-overflow-tooltip></el-table-column>
						<el-table-column label="公开" prop="is_public" align="center" width="80">
							<template #default="scope">
								<el-tag v-if="scope.row.is_public" type="success" size="small">公开</el-tag>
								<el-tag v-else type="info" size="small">私有</el-tag>
							</template>
						</el-table-column>
						<el-table-column label="操作" fixed="right" align="right" width="160">
							<template #default="scope">
								<el-button-group>
									<el-button text type="primary" size="small" @click="table_show(scope.row)">查看</el-button>
									<el-button text type="primary" size="small" @click="table_edit(scope.row)">编辑</el-button>
								</el-button-group>
							</template>
						</el-table-column>
					</scTable>
				</el-main>
		</el-container>
	</el-container>

	<save-dialog v-if="dialog.save" ref="saveDialog" @success="handleSuccess" @closed="dialog.save=false"></save-dialog>

</template>

<script>
	import saveDialog from './save.vue'

	export default {
		name: 'system.config',
		components: {
			saveDialog
		},
		data() {
			return {
				dialog: {
					save: false
				},
				// 分类标签:后端 group 字段统一为 gen,这里按配置键前缀做展示分类,
				// 避免模型/网关等关键配置被平铺列表的字母序埋到后几页
				tabs: [
					{ key: 'all', label: '全部' },
					{ key: 'model', label: '模型' },
					{ key: 'gateway', label: '网关' },
					{ key: 'route', label: '路由' },
					{ key: 'render', label: '生成参数' },
					{ key: 'quota', label: '额度与定价' }
				],
				activeTab: 'all',
				// 一次拉取的全量配置,分类/搜索在本地过滤
				allRows: [],
				search: {}
			}
		},
		computed: {
			// scTable 以 apiObj 变化为刷新信号:仅依赖 activeTab,切标签即重新过滤
			apiObj() {
				const tab = this.activeTab
				return {
					get: (params) => this.localList(tab, params)
				}
			},
			counts() {
				const c = { all: this.allRows.length }
				for (const r of this.allRows) {
					const k = this.classify(r.key)
					c[k] = (c[k] || 0) + 1
				}
				return c
			}
		},
		mounted() {
			this.loadAll()
		},
		methods: {
			// 配置键 → 展示分类(顺序即优先级:网关/路由先判,再判模型)
			classify(key) {
				const k = key || ''
				if (k.includes('.gw.') || k.includes('llm_')) return 'gateway'
				if (k.includes('route.')) return 'route'
				if (k.includes('_model')) return 'model'
				if (k.includes('ratio') || k.includes('resolution')) return 'render'
				if (k.includes('price') || k.includes('credits')) return 'quota'
				return 'all'
			},
			tabLabel(t) {
				const n = this.counts[t.key]
				return n ? `${t.label} (${n})` : t.label
			},
			// 拉全量:pageSize 取足够大,避免后端默认分页导致模型配置不在首屏
			async loadAll() {
				const res = await this.$API.system.config.list.get({ pageNum: 1, pageSize: 500 })
				if (res.code == 1) {
					this.allRows = res.data || []
					this.$nextTick(() => this.$refs.table && this.$refs.table.refresh())
				}
			},
			// 本地过滤:分类 + 关键字,返回 scTable 约定结构
			async localList(tab, params) {
				const kw = ((params && params.keyword) || '').toString().trim().toLowerCase()
				let rows = this.allRows
				if (tab !== 'all') rows = rows.filter(r => this.classify(r.key) === tab)
				if (kw) {
					rows = rows.filter(r =>
						(r.key || '').toLowerCase().includes(kw) || (r.remark || '').toLowerCase().includes(kw)
					)
				}
				return { code: 1, message: '操作成功', data: rows, total: rows.length }
			},
			//添加
			add(){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open()
				})
			},
			//编辑
			table_edit(row){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open('edit').setData(row)
				})
			},
			//查看
			table_show(row){
				this.dialog.save = true
				this.$nextTick(() => {
					this.$refs.saveDialog.open('show').setData(row)
				})
			},
			//搜索
			upsearch(){
				this.$refs.table.upData(this.search)
			},
			//新增/编辑成功后重新拉全量(分类计数与当前列表都可能变化)
			async handleSuccess(data, mode){
				if(mode=='add' || mode=='edit'){
					await this.loadAll()
				}
			}
		}
	}
</script>

<style scoped>
.config-tabs { padding: 0 15px; background: #fff; }
.config-tabs :deep(.el-tabs__header) { margin-bottom: 0; }
</style>
