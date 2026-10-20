<template>
  <view class="app-page digital">
    <AppNavBar title="数字人口播">
      <template #right>
        <view class="digital__upload" role="button" aria-label="上传我的形象" @click="createPersonalAvatar" tabindex="0" @keydown.enter.stop.prevent="createPersonalAvatar" @keydown.space.stop.prevent="createPersonalAvatar">
          <AppIcon name="plus" :size="14" color="#B23A2E" :stroke-width="2.5" />
          <text>上传</text>
        </view>
      </template>
    </AppNavBar>
    <view class="tool-intro app-enter"><text class="tool-intro__title">不用出镜，也有好表达。</text><text class="tool-intro__desc">选择一个形象，写下你想说的话。</text></view>


    <!-- 形象来源切换：吸顶在导航栏正下方 -->
    <view class="digital__tabs" :style="{ top: navBarHeight + 'px' }">
      <view
        class="digital__tab"
        :class="{ 'digital__tab--active': tab === 'platform' }"
        role="button"
        aria-label="平台形象"
        @click="tab = 'platform'"
       tabindex="0" @keydown.enter.stop.prevent="tab = 'platform'" @keydown.space.stop.prevent="tab = 'platform'">
        <text>平台形象</text>
      </view>
      <view
        class="digital__tab"
        :class="{ 'digital__tab--active': tab === 'mine' }"
        role="button"
        aria-label="我的形象"
        @click="switchToMine"
       tabindex="0" @keydown.enter.stop.prevent="switchToMine" @keydown.space.stop.prevent="switchToMine">
        <text>我的形象</text>
      </view>
    </view>

    <!-- ============ 平台形象 ============ -->
    <view v-if="tab === 'platform'" class="digital__panel">
      <view v-if="platformLoading" class="digital__grid">
        <view v-for="n in 4" :key="n" class="digital__card digital__card--skeleton">
          <view class="digital__cover digital__cover--skeleton" />
          <view class="digital__body">
            <view class="digital__skel-line" />
            <view class="digital__skel-btn" />
          </view>
        </view>
      </view>

      <AppEmpty v-else-if="platformError" title="形象加载失败" :desc="platformError" icon="alert-circle" action-text="重新加载" @action="loadPlatform" />

      <view v-else-if="platformList.length" class="digital__grid">
        <view
          v-for="item in platformList"
          :key="item.id"
          class="digital__card"
          role="button"
          @click="openSheet(item)"
         tabindex="0" @keydown.enter.stop.prevent="openSheet(item)" @keydown.space.stop.prevent="openSheet(item)">
          <view class="digital__cover">
            <image v-if="coverOf(item)" class="digital__img" :src="coverOf(item)" mode="aspectFill" />
            <view v-else class="digital__img digital__img--empty">
              <view class="digital__ph-icon">
                <AppIcon name="user" :size="48" color="#B23A2E" />
              </view>
            </view>
            <text v-if="tagOf(item).text" class="digital__tag" :class="tagOf(item).cls">
              {{ tagOf(item).text }}
            </text>
          </view>
          <view class="digital__body">
            <text class="digital__name app-truncate">{{ item.name }}</text>
            <view class="digital__select" role="button" @click.stop="openSheet(item)" tabindex="0" @keydown.enter.stop.prevent="openSheet(item)" @keydown.space.stop.prevent="openSheet(item)">
              <text>选择</text>
            </view>
          </view>
        </view>
      </view>

      <AppEmpty v-else title="数字人整理中" desc="敬请期待，也可以先上传你自己的形象" icon="user" />
    </view>

    <!-- ============ 我的形象 ============ -->
    <view v-else class="digital__panel">
      <AppEmpty v-if="mineError" title="我的形象加载失败" :desc="mineError" icon="alert-circle" action-text="重新加载" @action="loadMine" />
      <view v-else class="digital__grid">
        <view
          v-for="item in mineList"
          :key="item.id"
          class="digital__card"
          role="button"
          @click="openSheet(item)"
         tabindex="0" @keydown.enter.stop.prevent="openSheet(item)" @keydown.space.stop.prevent="openSheet(item)">
          <view class="digital__cover">
            <image v-if="coverOf(item)" class="digital__img" :src="coverOf(item)" mode="aspectFill" />
            <view v-else class="digital__img digital__img--empty">
              <view class="digital__ph-icon">
                <AppIcon name="user" :size="48" color="#B23A2E" />
              </view>
            </view>
            <text v-if="tagOf(item).text" class="digital__tag" :class="tagOf(item).cls">
              {{ tagOf(item).text }}
            </text>
          </view>
          <view class="digital__body">
            <text class="digital__name app-truncate">{{ item.name }}</text>
            <view class="digital__select" role="button" @click.stop="openSheet(item)" tabindex="0" @keydown.enter.stop.prevent="openSheet(item)" @keydown.space.stop.prevent="openSheet(item)">
              <text>选择</text>
            </view>
          </view>
        </view>

        <!-- 上传我的形象：设计稿的虚线占位卡 -->
        <view class="digital__card digital__card--upload" role="button" @click="createPersonalAvatar" tabindex="0" @keydown.enter.stop.prevent="createPersonalAvatar" @keydown.space.stop.prevent="createPersonalAvatar">
          <view class="digital__upload-content">
            <view class="digital__upload-icon">
              <AppIcon name="plus" :size="32" color="#B23A2E" :stroke-width="1.5" />
            </view>
            <text class="digital__upload-title">上传我的形象</text>
            <text class="digital__upload-sub">支持图片/视频</text>
          </view>
        </view>
      </view>

      <view v-if="!userStore.isLoggedIn" class="digital__login-tip" role="button" @click="goLogin" tabindex="0" @keydown.enter.stop.prevent="goLogin" @keydown.space.stop.prevent="goLogin">
        <text>登录后可上传并使用你的专属形象</text>
      </view>
      <text v-else-if="mineLoading" class="digital__loading-text">加载中…</text>
    </view>

    <!-- 底部提示条 -->
    <view class="digital__tip">
      <view class="digital__tip-icon">
        <AppIcon name="sparkles" :size="16" color="#FFFFFF" :stroke-width="2.5" />
      </view>
      <view class="digital__tip-text">
        <text class="digital__tip-title">选择形象，输入台词</text>
        <text class="digital__tip-sub">一键生成口型同步视频</text>
      </view>
    </view>

    <!-- ============ 形象详情 + 口播设置（底部弹层） ============ -->
    <view v-if="sheetVisible" class="digital__overlay" @click="closeSheet" @touchmove.stop.prevent>
      <view class="digital__sheet app-enter" role="dialog" aria-modal="true" aria-label="形象与口播设置" @click.stop @touchmove.stop @keydown.esc.stop.prevent="closeSheet">
        <view class="digital__handle-wrap">
          <view class="digital__handle" />
          <view class="digital__sheet-close" role="button" aria-label="关闭口播设置" @click="closeSheet" tabindex="0" @keydown.enter.stop.prevent="closeSheet" @keydown.space.stop.prevent="closeSheet"><AppIcon name="close" :size="20" color="#48463F" /></view>
        </view>

        <scroll-view class="digital__sheet-body" scroll-y>
          <!-- 形象预览 -->
          <view class="digital__preview">
            <view class="digital__preview-img">
              <image v-if="coverOf(active)" class="digital__img" :src="coverOf(active)" mode="aspectFill" />
              <view v-else class="digital__img digital__img--empty">
                <view class="digital__ph-icon">
                  <AppIcon name="user" :size="40" color="#B23A2E" />
                </view>
              </view>
            </view>
            <view class="digital__preview-meta">
              <text class="digital__preview-name app-truncate">{{ active?.name }}</text>
              <text v-if="tagOf(active).text" class="digital__tag" :class="tagOf(active).cls">
                {{ tagOf(active).text }}
              </text>
              <text class="digital__preview-desc">{{ active?.desc || '暂无简介' }}</text>
            </view>
          </view>

          <!-- 口播文案 -->
          <view class="digital__field">
            <text class="digital__label">口播文案</text>
            <AppTextarea
              v-model="scriptText"
              aria-label="口播文案"
              class="app-field digital__textarea"
              :maxlength="2000"
              placeholder="请输入您想要的口播台词，支持中英文..."
              placeholder-class="app-placeholder"
            />
            <view class="digital__counter-row">
              <text class="digital__counter">已输入 {{ scriptCount }} 字</text>
              <view class="digital__polish" role="button" @click="polishScript" tabindex="0" @keydown.enter.stop.prevent="polishScript" @keydown.space.stop.prevent="polishScript">
                <AppIcon name="sparkles" :size="12" color="#B23A2E" :stroke-width="2.5" />
                <text>{{ polishing ? '润色中…' : 'AI 润色' }}</text>
              </view>
            </view>
          </view>

          <!-- 音色选择：real 豆包官方音色，选中项存 code，提交时作为 voice -->
          <view class="digital__field">
            <text class="digital__label">音色选择</text>
            <view class="digital__voice-row">
              <picker mode="selector" :range="voiceLabels" :value="voiceIndex" @change="onVoiceChange">
                <view class="app-field digital__select-field">
                  <text class="digital__select-text app-truncate">{{ voiceLabel }}</text>
                  <AppIcon name="chevron-down" :size="16" color="#6B6357" />
                </view>
              </picker>
              <view class="digital__preview-btn" :class="{ 'digital__preview-btn--active': voicePreviewPlaying || voicePreviewLoading }" role="button" @click="toggleVoicePreview" tabindex="0" @keydown.enter.stop.prevent="toggleVoicePreview" @keydown.space.stop.prevent="toggleVoicePreview">
                <AppIcon :name="voicePreviewLoading ? 'loader' : voicePreviewPlaying ? 'pause' : 'play'" :size="14" color="#B23A2E" :stroke-width="2.5" />
                <text>{{ voicePreviewLoading ? '生成中' : voicePreviewPlaying ? '停止' : '试听' }}</text>
              </view>
            </view>
          </view>

          <!-- 更多设置（可折叠） -->
          <view class="digital__more">
            <view class="digital__more-head" role="button" :aria-expanded="moreOpen" @click="moreOpen = !moreOpen" tabindex="0" @keydown.enter.stop.prevent="moreOpen = !moreOpen" @keydown.space.stop.prevent="moreOpen = !moreOpen">
              <text class="digital__more-title">更多设置</text>
              <AppIcon
                name="chevron-down"
                :size="18"
                color="#6B6357"
                :class="moreOpen ? 'digital__arrow--open' : ''"
              />
            </view>

            <view v-if="moreOpen" class="digital__collapse app-enter">
              <view class="digital__collapse-inner">
                <!-- 语速 -->
                <view class="digital__setting">
                  <view class="digital__setting-head">
                    <text class="digital__setting-label">语速</text>
                    <text class="digital__setting-value">{{ speedText }}x</text>
                  </view>
                  <slider
                    class="digital__slider"
                    :min="0.5"
                    :max="2"
                    :step="0.1"
                    :value="speed"
                    activeColor="#B23A2E"
                    backgroundColor="#E7E0D1"
                    block-color="#B23A2E"
                    :block-size="20"
                    @changing="onSpeedChange"
                    @change="onSpeedChange"
                  />
                </view>

                <!-- 成片时长 -->
                <view class="digital__setting">
                  <text class="digital__setting-label">成片时长</text>
                  <view v-if="durationOptions.length" class="digital__segment">
                    <view
                      v-for="d in durationOptions"
                      :key="d"
                      class="digital__seg"
                      :class="{ 'digital__seg--active': Number(duration) === Number(d) }"
                      role="button"
                      @click="selectDuration(d)"
                     tabindex="0" @keydown.enter.stop.prevent="selectDuration(d)" @keydown.space.stop.prevent="selectDuration(d)" :aria-pressed="Number(duration) === Number(d)">
                      <text>{{ d }}s</text>
                    </view>
                  </view>
                  <text v-else class="digital__setting-hint">时长档位加载中…</text>
                </view>

                <!-- 画幅比例 -->
                <view class="digital__row" role="button" @click="pickRatio" tabindex="0" @keydown.enter.stop.prevent="pickRatio" @keydown.space.stop.prevent="pickRatio">
                  <text class="digital__row-label">画幅比例</text>
                  <view class="digital__row-value">
                    <text>{{ ratio || '系统默认' }}</text>
                    <AppIcon name="chevron-right" :size="16" color="#6B6357" />
                  </view>
                </view>

                <!-- 清晰度 -->
                <picker mode="selector" :range="resolutionOptions" :value="resolutionIndex" @change="onResolutionChange">
                  <view class="digital__row">
                    <text class="digital__row-label">清晰度</text>
                    <view class="digital__row-value">
                      <text>{{ resolution || '系统默认' }}</text>
                      <AppIcon name="chevron-down" :size="16" color="#6B6357" />
                    </view>
                  </view>
                </picker>

                <!-- 背景场景：后端 background 只接受真实上传的图片地址，故不提供设计稿的三张渐变示意色块 -->
                <view class="digital__row" role="button" @click="pickBackground" tabindex="0" @keydown.enter.stop.prevent="pickBackground" @keydown.space.stop.prevent="pickBackground">
                  <text class="digital__row-label">背景场景</text>
                  <view class="digital__row-value">
                    <text>{{ background ? '已上传' : '数字人默认' }}</text>
                    <AppIcon name="chevron-right" :size="16" color="#6B6357" />
                  </view>
                </view>

                <!-- 带货商品图 -->
                <view class="digital__row" role="button" @click="pickGoods" tabindex="0" @keydown.enter.stop.prevent="pickGoods" @keydown.space.stop.prevent="pickGoods">
                  <text class="digital__row-label">带货商品图</text>
                  <view class="digital__row-value">
                    <text>{{ goods ? '已上传' : '不使用' }}</text>
                    <AppIcon name="chevron-right" :size="16" color="#6B6357" />
                  </view>
                </view>
              </view>
            </view>
          </view>

          <!-- 开始生成 -->
          <view
            class="digital__submit app-btn-brand"
            :class="{ 'digital__submit--loading': submitting }"
            role="button"
            aria-label="开始生成"
            @click="generate"
           tabindex="0" @keydown.enter.stop.prevent="generate" @keydown.space.stop.prevent="generate" :aria-busy="submitting" :aria-disabled="submitting">
            <AppIcon name="play" :size="20" color="#FFFFFF" />
            <text>{{ submitting ? '提交中…' : '开始生成' }}</text>
          </view>
          <text class="digital__hint">{{ estimateHint }}</text>
          <ToolCost ref="toolCost" :params="{ type: 'digital', duration: Number(duration) || 8 }" />
        </scroll-view>
      </view>
    </view>

    <AppTabBar active="create" />
  </view>
