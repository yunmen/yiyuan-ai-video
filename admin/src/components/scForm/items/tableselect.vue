<template>
	<sc-table-select v-model="value" :apiObj="apiObj" :table-width="600" :multiple="item.options.multiple" :props="item.options.props" style="width: 100%;">
		<el-table-column  v-for="(_item, _index) in item.options.column" :key="_index" :prop="_item.prop" :label="_item.label" :width="_item.width"></el-table-column>
	</sc-table-select>
</template>

<script>
	export default {
		name: 'uploadRender',
		props: {
			modelValue: [String, Number, Boolean, Date, Object, Array],
			item: { type: Object, default: () => {} }
		},
		data() {
			return {
				value: this.modelValue,
				apiObj: this.getApiObj()
			}
		},
		watch:{
			value(val){
				this.$emit("update:modelValue", val)
			}
		},
		mounted() {

		},
		methods: {
			getApiObj(){
				//按属性路径逐级取值(如 $API.user.list),代替 eval(`this.`+path)
				const path = String(this.item.options.apiObj || '').split('.')
				return path.reduce((obj, key) => (obj == null ? obj : obj[key]), this)
			}
		}
	}
</script>

<style>
</style>
