<template>
	<div ref="scEcharts" :style="{height:height, width:width}"></div>
</template>

<script>
	// echarts 按需引入：只打包实际用到的图表类型与组件，避免全量引入
	import * as echarts from 'echarts/core';
	import { BarChart, CandlestickChart, GaugeChart, LineChart, PieChart, RadarChart } from 'echarts/charts';
	import {
		AxisPointerComponent,
		GridComponent,
		LegendComponent,
		TitleComponent,
		TooltipComponent
	} from 'echarts/components';
	import { LabelLayout, UniversalTransition } from 'echarts/features';
	import { CanvasRenderer } from 'echarts/renderers';
	import T from './echarts-theme-T.js';

	echarts.use([
		BarChart,
		CandlestickChart,
		GaugeChart,
		LineChart,
		PieChart,
		RadarChart,
		AxisPointerComponent,
		GridComponent,
		LegendComponent,
		TitleComponent,
		TooltipComponent,
		LabelLayout,
		UniversalTransition,
		CanvasRenderer
	]);
	echarts.registerTheme('T', T);
	const unwarp = (obj) => obj && (obj.__v_raw || obj.valueOf() || obj);

	export default {
		...echarts,
		name: "scEcharts",
		props: {
			height: { type: String, default: "100%" },
			width: { type: String, default: "100%" },
			nodata: {type: Boolean, default: false },
			option: { type: Object, default: () => {} }
		},
		data() {
			return {
				isActivat: false,
				myChart: null
			}
		},
		watch: {
			option: {
				deep:true,
				handler (v) {
					unwarp(this.myChart).setOption(v);
				}
			}
		},
		computed: {
			myOptions: function() {
				return this.option || {};
			}
		},
		activated(){
			if(!this.isActivat){
				this.$nextTick(() => {
					this.myChart.resize()
				})
			}
		},
		deactivated(){
			this.isActivat = false;
		},
		mounted(){
			this.isActivat = true;
			this.$nextTick(() => {
				this.draw();
			})
		},
		methods: {
			draw(){
				var myChart = echarts.init(this.$refs.scEcharts, 'T');
				myChart.setOption(this.myOptions);
				this.myChart = myChart;
				window.addEventListener('resize', () => myChart.resize());
			}
		}
	}
</script>