</template>

<script setup>
import { showAppModal, showAppActionSheet } from '@/utils/feedback'
import { computed, onMounted, ref, watch } from 'vue'
import { onUnload } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import AppTextarea from '@/components/AppTextarea.vue'
import ToolCost from '@/components/ToolCost.vue'

const toolCost = ref(null)
import AppTabBar from '@/components/AppTabBar.vue'
import AppEmpty from '@/components/AppEmpty.vue'
import api from '@/api'
import { useUserStore } from '@/store/modules/user'
import { useGenConfig } from '@/composables/useGenConfig'
import { currentPagePath, go, toLoginPath } from '@/utils/navigation'
import { getNavBarMetrics } from '@/utils/system'
import { uploadMedia } from '@/utils/upload'

/**
 * 数字人口播（对应设计稿《数字人口播》）。
 *
 * 设计稿里的形象照片、音色名、背景色块都是示意数据，这里一律换成后端真实字段：
 * 平台形象走 /v1/digital/list，我的形象走 /v1/digital/personal/list；
 * 音色复用桌面端 constants/doubaoVoices.js 的豆包官方音色清单（不虚构音色名）；
 * 预估消耗与耗时来自 /v1/task/estimate，绝不写死数字。
 */

const userStore = useUserStore()
const { loadGenConfig, digitalModel } = useGenConfig()

