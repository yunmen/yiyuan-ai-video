<script setup>
import { reactive, ref } from 'vue'
import { state, go, toast } from '../store/app'
import AppBar from '../components/AppBar.vue'

const LS_NOTIFY = 'yy_notify'
const notify = reactive(JSON.parse(localStorage.getItem(LS_NOTIFY) || '{"gen":true,"promo":true,"sys":false}'))

function toggleNotify(key) {
  notify[key] = !notify[key]
  localStorage.setItem(LS_NOTIFY, JSON.stringify(notify))
  toast(`${labelOf(key)}已${notify[key] ? '开启' : '关闭'}`)
}

function labelOf(key) {
  return { gen: '生成完成通知', promo: '活动优惠通知', sys: '系统公告' }[key]
}

const doc = ref(null) // 'agreement' | 'privacy' | null
const docs = {
  agreement: {
    title: '用户协议',
    body: '欢迎使用一源 AI 视频。使用本服务即表示你同意：1）你上传的素材拥有合法使用权；2）生成的内容仅用于正当营销用途；3）不得用于违法违规场景；4）服务按"现状"提供，AI 生成结果可能存在偏差。'
  },
  privacy: {
    title: '隐私政策',
    body: '我们仅收集为提供服务所必需的信息：1）手机号用于登录验证；2）你上传的图片/视频仅用于本次生成，处理完成后自动删除；3）所有数据传输均加密；4）你可在设置中随时清除本地缓存。'
  }
}

function clearCache() {
  localStorage.removeItem('yy_works')
  state.works = []
  toast('缓存已清除（作品列表已重置）')
}

function logout() {
  state.logged = false
  state.stack = []
  go('home', true)
  toast('已退出登录')
}

const arrow = 'M7.5 4L13.5 10L7.5 16'
</script>

<template>
  <section class="page active">
    <AppBar title="设置" back-target="me" />
    <div class="body">
      <div class="set-group">
        <div class="g-title">账号</div>
        <div class="g-card">
          <div class="set-item" @click="toast('手机号修改需重新验证')">
            修改手机号
            <span class="s-sub">138****6688<svg height="20" viewBox="0 0 20 20" width="20"><path :d="arrow" fill="none" stroke="#C9CCD1" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg></span>
          </div>
          <div class="set-item" @click="go('change-password')">
            修改密码
            <svg height="20" viewBox="0 0 20 20" width="20"><path :d="arrow" fill="none" stroke="#C9CCD1" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <div class="set-group">
        <div class="g-title">通知</div>
        <div class="g-card">
          <div class="set-item">
            生成完成通知
            <div @click="toggleNotify('gen')">
              <svg v-if="notify.gen" width="44" height="24" viewBox="0 0 44 24"><rect width="44" height="24" rx="12" fill="#FF4D1C"/><circle cx="32" cy="12" r="10" fill="#fff"/></svg>
              <svg v-else width="44" height="24" viewBox="0 0 44 24"><rect width="44" height="24" rx="12" fill="#DCDFE4"/><circle cx="12" cy="12" r="10" fill="#fff"/></svg>
            </div>
          </div>
          <div class="set-item">
            活动优惠通知
            <div @click="toggleNotify('promo')">
              <svg v-if="notify.promo" width="44" height="24" viewBox="0 0 44 24"><rect width="44" height="24" rx="12" fill="#FF4D1C"/><circle cx="32" cy="12" r="10" fill="#fff"/></svg>
              <svg v-else width="44" height="24" viewBox="0 0 44 24"><rect width="44" height="24" rx="12" fill="#DCDFE4"/><circle cx="12" cy="12" r="10" fill="#fff"/></svg>
            </div>
          </div>
          <div class="set-item">
            系统公告
            <div @click="toggleNotify('sys')">
              <svg v-if="notify.sys" width="44" height="24" viewBox="0 0 44 24"><rect width="44" height="24" rx="12" fill="#FF4D1C"/><circle cx="32" cy="12" r="10" fill="#fff"/></svg>
              <svg v-else width="44" height="24" viewBox="0 0 44 24"><rect width="44" height="24" rx="12" fill="#DCDFE4"/><circle cx="12" cy="12" r="10" fill="#fff"/></svg>
            </div>
          </div>
        </div>
      </div>

      <div class="set-group">
        <div class="g-title">通用</div>
        <div class="g-card">
          <div class="set-item" @click="clearCache">
            清除缓存
            <span class="s-sub">{{ state.works.length }} 个作品<svg height="20" viewBox="0 0 20 20" width="20"><path :d="arrow" fill="none" stroke="#C9CCD1" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg></span>
          </div>
          <div class="set-item" @click="toast('已是最新版本 V1.0')">
            检查更新
            <svg height="20" viewBox="0 0 20 20" width="20"><path :d="arrow" fill="none" stroke="#C9CCD1" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <div class="set-group">
        <div class="g-title">协议</div>
        <div class="g-card">
          <div class="set-item" @click="doc = 'agreement'">
            用户协议
            <svg height="20" viewBox="0 0 20 20" width="20"><path :d="arrow" fill="none" stroke="#C9CCD1" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>
          </div>
          <div class="set-item" @click="doc = 'privacy'">
            隐私政策
            <svg height="20" viewBox="0 0 20 20" width="20"><path :d="arrow" fill="none" stroke="#C9CCD1" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <button class="logout-btn" @click="logout">退出登录</button>
      <div class="version">一源 AI 视频 V1.0</div>
    </div>

    <!-- 协议弹窗 -->
    <div class="overlay" :class="{ on: doc }" @click.self="doc = null">
      <div v-if="doc" class="modal">
        <h3>{{ docs[doc].title }}</h3>
        <p class="muted" style="margin:0; line-height:1.8; font-size:13px; color:var(--body)">{{ docs[doc].body }}</p>
        <div class="btn-p" @click="doc = null">我知道了</div>
      </div>
    </div>
  </section>
</template>
