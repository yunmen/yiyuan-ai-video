<script setup>
import { ref } from 'vue'
import api from '@/api'

const openIdx = ref(-1)
const faqRef = ref(null)
const fbRef = ref(null)
const feedbackText = ref('')
const feedbackContact = ref('')
const feedbackSending = ref(false)

function toggle(i) {
  openIdx.value = openIdx.value === i ? -1 : i
}

async function copyWechat() {
  try {
    await navigator.clipboard.writeText('yiyuan-kefu')
    window.$message?.success('微信号已复制：yiyuan-kefu')
  } catch {
    window.$message?.info('复制失败，微信号：yiyuan-kefu')
  }
}

function scrollToFaq() {
  faqRef.value?.scrollIntoView({ behavior: 'smooth' })
}

function scrollToFb() {
  fbRef.value?.scrollIntoView({ behavior: 'smooth' })
  fbRef.value?.querySelector('textarea')?.focus()
}

// 提交意见反馈:真实调用 backend /feedback/create,而非仅弹提示
async function feedback() {
  const content = feedbackText.value.trim()
  if (!content) {
    window.$message?.warning('请输入反馈内容')
    return
  }
  feedbackSending.value = true
  try {
    const res = await api.feedback.create.post({
      content,
      contact: feedbackContact.value.trim(),
    })
    if (res.code === 1) {
      window.$message?.success('反馈已提交，感谢你的建议')
      feedbackText.value = ''
      feedbackContact.value = ''
    } else {
      window.$message?.warning(res.message || '提交失败，请稍后重试')
    }
  } catch {
    window.$message?.warning('提交失败，请稍后重试或联系客服')
  } finally {
    feedbackSending.value = false
  }
}

const faqs = [
  { q: '生成视频需要多久？', a: '生成耗时取决于成片时长，通常几分钟即可完成，长视频或高峰期可能稍久。生成完成后可在「我的作品」中查看和下载。' },
  { q: '生成的视频有水印吗？', a: '免费额度生成的视频带一源角标，充值套餐生成的视频均为无水印高清版。' },
  { q: '支持哪些视频格式和时长？', a: '目前支持 MP4、WebM 格式，时长 5-30 秒，建议上传竖版 9:16 视频效果最佳。' },
  { q: '免费额度怎么获取？', a: '每日 0 点自动重置 3 次免费额度，签到、邀请好友还可额外获得。' },
  { q: '生成的视频可以商用吗？', a: '个人版套餐生成的视频仅限个人使用，商用需购买企业版授权，请联系客服开通。' }
]
</script>

<template>
  <div class="support-page">
    <div class="wrap">
      <div class="tip">
        <svg width="16" height="16" viewBox="0 0 16 16"><circle cx="8" cy="8" r="7" fill="none" stroke="#FF7A45" stroke-width="1.5"/><path d="M8 4V8.5M8 11.5V11" stroke="#FF7A45" stroke-width="1.5" stroke-linecap="round"/></svg>
        客服在线时间：工作日 9:00-21:00，留言将在 24 小时内回复
      </div>

      <div class="quick">
        <div class="q" @click="copyWechat">
          <div class="q-ic"><svg width="22" height="22" viewBox="0 0 22 22"><path d="M8 4C4.7 4 2 6.2 2 9C2 10.5 2.8 11.9 4 12.7L3.5 15L6 13.8C6.6 14 7.3 14.1 8 14.1" fill="none" stroke="#FF4D1C" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.5 14.5C9.5 11.9 12 9.9 15 9.9C18 9.9 20.5 11.9 20.5 14.5C20.5 17.1 18 19.1 15 19.1C14.4 19.1 13.8 19 13.3 18.8L11 19.9L11.4 17.6C10.2 16.8 9.5 15.7 9.5 14.5Z" fill="none" stroke="#FF4D1C" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
          <span>微信客服</span>
        </div>
        <div class="q" @click="scrollToFaq">
          <div class="q-ic"><svg width="22" height="22" viewBox="0 0 22 22"><circle cx="11" cy="11" r="9" fill="none" stroke="#FF4D1C" stroke-width="1.6"/><path d="M8 9C8 7.3 9.3 6 11 6C12.7 6 14 7.3 14 9C14 10 13.3 10.8 12.5 11.2C11.8 11.6 11 12 11 13" fill="none" stroke="#FF4D1C" stroke-width="1.6" stroke-linecap="round"/><circle cx="11" cy="16" r="1" fill="#FF4D1C"/></svg></div>
          <span>常见问题</span>
        </div>
        <div class="q" @click="scrollToFb">
          <div class="q-ic"><svg width="22" height="22" viewBox="0 0 22 22"><rect x="3" y="4" width="16" height="12" rx="2" fill="none" stroke="#FF4D1C" stroke-width="1.6"/><path d="M3 6L11 11L19 6" fill="none" stroke="#FF4D1C" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
          <span>意见反馈</span>
        </div>
        <div class="q" @click="location.href='tel:4008880000'">
          <div class="q-ic"><svg width="22" height="22" viewBox="0 0 22 22"><path d="M5 3H8L10 8L7.5 9.5C8.5 11.5 10.5 13.5 12.5 14.5L14 12L19 14V17C19 18.1 18.1 19 17 19C9.8 19 3 12.2 3 5C3 3.9 3.9 3 5 3Z" fill="none" stroke="#FF4D1C" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
          <span>电话咨询</span>
        </div>
      </div>

      <div ref="fbRef" class="fb">
        <div class="fb-title">意见反馈</div>
        <textarea v-model="feedbackText" class="fb-input" maxlength="1000" placeholder="说说你的建议或遇到的问题（必填）"></textarea>
        <input v-model="feedbackContact" class="fb-contact" maxlength="100" placeholder="联系方式（选填，方便我们回复你）" />
        <button class="fb-btn" :disabled="feedbackSending" @click="feedback">提交反馈</button>
      </div>

      <div ref="faqRef" class="faq">
        <div class="faq-title">常见问题</div>
        <div v-for="(f, i) in faqs" :key="i" class="f-item" :class="{ open: openIdx === i }">
          <div class="f-q" @click="toggle(i)">
            {{ f.q }}
            <svg width="16" height="16" viewBox="0 0 16 16"><path d="M4 6L8 10L12 6" fill="none" stroke="#C9CCD1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div class="f-a">{{ f.a }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.support-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding-bottom: 80px; }