/** 导航栏总高：状态栏 + 标题栏（小程序标题栏高度跟随胶囊按钮，见 utils/system） */
const navBarMetrics = getNavBarMetrics()
const navBarHeight = computed(() => navBarMetrics.statusBarHeight + navBarMetrics.barHeight)

/**
 * 音色清单：直接复用豆包语音合成 2.0 官方音色（火山引擎《音色列表--豆包语音》）；
 * 设计稿里的「小雅 / 小柔」是示意名，不能据此虚构音色，故一律使用官方中文名。
 */
const VOICE_OPTIONS = [
  { label: 'Vivi', value: 'zh_female_vv_uranus_bigtts' },
  { label: '小何', value: 'zh_female_xiaohe_uranus_bigtts' },
  { label: '魅力苏菲', value: 'zh_female_sophie_uranus_bigtts' },
  { label: '清新女声', value: 'zh_female_qingxinnvsheng_uranus_bigtts' },
  { label: '甜美小源', value: 'zh_female_tianmeixiaoyuan_uranus_bigtts' },
  { label: '甜美桃子', value: 'zh_female_tianmeitaozi_uranus_bigtts' },
  { label: '爽快思思', value: 'zh_female_shuangkuaisisi_uranus_bigtts' },
  { label: '邻家女孩', value: 'zh_female_linjianvhai_uranus_bigtts' },
  { label: '温柔妈妈', value: 'zh_female_wenroumama_uranus_bigtts' },
  { label: 'TVB女声', value: 'zh_female_tvbnv_uranus_bigtts' },
  { label: '俏皮女声', value: 'zh_female_qiaopinv_uranus_bigtts' },
  { label: '婆婆', value: 'zh_female_popo_uranus_bigtts' },
  { label: '高冷御姐', value: 'zh_female_gaolengyujie_uranus_bigtts' },
  { label: '温柔淑女', value: 'zh_female_wenroushunv_uranus_bigtts' },
  { label: '萌丫头', value: 'zh_female_mengyatou_uranus_bigtts' },
  { label: '贴心女声', value: 'zh_female_tiexinnvsheng_uranus_bigtts' },
  { label: '鸡汤妹妹', value: 'zh_female_jitangmei_uranus_bigtts' },
  { label: '开朗姐姐', value: 'zh_female_kailangjiejie_uranus_bigtts' },
  { label: '娇喘女声', value: 'zh_female_jiaochuannv_uranus_bigtts' },
  { label: '亲切女声', value: 'zh_female_qinqienv_uranus_bigtts' },
  { label: '文静毛毛', value: 'zh_female_wenjingmaomao_uranus_bigtts' },
  { label: '知性女声', value: 'zh_female_zhixingnv_uranus_bigtts' },
  { label: '清澈梓梓', value: 'zh_female_qingchezizi_uranus_bigtts' },
  { label: '甜美悦悦', value: 'zh_female_tianmeiyueyue_uranus_bigtts' },
  { label: '心灵鸡汤', value: 'zh_female_xinlingjitang_uranus_bigtts' },
  { label: '柔美女友', value: 'zh_female_roumeinvyou_uranus_bigtts' },
  { label: '温柔小雅', value: 'zh_female_wenrouxiaoya_uranus_bigtts' },
  { label: '魅力女友', value: 'zh_female_meilinvyou_uranus_bigtts' },
  { label: '谄媚女声', value: 'zh_female_chanmeinv_uranus_bigtts' },
  { label: '知性灿灿', value: 'zh_female_cancan_uranus_bigtts' },
  { label: '撒娇学妹', value: 'zh_female_sajiaoxuemei_uranus_bigtts' },
  { label: '直率英子', value: 'zh_female_zhishuaiyingzi_uranus_bigtts' },
  { label: '樱桃丸子', value: 'zh_female_yingtaowanzi_uranus_bigtts' },
  { label: '古风少御', value: 'zh_female_gufengshaoyu_uranus_bigtts' },
  { label: '林潇', value: 'zh_female_linxiao_uranus_bigtts' },
  { label: '玲玲姐姐', value: 'zh_female_lingling_uranus_bigtts' },
  { label: '春日部姐姐', value: 'zh_female_chunribu_uranus_bigtts' },
  { label: '感冒电音姐姐', value: 'zh_female_ganmaodianyin_uranus_bigtts' },
  { label: '女雷神', value: 'zh_female_nvleishen_uranus_bigtts' },
  { label: '武则天', value: 'zh_female_wuzetian_uranus_bigtts' },
  { label: '顾姐', value: 'zh_female_gujie_uranus_bigtts' },
  { label: '佩奇猪', value: 'zh_female_peiqi_uranus_bigtts' },
  { label: '黑猫侦探社咪仔', value: 'zh_female_mizai_uranus_bigtts' },
  { label: '鸡汤女', value: 'zh_female_jitangnv_uranus_bigtts' },
  { label: '流畅女声', value: 'zh_female_liuchangnvsheng_uranus_bigtts' },
  { label: '儿童绘本', value: 'zh_female_xiaoxue_uranus_bigtts' },
  { label: '少儿故事', value: 'zh_female_shaoergushi_uranus_bigtts' },
  { label: 'Tina老师', value: 'zh_female_yingyujiaoxue_uranus_bigtts' },
  { label: '暖阳女声', value: 'zh_female_kefunvsheng_uranus_bigtts' },
  { label: '云舟', value: 'zh_male_m191_uranus_bigtts' },
  { label: '小天', value: 'zh_male_taocheng_uranus_bigtts' },
  { label: '刘飞', value: 'zh_male_liufei_uranus_bigtts' },
  { label: '少年梓辛', value: 'zh_male_shaonianzixin_uranus_bigtts' },
  { label: '解说小明', value: 'zh_male_jieshuoxiaoming_uranus_bigtts' },
  { label: '译制片男', value: 'zh_male_yizhipiannan_uranus_bigtts' },
  { label: '邻家男孩', value: 'zh_male_linjiananhai_uranus_bigtts' },
  { label: '儒雅青年', value: 'zh_male_ruyaqingnian_uranus_bigtts' },
  { label: '温暖阿虎', value: 'zh_male_wennuanahu_uranus_bigtts' },
  { label: '奶气萌娃', value: 'zh_male_naiqimengwa_uranus_bigtts' },
  { label: '傲娇霸总', value: 'zh_male_aojiaobazong_uranus_bigtts' },
  { label: '反卷青年', value: 'zh_male_fanjuanqingnian_uranus_bigtts' },
  { label: '活力小哥', value: 'zh_male_huolixiaoge_uranus_bigtts' },
  { label: '磁性解说男声', value: 'zh_male_cixingjieshuonan_uranus_bigtts' },
  { label: '亮嗓萌仔', value: 'zh_male_liangsangmengzai_uranus_bigtts' },
  { label: '高冷沉稳', value: 'zh_male_gaolengchenwen_uranus_bigtts' },
  { label: '深夜播客', value: 'zh_male_shenyeboke_uranus_bigtts' },
  { label: '快乐小东', value: 'zh_male_kuailexiaodong_uranus_bigtts' },
  { label: '开朗学长', value: 'zh_male_kailangxuezhang_uranus_bigtts' },
  { label: '悠悠君子', value: 'zh_male_youyoujunzi_uranus_bigtts' },
  { label: '清爽男大', value: 'zh_male_qingshuangnanda_uranus_bigtts' },
  { label: '渊博小叔', value: 'zh_male_yuanboxiaoshu_uranus_bigtts' },
  { label: '阳光青年', value: 'zh_male_yangguangqingnian_uranus_bigtts' },
  { label: '温柔小哥', value: 'zh_male_wenrouxiaoge_uranus_bigtts' },
  { label: '东方浩然', value: 'zh_male_dongfanghaoran_uranus_bigtts' },
  { label: '天才童声', value: 'zh_male_tiancaitongsheng_uranus_bigtts' },
  { label: '广告解说', value: 'zh_male_guanggaojieshuo_uranus_bigtts' },
  { label: '开朗弟弟', value: 'zh_male_kailangdidi_uranus_bigtts' },
  { label: '四郎', value: 'zh_male_silang_uranus_bigtts' },
  { label: '擎苍', value: 'zh_male_qingcang_uranus_bigtts' },
  { label: '熊二', value: 'zh_male_xionger_uranus_bigtts' },
  { label: '懒音绵宝', value: 'zh_male_lanyinmianbao_uranus_bigtts' },
  { label: '鲁班七号', value: 'zh_male_lubanqihao_uranus_bigtts' },
  { label: '猴哥', value: 'zh_male_sunwukong_uranus_bigtts' },
  { label: '大壹', value: 'zh_male_dayi_uranus_bigtts' },
  { label: '儒雅逸辰', value: 'zh_male_ruyayichen_uranus_bigtts' },
  { label: '霸气青叔', value: 'zh_male_baqiqingshu_uranus_bigtts' },
  { label: '悬疑解说', value: 'zh_male_xuanyijieshuo_uranus_bigtts' },
  { label: '调皮公主', value: 'saturn_zh_female_tiaopigongzhu_tob' },
  { label: '爽朗少年', value: 'saturn_zh_male_shuanglangshaonian_tob' },
  { label: '天才同桌', value: 'saturn_zh_male_tiancaitongzhuo_tob' },
  { label: '知性灿灿（风格化）', value: 'saturn_zh_female_cancan_tob' },
  { label: '傲娇女友', value: 'saturn_zh_female_aojiaonvyou_tob' },
  { label: '病娇姐姐', value: 'saturn_zh_female_bingjiaojiejie_tob' },
  { label: '成熟姐姐', value: 'saturn_zh_female_chengshujiejie_tob' },
  { label: '可爱女生', value: 'saturn_zh_female_keainvsheng_tob' },
  { label: '暖心学姐', value: 'saturn_zh_female_nuanxinxuejie_tob' },
  { label: '贴心女友', value: 'saturn_zh_female_tiexinnvyou_tob' },
  { label: '妩媚御姐', value: 'saturn_zh_female_wumeiyujie_tob' },
  { label: '性感御姐', value: 'saturn_zh_female_xingganyujie_tob' },
  { label: '傲气凌人', value: 'saturn_zh_male_aiqilingren_tob' },
  { label: '傲娇公子', value: 'saturn_zh_male_aojiaogongzi_tob' },
  { label: '傲娇精英', value: 'saturn_zh_male_aojiaojingying_tob' },
  { label: '傲慢少爷', value: 'saturn_zh_male_aomanshaoye_tob' },
  { label: '霸道少爷', value: 'saturn_zh_male_badaoshaoye_tob' },
  { label: '病娇白莲', value: 'saturn_zh_male_bingjiaobailian_tob' },
  { label: '不羁青年', value: 'saturn_zh_male_bujiqingnian_tob' },
  { label: '成熟总裁', value: 'saturn_zh_male_chengshuzongcai_tob' },
  { label: '磁性男嗓', value: 'saturn_zh_male_cixingnansang_tob' },
  { label: '醋精男友', value: 'saturn_zh_male_cujingnanyou_tob' },
  { label: '风发少年', value: 'saturn_zh_male_fengfashaonian_tob' },
  { label: '腹黑公子', value: 'saturn_zh_male_fuheigongzi_tob' },
  { label: '轻盈朵朵', value: 'saturn_zh_female_qingyingduoduo_cs_tob' },
  { label: '温婉珊珊', value: 'saturn_zh_female_wenwanshanshan_cs_tob' },
  { label: '热情艾娜', value: 'saturn_zh_female_reqingaina_cs_tob' },
  { label: '清新沐沐', value: 'saturn_zh_male_qingxinmumu_cs_tob' },
  { label: '温柔文雅', value: 'saturn_zh_female_wenrouwenya_tob' },
  { label: 'Tim（男）', value: 'en_male_tim_uranus_bigtts' },
  { label: 'Dacey（女）', value: 'en_female_dacey_uranus_bigtts' },
  { label: 'Stokie（女）', value: 'en_female_stokie_uranus_bigtts' },
]
const voiceLabels = VOICE_OPTIONS.map((o) => o.label)

