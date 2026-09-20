<!--
 * @Descripttion: 生成二维码组件
 * @version: 1.0
 * @Author: sakuya
 * @Date: 2021年12月20日14:22:20
 * @LastEditors:
 * @LastEditTime:
-->

<template>
	<img ref="img"/>
</template>

<script>
	import QRCode from "qrcode"

	const correctLevelMap = { 0: 'L', 1: 'M', 2: 'Q', 3: 'H' }

	export default {
		props: {
			text: { type: String, required: true, default: "" },
			size: { type: Number, default: 100 },
			logo: { type: String, default: "" },
			logoSize: { type: Number, default: 30 },
			logoPadding: { type: Number, default: 5 },
			colorDark: { type: String, default: "#000000" },
			colorLight: { type: String, default: "#ffffff" },
			correctLevel: { type: Number, default: 2 },
		},
		data() {
			return {
				canvas: null
			}
		},
		watch:{
			text(){
				this.draw()
			}
		},
		mounted() {
			this.draw()
		},
		methods: {
			//创建原始二维码DOM
			async create(){
				const canvas = document.createElement("canvas")
				await QRCode.toCanvas(canvas, this.text, {
					width: this.size,
					margin: 0,
					color: {
						dark: this.colorDark,
						light: this.colorLight
					},
					errorCorrectionLevel: correctLevelMap[this.correctLevel] || 'Q'
				})
				this.canvas = canvas
			},
			//绘制LOGO
			async drawLogo(){
				return new Promise((resolve) => {
					var logo = new Image()
					logo.src = this.logo
					logo.crossOrigin = 'anonymous'
					const logoPos = (this.size - this.logoSize) / 2
					const rectSize = this.logoSize + this.logoPadding
					const rectPos = (this.size - rectSize) / 2
					var ctx = this.canvas.getContext("2d")
					logo.onload = ()=>{
						ctx.fillRect(rectPos, rectPos, rectSize, rectSize)
						ctx.drawImage(logo, logoPos, logoPos, this.logoSize, this.logoSize)
						resolve()
					}
					logo.onerror = () => resolve()
				})
			},
			async draw(){
				await this.create()
				if(this.logo){
					await this.drawLogo()
				}
				this.$refs.img.src = this.canvas.toDataURL("image/png")
			},
		}
	}
</script>

<style>
</style>