.wrap { max-width: 560px; margin: 0 auto; padding: 20px; }

.tip {
  display: flex; align-items: center; gap: 6px;
  background: var(--brand-bg); color: #FF7A45;
  font-size: 13px; padding: 10px 12px; border-radius: var(--radius-sm);
}

.quick {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;
  margin-top: 16px;
}
.q {
  background: #fff; border-radius: var(--radius); padding: 20px 0;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  font-size: 13px; cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: transform .18s, box-shadow .18s;
}
.q:hover { transform: translateY(-3px); box-shadow: var(--shadow-brand); }
.q-ic { display: flex; }

.fb {
  margin-top: 16px; background: #fff; border-radius: var(--radius); padding: 16px;
  box-shadow: var(--shadow-sm);
}
.fb-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
.fb-input {
  width: 100%; min-height: 96px; resize: vertical; box-sizing: border-box;
  border: 1px solid #e5e7eb; border-radius: var(--radius-sm); padding: 10px 12px;
  font-size: 14px; line-height: 1.6; outline: none; font-family: inherit;
}
.fb-input:focus { border-color: var(--brand-color, #FF4D1C); }
.fb-contact {
  width: 100%; box-sizing: border-box; margin-top: 10px;
  border: 1px solid #e5e7eb; border-radius: var(--radius-sm); padding: 9px 12px;
  font-size: 13px; outline: none;
}
.fb-contact:focus { border-color: var(--brand-color, #FF4D1C); }
.fb-btn {
  margin-top: 12px; width: 100%; border: none; border-radius: var(--radius-sm);
  background: var(--brand-color, #FF4D1C); color: #fff; font-size: 14px;
  padding: 10px 0; cursor: pointer; transition: opacity .18s;
}
.fb-btn:disabled { opacity: .6; cursor: not-allowed; }

.faq { margin-top: 24px; }
.faq-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
.f-item {
  background: #fff; border-radius: var(--radius); margin-bottom: 10px;
  overflow: hidden; box-shadow: var(--shadow-sm);
}
.f-q {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; font-size: 14px; cursor: pointer;
}
.f-q svg { transition: transform .2s; flex-shrink: 0; }
.f-item.open .f-q svg { transform: rotate(180deg); }
.f-a {
  max-height: 0; overflow: hidden; transition: max-height .25s ease;
  padding: 0 16px; font-size: 13px; color: var(--body-c); line-height: 1.7;
}
.f-item.open .f-a { max-height: 200px; padding-bottom: 14px; }

@media (min-width: 768px) {
  .wrap { max-width: 860px; padding: 24px; }
  .quick { grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 20px; }
}
</style>