const tab = ref('platform')
const platformList = ref([])
const platformLoading = ref(false)
// 区分请求失败与真实空列表，为弱网提供明确的恢复入口。
const platformError = ref('')
const mineList = ref([])
const mineLoading = ref(false)
const mineError = ref('')

const sheetVisible = ref(false)
const active = ref(null)
const moreOpen = ref(false)
const submitting = ref(false)
const polishing = ref(false)

const scriptText = ref('')
const voiceValue = ref('')
const voicePreviewLoading = ref(false)
const voicePreviewPlaying = ref(false)
let voiceAudio = null
let voicePreviewSeq = 0
const speed = ref(1.0)
const duration = ref(8)
const ratio = ref('')
const resolution = ref('')
const background = ref('')
const goods = ref('')

const estimate = ref(null)
let estimateTimer = null
let estimateSeq = 0
/** 润色轮询计时器：离开页面时必须清理，避免后台持续请求 */
const pollTimers = []

const scriptCount = computed(() => scriptText.value.length)
/** 语速展示统一保留一位小数（1.0x / 1.5x …） */
const speedText = computed(() => Number(speed.value).toFixed(1))
const voiceIndex = computed(() => {
  const idx = VOICE_OPTIONS.findIndex((o) => o.value === voiceValue.value)
  return idx < 0 ? 0 : idx
})
const voiceLabel = computed(() => VOICE_OPTIONS[voiceIndex.value]?.label || '选择音色')

