<script setup>
import { state, restart } from '../store/app'

const hot = defineModel('hot', { type: Boolean, default: false })
</script>

<template>
  <div class="panel">
    <h2>一源 V1.0 · 可点击原型</h2>
    <p class="lead">手机里每个按钮都能点。直接演示主路径：首页 → 立即制作 → 选模板 → 填素材 → 生成 → 下载。</p>

    <h4>主路径（3 次点击到生成）</h4>
    <div class="flow">
      <b>首页</b> 点「立即制作」<br>
      → <b>模板选择</b> 点任意模板卡<br>
      → <b>替换素材</b> 填完点「生成视频」<br>
      → <b>生成中</b>（进度跑完自动跳）<br>
      → <b>结果预览</b> 下载 / 再做一个
    </div>

    <h4>分支与状态</h4>
    <div class="kv"><span>首页「登录」</span><span>弹窗浮层，登录后变头像</span></div>
    <div class="kv"><span>首页「去看看」</span><span>数字人页，点选择 → toast</span></div>
    <div class="kv"><span>模板页 Tab</span><span>选模板做 / 上传参考做</span></div>
    <div class="kv"><span>分类条</span><span>切换真实过滤卡片</span></div>
    <div class="kv"><span>必填未填</span><span>生成按钮置灰不可点</span></div>
    <div class="kv"><span>生成中点「返回首页等」</span><span>回首页，后台继续</span></div>
    <div class="kv"><span>客服浮窗 / 分享 / 下载</span><span>toast 提示</span></div>

    <h4>演示控制台</h4>
    <div class="tools">
      <button @click="restart">重新开始</button>
      <button :class="{ on: hot }" @click="hot = !hot">显示热区</button>
      <button :class="{ on: state.emptyWorks }" @click="state.emptyWorks = !state.emptyWorks">切换作品空状态</button>
      <button :class="{ on: state.logged }" @click="state.logged = !state.logged">切换登录状态</button>
    </div>
  </div>
</template>
