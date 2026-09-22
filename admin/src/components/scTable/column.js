import { h } from 'vue'
// Element Plus 已改为按需引入，组件不再全局注册，
// 因此这里必须显式引入，不能用 resolveComponent("el-table-column") 运行时解析
import { ElTableColumn } from 'element-plus'

export default {
	render() {
		return h (
			ElTableColumn,
			{
				index: this.index,
				...this.$attrs
			},
			this.$slots
		)
	},
	methods: {
		index(index){
			if(this.$attrs.type=="index"){
				let page = this.$parent.$parent.currentPage
				let pageSize = this.$parent.$parent.pageSize
				return (page - 1) * pageSize + index + 1
			}
		}
	}
}