const durationOptions = computed(() => estimate.value?.options?.durations || [])
const ratioOptions = computed(() => estimate.value?.options?.ratios || [])
const resolutionOptions = computed(() => estimate.value?.options?.resolutions || [])
const resolutionIndex = computed(() => {
  const idx = resolutionOptions.value.indexOf(resolution.value)
  return idx < 0 ? 0 : idx
})

/** 预估提示：拿不到后端结果时只展示占位符，绝不编造消耗数字 */
const estimateHint = computed(() => {
  // 耗时未知时明确说明随排队变化，不根据费用推算或编造时间。
  const seconds = Number(estimate.value?.estimate_seconds)
  if (!Number.isFinite(seconds) || seconds <= 0) return '生成用时随任务排队情况变化'
  return `预计用时约 ${Math.max(1, Math.round(seconds / 60))} 分钟`
})

function toast(title) {
  uni.showToast({ title, icon: 'none' })
}

/** 卡片封面：平台形象用 avatar，我的形象优先 image，缺失时页面渲染渐变兜底 */
function coverOf(item) {
  return String(item?.image || item?.avatar || '').trim()
}

/** 角标签由真实字段拼装：性别决定配色，性别 + 风格决定文案，都没有则不渲染 */
function tagOf(item) {
  const gender = String(item?.gender || '').trim()
  const style = String(item?.style || '').trim()
  const genderWord = gender === '男' ? '男声' : gender === '女' ? '女声' : gender
  const text = [genderWord, style].filter(Boolean).join('·')
  return { text, cls: gender === '女' ? 'digital__tag--female' : 'digital__tag--male' }
}

function requireLogin() {
  if (userStore.isLoggedIn) return true
  go(toLoginPath(currentPagePath()))
  return false
}

function goLogin() {
  go(toLoginPath(currentPagePath()))
}

/** 加载平台形象，失败保留可重试说明，避免被误认为暂无形象。 */
async function loadPlatform() {
  platformLoading.value = true
  platformError.value = ''
  try {
    const res = await api.digital.list.post(
      { pageNum: 1, pageSize: 20 },
      { suppressGlobalError: true }
    )
    if (res?.code !== 1 || !Array.isArray(res.data)) throw new Error(res?.message || '暂时无法读取形象，请稍后重试')
    platformList.value = res.data
  } catch (err) {
    console.error('加载平台数字人形象失败', err)
    platformList.value = []
    platformError.value = err?.message || '请检查网络后重试'
  } finally {
    platformLoading.value = false
  }
}

/** 登录后读取个人形象，错误反馈与上传入口保持各自可用。 */
async function loadMine() {
  if (!userStore.isLoggedIn) {
    mineList.value = []
    return
  }
  mineLoading.value = true
  mineError.value = ''
  try {
    const res = await api.digital.personalList.post({}, { suppressGlobalError: true })
    if (res?.code !== 1 || !Array.isArray(res.data)) throw new Error(res?.message || '暂时无法读取我的形象')
    mineList.value = res.data
  } catch (err) {
    console.error('加载我的专属数字人失败', err)
    mineList.value = []
    mineError.value = err?.message || '请检查网络后重试'
  } finally {
    mineLoading.value = false
  }
}

function switchToMine() {
  tab.value = 'mine'
  if (userStore.isLoggedIn) loadMine()
}

function openSheet(item) {
  if (!item) return
  active.value = item
  sheetVisible.value = true
  scheduleEstimate()
  syncDurationDefault()
}

function closeSheet() {
  sheetVisible.value = false
}

/** 上传形象 → 转推绝对地址 → 命名 → 创建专属数字人（需登录） */
function createPersonalAvatar() {
  if (!requireLogin()) return
  uni.chooseImage({
    count: 1,
    success: async (res) => {
      const path = res.tempFilePaths && res.tempFilePaths[0]
      if (!path) return
      let uploaded = null
      try {
        uploaded = await uploadMedia(path, {
          onProgress: (percent) => toast(`上传中 ${percent}%`),
        })
      } catch (err) {
        console.error('上传形象图片失败', err)
        toast(err?.message || '上传失败，请稍后重试')
        return
      }
      showAppModal({
        title: '形象名称',
        editable: true,
        placeholderText: '给这个形象起个名字',
        success: async (modal) => {
          const name = String(modal.content || '').trim()
          // 未填名称或点了取消都视为放弃，不再调用创建接口
          if (!modal.confirm || !name) {
            toast('已取消上传')
            return
          }
          try {
            const created = await api.digital.personalCreate.post(
              { name, image: uploaded.url, gender: '女', device: 'mobile' },
              { suppressGlobalError: true }
            )
            if (!created || created.code !== 1) {
              toast(created?.message || '创建失败，请稍后重试')
              return
            }
            uni.showToast({ title: '形象已创建', icon: 'none' })
            tab.value = 'mine'
            await loadMine()
          } catch (err) {
            console.error('创建专属数字人失败', err)
            toast(err?.data?.message || err?.message || '创建失败，请稍后重试')
          }
        },
      })
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择形象图片失败', err)
    },
  })
}

