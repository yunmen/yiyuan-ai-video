<script setup>
import { reactive } from 'vue'
import { go, toast } from '../store/app'
import AppBar from '../components/AppBar.vue'

const form = reactive({ old: '', pwd: '', confirm: '' })
const show = reactive({ old: false, pwd: false, confirm: false })

function submit() {
  if (!form.old) return toast('请输入原密码')
  if (form.pwd.length < 6) return toast('新密码至少 6 位')
  if (form.pwd === form.old) return toast('新密码不能与原密码相同')
  if (form.pwd !== form.confirm) return toast('两次输入的新密码不一致')
  toast('密码修改成功')
  go('settings', true)
}

const eyeOn = 'M2 12C4.5 7 8 5 12 5C16 5 19.5 7 22 12C19.5 17 16 19 12 19C8 19 4.5 17 2 12Z'
const eyeOff = 'M3 3L21 21M10 5.2C10.6 5.1 11.3 5 12 5C16 5 19.5 7 22 12C21.2 13.5 20.2 14.8 19 15.8M14.1 18.7C13.4 18.9 12.7 19 12 19C8 19 4.5 17 2 12C3 10.2 4.4 8.7 6.1 7.6'
</script>

<template>
  <section class="page active">
    <AppBar title="修改密码" back-target="settings" />
    <div class="body">
      <div class="pwd-card">
        <div class="pwd-item">
          <span class="lb">原密码</span>
          <input v-model="form.old" :type="show.old ? 'text' : 'password'" placeholder="请输入原密码" maxlength="20" />
          <span class="eye" @click="show.old = !show.old">
            <svg v-if="show.old" width="20" height="20" viewBox="0 0 24 24"><path :d="eyeOn" fill="none" stroke="#8A8F99" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" fill="none" stroke="#8A8F99" stroke-width="1.6"/></svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24"><path :d="eyeOff" fill="none" stroke="#C9CCD1" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
        <div class="pwd-item">
          <span class="lb">新密码</span>
          <input v-model="form.pwd" :type="show.pwd ? 'text' : 'password'" placeholder="6-20 位字符" maxlength="20" />
          <span class="eye" @click="show.pwd = !show.pwd">
            <svg v-if="show.pwd" width="20" height="20" viewBox="0 0 24 24"><path :d="eyeOn" fill="none" stroke="#8A8F99" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" fill="none" stroke="#8A8F99" stroke-width="1.6"/></svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24"><path :d="eyeOff" fill="none" stroke="#C9CCD1" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
        <div class="pwd-item">
          <span class="lb">确认密码</span>
          <input v-model="form.confirm" :type="show.confirm ? 'text' : 'password'" placeholder="请再次输入新密码" maxlength="20" @keyup.enter="submit" />
          <span class="eye" @click="show.confirm = !show.confirm">
            <svg v-if="show.confirm" width="20" height="20" viewBox="0 0 24 24"><path :d="eyeOn" fill="none" stroke="#8A8F99" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" fill="none" stroke="#8A8F99" stroke-width="1.6"/></svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24"><path :d="eyeOff" fill="none" stroke="#C9CCD1" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
      </div>

      <div class="pwd-submit">
        <button class="btn-p" @click="submit">确认修改</button>
      </div>
      <div class="pwd-tip">密码需为 6-20 位字符，建议包含字母和数字。修改成功后请妥善保管新密码。</div>
    </div>
  </section>
</template>