function onSpeedChange(e) {
  speed.value = Number(e.detail.value)
}

function onVoiceChange(e) {
  const picked = VOICE_OPTIONS[Number(e.detail.value)]
  if (picked) {
    stopVoicePreview()
    voiceValue.value = picked.value
  }
}

function stopVoicePreview() {
  voicePreviewSeq += 1
  voicePreviewLoading.value = false
  voicePreviewPlaying.value = false
  if (voiceAudio) {
    voiceAudio.stop()
    voiceAudio.destroy()
    voiceAudio = null
  }
}

function findAudioUrl(node) {
  if (!node) return ''
  if (typeof node === 'string') return /^https?:\/\//.test(node) && /\.(mp3|wav|m4a|aac)(\?|$)/i.test(node) ? node : ''
  if (Array.isArray(node)) {
    for (const item of node) {
      const found = findAudioUrl(item)
      if (found) return found
    }
    return ''
  }
  if (typeof node === 'object') {
    for (const key of ['audio_url', 'audio', 'url']) {
      const found = findAudioUrl(node[key])
      if (found) return found
    }
    return findAudioUrl(node.content) || findAudioUrl(node.result)
  }
  return ''
}

/** 登录后生成音色试听，避免匿名调用语音服务。 */
async function toggleVoicePreview() {
  if (!requireLogin()) return
  if (voicePreviewLoading.value || voicePreviewPlaying.value) {
    stopVoicePreview()
    return
  }
  const selected = VOICE_OPTIONS[voiceIndex.value]
  if (!selected) return
  const seq = ++voicePreviewSeq
  voicePreviewLoading.value = true
  try {
    const created = await api.content.voice.post({
      text: '你好，这是一段音色试听。',
      voice: selected.value,
    }, { suppressGlobalError: true })
    const taskId = created?.code === 1 ? created.data?.task_id : null
    if (!taskId) throw new Error(created?.message || '试听任务创建失败')
    const startedAt = Date.now()
    let audioUrl = ''
    while (Date.now() - startedAt < 60000 && seq === voicePreviewSeq) {
      await new Promise((resolve) => setTimeout(resolve, 1500))
      const result = await api.content.result.post(
        { task_id: taskId },
        { suppressGlobalError: true }
      )
      const data = result?.code === 1 ? result.data : null
      if (data?.status === 'done') {
        audioUrl = findAudioUrl(data.result)
        break
      }
    }
    if (!audioUrl) throw new Error('试听音频生成超时')
    if (seq !== voicePreviewSeq) return
    voiceAudio = uni.createInnerAudioContext()
    voiceAudio.src = audioUrl
    voiceAudio.onPlay(() => { voicePreviewPlaying.value = true })
    voiceAudio.onEnded(stopVoicePreview)
    voiceAudio.onStop(stopVoicePreview)
    voiceAudio.onError(() => {
      stopVoicePreview()
      toast('试听播放失败，请稍后重试')
    })
    voiceAudio.play()
  } catch (err) {
    if (seq === voicePreviewSeq) toast(err?.message || '试听失败，请稍后重试')
  } finally {
    if (seq === voicePreviewSeq) voicePreviewLoading.value = false
  }
}

function selectDuration(value) {
  duration.value = Number(value)
}

function onResolutionChange(e) {
  const picked = resolutionOptions.value[Number(e.detail.value)]
  if (picked) resolution.value = picked
}

function pickRatio() {
  if (!ratioOptions.value.length) {
    toast('选项加载中，请稍后重试')
    return
  }
  showAppActionSheet({
    itemList: ratioOptions.value,
    success: ({ tapIndex }) => {
      const picked = ratioOptions.value[tapIndex]
      if (picked) ratio.value = picked
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择画幅比例失败', err)
    },
  })
}

/** 选图片并上传，返回可透传的绝对地址；上传进度用轻提示反馈 */
function pickImageAndUpload() {
  return new Promise((resolve) => {
    uni.chooseImage({
      count: 1,
      success: async (res) => {
        const path = res.tempFilePaths && res.tempFilePaths[0]
        if (!path) {
          resolve('')
          return
        }
        try {
          const data = await uploadMedia(path, {
            onProgress: (percent) => toast(`上传中 ${percent}%`),
          })
          resolve(data.url || '')
        } catch (err) {
          console.error('上传图片失败', err)
          toast(err?.message || '上传失败，请稍后重试')
          resolve('')
        }
      },
      fail: (err) => {
        if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择图片失败', err)
        resolve('')
      },
    })
  })
}

function pickBackground() {
  showAppActionSheet({
    itemList: ['使用默认场景', '上传背景图'],
    success: async ({ tapIndex }) => {
      if (tapIndex === 0) {
        background.value = ''
        return
      }
      const url = await pickImageAndUpload()
      if (url) background.value = url
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('背景场景操作失败', err)
    },
  })
}

function pickGoods() {
  showAppActionSheet({
    itemList: ['不使用', '上传商品图'],
    success: async ({ tapIndex }) => {
      if (tapIndex === 0) {
        goods.value = ''
        return
      }
      const url = await pickImageAndUpload()
      if (url) goods.value = url
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('带货商品图操作失败', err)
    },
  })
}

// ---------- 预估 ----------

async function runEstimate() {
  const seq = ++estimateSeq
  try {
    const res = await api.task.estimate.post(
      { type: 'digital', duration: Number(duration.value) || 8 },
      { suppressGlobalError: true }
    )
    if (seq !== estimateSeq) return
    estimate.value = res && res.code === 1 && res.data ? res.data : null
    if (estimate.value) syncDurationDefault()
  } catch (err) {
    console.error('预估数字人消耗失败', err)
    if (seq === estimateSeq) estimate.value = null
  }
}

/** 时长档位与后端白名单保持一致：当前值不在档位内时吸附到最接近 8 秒的档 */
function syncDurationDefault() {
  const opts = durationOptions.value
  if (!opts.length) return
  if (opts.some((d) => Number(d) === Number(duration.value))) return
  duration.value = opts.reduce(
    (a, b) => (Math.abs(Number(b) - 8) < Math.abs(Number(a) - 8) ? b : a),
    opts[0]
  )
}

/** 输入变化后防抖预估，避免连续点选时打出一串请求 */
function scheduleEstimate() {
  if (estimateTimer) clearTimeout(estimateTimer)
  estimateTimer = setTimeout(runEstimate, 300)
}

watch(duration, () => {
  if (sheetVisible.value) scheduleEstimate()
})

// ---------- AI 润色（真实异步接口 + 轮询） ----------

function pollRewrite(taskId) {
  return new Promise((resolve) => {
    const startedAt = Date.now()
    const timer = setInterval(async () => {
      if (Date.now() - startedAt > 90000) {
        clearInterval(timer)
        resolve(null)
        return
      }
      try {
        const res = await api.content.result.post(
          { task_id: taskId },
          { suppressGlobalError: true }
        )
        const data = res && res.code === 1 ? res.data : null
        if (data && data.status === 'done') {
          clearInterval(timer)
          // rewrite 产物 content 为对象 {rewritten,...}，兼容直接字符串形态
          const content = (data.result?.content?.rewritten ?? data.result?.content ?? '').trim()
          resolve(content || null)
        }
      } catch (err) {
        console.error('轮询润色结果失败', err)
      }
    }, 2000)
    pollTimers.push(timer)
  })
}

/** 登录后执行文案润色，游客不调用模型。 */
async function polishScript() {
  if (!requireLogin() || polishing.value) return
  const text = scriptText.value.trim()
  if (!text) {
    toast('请先输入口播文案')
    return
  }
  polishing.value = true
  try {
    const res = await api.content.rewrite.post(
      { text, level: 2, tone: 'natural', max_chars: 0 },
      { suppressGlobalError: true }
    )
    const taskId = res && res.code === 1 ? res.data?.task_id : null
    if (!taskId) {
      toast(res?.message || '润色失败，请重试')
      return
    }
    const content = await pollRewrite(taskId)
    if (content === null) {
      toast('润色超时，请重试')
      return
    }
    scriptText.value = content
  } catch (err) {
    console.error('AI 润色失败', err)
    toast(err?.data?.message || err?.message || '润色失败，请重试')
  } finally {
    polishing.value = false
  }
}

// ---------- 提交 ----------

async function generate() {
  if (submitting.value) return
  if (!active.value) {
    toast('请先选择形象')
    return
  }
  if (!scriptText.value.trim()) {
    toast('请输入口播文案')
    return
  }
  // 后端未接入数字人模型时保持页面可用，仅在提交时明确告知能力未开通
  if (!digitalModel.value) {
    toast('数字人能力暂未开通')
    return
  }
  if (!requireLogin()) return

  submitting.value = true
  try {
    if (!await toolCost.value?.ensure()) return
    const payload = {
      digital_id: active.value.id,
      text: scriptText.value.trim(),
      voice: voiceValue.value,
      speed: Number(speed.value),
      duration: Number(duration.value) || 8,
      device: 'mobile',
    }
    if (ratio.value) payload.ratio = ratio.value
    if (resolution.value) payload.resolution = resolution.value
    if (background.value) payload.background = background.value
    if (goods.value) payload.goods = goods.value

    const res = await api.task.digitalCreate.post(payload, { suppressGlobalError: true })
    if (!res || res.code !== 1) {
      toast(res?.message || '提交失败，请稍后重试')
      return
    }
    await toolCost.value?.refresh()
    toast('已提交生成')
    closeSheet()
    go('/pages/works/index')
  } catch (err) {
    console.error('创建数字人口播任务失败', err)
    toast(err?.data?.message || err?.message || '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

// ---------- 生命周期 ----------

onMounted(async () => {
  voiceValue.value = VOICE_OPTIONS[0].value
  await loadGenConfig()
  loadPlatform()
  if (userStore.isLoggedIn) loadMine()
  scheduleEstimate()
})

onUnload(() => {
  stopVoicePreview()
  if (estimateTimer) clearTimeout(estimateTimer)
  pollTimers.forEach((timer) => clearInterval(timer))
  pollTimers.length = 0
})
</script>

<style lang="scss" scoped>
/* ============ 顶部「上传」按钮（品牌柔色虚线） ============ */
.digital__upload {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 10px 12px;
  min-height: 44px;
  border: 1px solid rgba(178, 58, 46, 0.6);
  border-radius: var(--radius-full);
  background: var(--brand-primary-light);
  color: var(--brand-primary);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 1px;

  &:active {
    background: #eee1cc;
  }
}

/* ============ 平台形象 / 我的形象 切换 ============ */
.digital__tabs {
  position: sticky;
  z-index: var(--z-header);
  display: flex;
  gap: 4px;
  margin: 0 20px 18px;
  padding: 4px;
  background: var(--paper-100);
  border: 1px solid rgba(74, 69, 61, 0.12);
  border-radius: var(--radius-full);
  box-shadow: 0 2px 8px rgba(67, 57, 44, 0.05);
}

.digital__tab {
  flex: 1;
  padding: 8px 0;
  text-align: center;
  font-size: 13px;
  color: var(--ink-500);
  border-radius: var(--radius-full);
  position: relative;
  letter-spacing: 1px;
  transition: background-color var(--transition-fast), color var(--transition-fast);
  min-height: 44px;

  &--active {
    color: var(--brand-primary);
    font-weight: 600;
    background: var(--paper-card);
    box-shadow: 0 1px 4px rgba(67, 57, 44, 0.08);
  }

  &--active::after {
    display: none;
  }
}

/* ============ 形象网格 ============ */
.digital__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 12px;
  padding: 4px var(--page-gutter) 28px;
}

.digital__card {
  position: relative;
  background: var(--paper-card);
  border-radius: 24px;
  box-shadow: var(--shadow-sm);
  border: 5px solid var(--paper-100);
  overflow: hidden;
  transition: transform var(--transition-base), box-shadow var(--transition-base);

  &:active {
    transform: translateY(1px);
    box-shadow: 0 1px 6px rgba(67, 57, 44, 0.08);
  }

  &--upload {
    position: relative;
    padding-top: 133.3333%;
    background: #fcfaf4;
    border: 1px dashed rgba(178, 58, 46, 0.42);
    color: var(--brand-primary);
  }
}

.digital__cover {
  position: relative;
  /* 3:4 撑高：不用 aspect-ratio，旧版小程序内核不支持会塌陷；原 4px 内边距改由图片 inset 表达 */
  padding-top: 133.3333%;
  background: #f1ecdf;
  overflow: hidden;

  &--skeleton {
    background: #eee8dc;
  }
}

.digital__cover .digital__img {
  background: #f7f3eb;
}

.digital__card:not(.digital__card--upload)::after {
  content: '';
  position: absolute;
  inset: 4px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 15px;
  pointer-events: none;
}

.digital__img {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc(100% - 8px);
  height: calc(100% - 8px);
  display: block;
  border-radius: 14px;

  &--empty {
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--paper-100);
  }
}

.digital__card .digital__img {
  filter: saturate(0.82) contrast(0.96);
}

/* 无封面时占位图标降到 40% 不透明度，避免抢占视觉 */
.digital__ph-icon {
  opacity: 0.4;
}

.digital__tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 7px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  background: rgba(248, 244, 235, 0.9);
  max-width: calc(100% - 16px);
  white-space: normal;
  overflow-wrap: anywhere;
}

.digital__cover .digital__tag {
  position: absolute;
  top: 8px;
  left: 8px;
}

.digital__tag--female {
  background: linear-gradient(135deg, rgba(138, 90, 59, 0.1), rgba(138, 90, 59, 0.1));
  color: var(--brand-secondary);
}

.digital__tag--male {
  background: linear-gradient(135deg, rgba(178, 58, 46, 0.1), rgba(62, 107, 122, 0.1));
  color: var(--brand-primary);
}

.digital__body {
  padding: 12px 12px 14px;
  background: var(--paper-card);
}

.digital__name {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #34332f;
  margin-bottom: 10px;
  letter-spacing: 0.5px;
}

.digital__select {
  width: 100%;
  padding: 10px 0;
  text-align: center;
  border-radius: var(--radius-full);
  background: var(--brand-primary);
  color: #fffaf0;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 1px;
  box-shadow: none;

  min-height: 44px;

  &:active {
    transform: translateY(1px);
    background: #8f2f26;
  }
}

.digital__upload-content {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.digital__upload-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.digital__upload-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--brand-primary);
}

.digital__upload-sub {
  font-size: 11px;
  color: var(--text-muted);
}

/* 骨架屏 */
.digital__card--skeleton {
  pointer-events: none;
}

.digital__skel-line {
  height: 12px;
  border-radius: 6px;
  background: var(--paper-200);
  animation: app-breathe 1.8s var(--ease-out) infinite;
}

.digital__skel-btn {
  height: 44px;
  border-radius: var(--radius-full);
  background: var(--paper-200);
  margin-top: 10px;
}

.digital__login-tip {
  margin: 0 16px 16px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--brand-primary-light);
  border: 1px solid rgba(178, 58, 46, 0.15);
  font-size: 13px;
  color: var(--brand-primary);
  text-align: center;
}

.digital__loading-text {
  display: block;
  padding: 0 16px 16px;
  font-size: 13px;
  color: var(--text-tertiary);
}

/* ============ 底部提示条 ============ */
.digital__tip {
  position: sticky;
  bottom: calc(var(--nav-h) + constant(safe-area-inset-bottom));
  bottom: calc(var(--nav-h) + env(safe-area-inset-bottom));
  z-index: var(--z-action);
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 var(--page-gutter) 12px;
  padding: 11px 14px;
  background: rgba(255, 253, 249, 0.96);
  border: 5px solid var(--paper-100);
  border-radius: 22px;
  box-shadow: 0 3px 12px rgba(68, 59, 47, 0.07);
}

.digital__tip-icon {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 10px;
  background: var(--brand-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.digital__tip-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.digital__tip-title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #37352f;
}

.digital__tip-sub {
  font-size: 12px;
  color: #756d62;
}

/* 关闭入口保持 44px 触控区，与滚动表单分离，长表单仍可随时退出。 */
.digital__sheet-close { position: absolute; right: 6px; top: 4px; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--paper-100); }

/* ============ 底部弹层 ============ */
.digital__overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-overlay);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(37, 36, 31, 0.48);
}

.digital__sheet {
  width: 100%;
  max-width: var(--page-max);
  background: var(--paper-card);
  border: 6px solid var(--paper-100);
  border-bottom: none;
  border-radius: 28px 28px 0 0;
  max-height: 90vh;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-lg);
}

.digital__handle-wrap {
  position: relative;
  padding: 22px 0;
  min-height: 52px;
}

.digital__handle {
  width: 42px;
  height: 3px;
  border-radius: var(--radius-full);
  margin: 0 auto;
  background: rgba(72, 67, 59, 0.45);
}

.digital__sheet-body {
  max-height: calc(90vh - 58px);
  overscroll-behavior: contain;
  padding: 0 16px calc(24px + env(safe-area-inset-bottom));
}

.digital__preview {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.digital__preview-img {
  position: relative;
  width: 96px;
  height: 128px;
  flex-shrink: 0;
  padding: 4px;
  border-radius: 18px;
  overflow: hidden;
  background: var(--paper-100);
  border: 1px solid var(--line-1);
  box-shadow: var(--shadow-sm);
}

.digital__preview-meta {
  flex: 1;
  min-width: 0;
  padding-top: 4px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.digital__preview-name {
  max-width: 100%;
  font: 600 22px/1.5 var(--font-serif);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.digital__preview-desc {
  margin-top: 12px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-tertiary);
}

.digital__field {
  margin-bottom: 16px;
}

.digital__label {
  display: block;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #37352f;
  margin-bottom: 8px;
}

.digital__textarea {
  height: 112px;
  line-height: 1.6;
  background: var(--paper-50);
  border: 1px solid var(--line-1);
  border-radius: 14px;
}

.digital__counter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
}

.digital__counter {
  font-size: 12px;
  color: var(--text-muted);
}

.digital__polish {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 44px;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--brand-primary);
}

.digital__voice-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.digital__voice-row picker {
  flex: 1;
  min-width: 0;
}

.digital__preview-btn {
  flex-shrink: 0;
  height: 48px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--line-1);
  border-radius: var(--radius-full);
  color: #b23a2e;
  font-size: 12px;
  background: var(--brand-primary-light);
}

.digital__preview-btn--active {
  background: #f9e8e2;
}

.digital__select-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: var(--paper-50);
  border: 1px solid var(--line-1);
  border-radius: 14px;
  min-height: 48px;
}

.digital__select-text {
  flex: 1;
  min-width: 0;
}

/* ============ 更多设置（折叠） ============ */
.digital__more {
  margin-bottom: 20px;
  border-top: 1px solid rgba(75, 69, 60, 0.28);
  padding-top: 16px;
}

.digital__more-head {
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.digital__more-title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #37352f;
}

.digital__arrow--open {
  transform: rotate(180deg);
}

.digital__collapse {
  overflow: visible;
}

.digital__collapse-inner {
  padding-top: 16px;
}

.digital__setting {
  margin-bottom: 16px;
}

.digital__setting-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.digital__setting-label {
  font-size: 14px;
  color: var(--text-tertiary);
}

.digital__setting-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--brand-primary);
}

.digital__setting-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.digital__segment {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.digital__seg {
  flex: 1;
  padding: 8px 0;
  text-align: center;
  font-size: 13px;
  color: #756d62;
  background: var(--paper-50);
  border: 1px solid var(--line-1);
  border-radius: 12px;
  transition: all var(--transition-fast);

  min-height: 44px;

  &--active {
    color: var(--brand-primary);
    font-weight: 700;
    background: var(--brand-primary-light);
    border-color: var(--brand-primary);
  }
}

.digital__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid rgba(75, 69, 60, 0.2);

  &:last-child {
    border-bottom: none;
  }
}

.digital__row-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.digital__row-value {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-tertiary);
}

/* ============ 提交 ============ */
.digital__submit {
  height: 48px;
  border-radius: var(--radius-full);
  background: var(--brand-primary);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 2px;
  box-shadow: none;

  &--loading {
    opacity: 0.6;
  }
}

.digital__hint {
  display: block;
  margin-top: 8px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
