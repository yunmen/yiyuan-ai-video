<template>
  <view class="app-page render">
    <AppNavBar title="视频换口播" />

    <view class="render__body">
      <!-- ============ 上传视频 ============ -->
      <view class="render__card">
        <view class="render__head">
          <view class="render__title">
            <view class="render__bar" />
            <text>上传视频</text>
          </view>
          <text class="render__tag">热门</text>
        </view>

        <!-- 未上传：设计稿的虚线拖拽区 -->
        <view v-if="!video" class="render__zone" role="button" @click="chooseVideo">
          <template v-if="videoUploading">
            <text class="render__zone-pct">上传中 {{ videoProgress }}%</text>
          </template>
          <template v-else>
            <view class="render__zone-icon">
              <AppIcon name="video-camera" :size="28" color="#FFFFFF" />
            </view>
            <text class="render__zone-title">点击或拖拽上传视频</text>
            <text class="render__zone-hint">支持 MP4 / MOV / AVI · 最长 10 分钟</text>
            <view class="render__zone-btn"><text>选择文件</text></view>
          </template>
        </view>

        <!-- 已上传：真实 video 预览 + 真实文件名/大小 -->
        <view v-else class="render__preview">
          <view class="render__video">
            <video
              id="renderVideo"
              class="render__video-el"
              :src="video.localPath"
              :controls="true"
              :show-center-play-btn="false"
              object-fit="cover"
            />
            <view class="render__video-mask" />
            <view class="render__play" role="button" aria-label="播放预览" @click="togglePlay">
              <AppIcon name="play" :size="20" color="#B23A2E" />
            </view>
            <text class="render__badge">{{ durationBadge }}</text>
            <view class="render__reupload" role="button" @click="chooseVideo">
              <AppIcon name="rotate-cw" :size="12" color="#FFFFFF" :stroke-width="2.5" />
              <text>重新上传</text>
            </view>
          </view>

          <view class="render__file">
            <view class="render__file-left">
              <AppIcon name="check" :size="14" color="#4B7A5A" :stroke-width="2.5" />
              <text class="render__file-name app-truncate">{{ video.name }}</text>
            </view>
            <text class="render__file-meta">{{ fileMetaText }}</text>
          </view>
        </view>
      </view>

      <!-- ============ 口播文案 ============ -->
      <view class="render__card">
        <view class="render__head">
          <view class="render__title">
            <view class="render__bar" />
            <text>口播文案</text>
          </view>
          <view class="render__extract" role="button" @click="extractScript">
            <AppIcon name="sparkles" :size="12" color="#B23A2E" :stroke-width="2.5" />
            <text>{{ extracting ? '识别中…' : 'AI 提取' }}</text>
          </view>
        </view>

        <textarea
          v-model="prompt"
          class="app-field render__textarea"
          :maxlength="2000"
          placeholder="输入新的口播文案，AI 将自动匹配口型..."
          placeholder-class="app-placeholder"
        />
        <!-- 后端没有语速模型，无法由字数推算时长，故只展示真实字数（设计稿的「· 约 18 秒」为示意数据） -->
        <view class="render__counter-row">
          <text class="render__counter">已输入 {{ promptCount }} 字</text>
          <view class="render__polish" role="button" @click="polishScript">
            <AppIcon name="sparkles" :size="12" color="#B23A2E" :stroke-width="2.5" />
            <text>{{ polishing ? '润色中…' : 'AI 润色' }}</text>
          </view>
        </view>
      </view>

      <!-- ============ 功能选择 ============ -->
      <view class="render__card">
        <view class="render__head">
          <view class="render__title">
            <view class="render__bar" />
            <text>功能选择</text>
          </view>
        </view>

        <view class="render__chips">
          <view
            v-for="item in MODE_OPTIONS"
            :key="item.key"
            class="app-chip"
            :class="{ 'app-chip--active': mode === item.key }"
            role="button"
            @click="selectMode(item.key)"
          >
            <AppIcon :name="item.icon" :size="16" :color="mode === item.key ? '#B23A2E' : '#6B6357'" />
            <text>{{ item.label }}</text>
          </view>
        </view>

        <!--
          后端路线由字段组合派生（digital_id → 数字人 / scene → 换场景 / 都无 → 只换声），
          设计稿三个 chip 没有真实载荷，这里补上对应的「选择数字人」「上传目标场景」条件行。
        -->
        <view v-if="mode === 'digital'" class="render__row" role="button" @click="pickDigital">
          <text class="render__row-label">选择数字人</text>
          <view class="render__row-value">
            <text>{{ digitalName || '请选择' }}</text>
            <AppIcon name="chevron-right" :size="16" color="#6B6357" />
          </view>
        </view>

        <view v-if="mode === 'scene'" class="render__scene">
          <text class="render__row-label">上传目标场景</text>
          <view class="render__scene-slot" role="button" @click="pickScene">
            <image v-if="scene" class="render__scene-img" :src="scene" mode="aspectFill" />
            <view v-else class="render__scene-empty">
              <AppIcon name="plus" :size="24" color="#9C9488" />
              <text>上传目标场景</text>
            </view>
          </view>
        </view>
      </view>

      <!-- ============ 音色选择 ============ -->
      <view class="render__card">
        <view class="render__head">
          <view class="render__title">
            <view class="render__bar" />
            <text>音色选择</text>
          </view>
        </view>

        <view class="render__voice-row">
          <picker mode="selector" :range="voiceLabels" :value="voiceIndex" @change="onVoiceChange">
            <view class="app-field render__select">
              <text class="render__select-text app-truncate">{{ voiceLabel }}</text>
              <AppIcon name="chevron-down" :size="16" color="#6B6357" />
            </view>
          </picker>
          <view class="render__preview-btn" :class="{ 'render__preview-btn--active': voicePreviewPlaying || voicePreviewLoading }" role="button" @click="toggleVoicePreview">
            <AppIcon :name="voicePreviewLoading ? 'loader' : voicePreviewPlaying ? 'pause' : 'play'" :size="14" color="#B23A2E" :stroke-width="2.5" />
            <text>{{ voicePreviewLoading ? '生成中' : voicePreviewPlaying ? '停止' : '试听' }}</text>
          </view>
        </view>

        <!-- 更多设置 -->
        <view class="render__more">
          <view class="render__more-head" role="button" @click="moreOpen = !moreOpen">
            <text class="render__more-title">更多设置</text>
            <AppIcon
              name="chevron-down"
              :size="18"
              color="#6B6357"
              :class="moreOpen ? 'render__arrow--open' : ''"
            />
          </view>

          <view class="render__collapse" :class="{ 'render__collapse--open': moreOpen }">
            <view class="render__collapse-inner">
              <!-- 语速调节 -->
              <view class="render__setting">
                <view class="render__setting-head">
                  <text class="render__setting-label">语速调节</text>
                  <text class="render__setting-value">{{ speedText }}x</text>
                </view>
                <slider
                  class="render__slider"
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
                <view class="render__slider-marks">
                  <text>慢</text>
                  <text>正常</text>
                  <text>快</text>
                </view>
              </view>

              <!-- 方言选择：后端只文档化了 cantonese / chuanyu 两个语义键，故去掉设计稿的东北话 -->
              <view class="render__setting">
                <text class="render__setting-label">方言选择</text>
                <view class="render__dialects">
                  <view
                    v-for="item in DIALECT_OPTIONS"
                    :key="item.value"
                    class="render__option"
                    :class="{ 'render__option--active': dialect === item.value }"
                    role="button"
                    @click="dialect = item.value"
                  >
                    <text>{{ item.label }}</text>
                  </view>
                </view>
              </view>

              <!-- 输出画质：档位来自 estimate.options.resolutions（后端只支持 720P / 1080P，不支持 4K） -->
              <view class="render__setting">
                <text class="render__setting-label">输出画质</text>
                <view v-if="resolutionOptions.length" class="render__quality">
                  <view
                    v-for="item in resolutionOptions"
                    :key="item"
                    class="render__option"
                    :class="{ 'render__option--active': resolution === item }"
                    role="button"
                    @click="resolution = item"
                  >
                    <text>{{ item }}</text>
                  </view>
                </view>
                <text v-else class="render__setting-hint">画质档位加载中…</text>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 底部固定操作：叠在底部导航之上 -->
    <view class="render__action">
      <view
        class="render__submit app-btn-brand"
        :class="{ 'render__submit--loading': submitting }"
        role="button"
        aria-label="开始换口播"
        @click="submit"
      >
        <AppIcon name="play" :size="20" color="#FFFFFF" />
        <text>{{ submitting ? '提交中…' : '开始换口播' }}</text>
      </view>
      <text class="render__hint">{{ estimateHint }}</text>
      <ToolCost ref="toolCost" :params="{ type: 'render', duration: renderDuration || 8, resolution: resolution || undefined }" />
    </view>

    <AppTabBar active="create" />
  </view>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { onUnload } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import ToolCost from '@/components/ToolCost.vue'

const toolCost = ref(null)
import AppTabBar from '@/components/AppTabBar.vue'
import api from '@/api'
import { useUserStore } from '@/store/modules/user'
import { currentPagePath, go, toLoginPath } from '@/utils/navigation'
import { chooseVideoFile } from '@/utils/media'
import { MAX_UPLOAD_MB, uploadMedia } from '@/utils/upload'
import { formatDuration } from '@/utils/task'

/**
 * 视频换口播（对应设计稿《视频换口播》）。
 *
 * 设计稿的示例视频/文件名/「1080P」都是演示数据，这里全部换成真实上传结果；
 * 提交与预估都走后端真实接口，路线由字段组合派生（digital_id / scene / 都不传）。
 */

const userStore = useUserStore()

/** 功能 chip：顺序与设计稿一致（换声 / 换数字人 / 换场景） */
const MODE_OPTIONS = [
  { key: 'voice', label: '换声', icon: 'mic' },
  { key: 'digital', label: '换数字人', icon: 'award' },
  { key: 'scene', label: '换场景', icon: 'image' },
]

/** 方言：后端文档化的语义键只有 cantonese(粤语) / chuanyu(四川话)，普通话用空串 */
const DIALECT_OPTIONS = [
  { value: '', label: '普通话' },
  { value: 'cantonese', label: '粤语' },
  { value: 'chuanyu', label: '四川话' },
]

/**
 * 音色清单：复用豆包语音合成 2.0 官方音色（与《数字人口播》同源），
 * 不使用设计稿里示意性的「小雅 / 小柔」等虚构音色。
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

const mode = ref('voice')
const video = ref(null)
const videoUploading = ref(false)
const videoProgress = ref(0)

const prompt = ref('')
const extracting = ref(false)
const polishing = ref(false)

const voice = ref('')
const voicePreviewLoading = ref(false)
const voicePreviewPlaying = ref(false)
let voiceAudio = null
let voicePreviewSeq = 0
const speed = ref(1.0)
const dialect = ref('')
const resolution = ref('')
const moreOpen = ref(false)

const digitalId = ref(null)
const digitalName = ref('')
const digitalList = ref([])
const scene = ref('')

const submitting = ref(false)
const estimate = ref(null)
let estimateTimer = null
let estimateSeq = 0
/** 轮询计时器（润色 / 拆解）：离开页面时必须清理 */
const pollTimers = []

const promptCount = computed(() => prompt.value.length)
/** 语速展示统一保留一位小数（1.0x / 1.5x …） */
const speedText = computed(() => Number(speed.value).toFixed(1))
const voiceIndex = computed(() => {
  const idx = VOICE_OPTIONS.findIndex((o) => o.value === voice.value)
  return idx < 0 ? 0 : idx
})
const voiceLabel = computed(() => VOICE_OPTIONS[voiceIndex.value]?.label || '选择音色')

/** 成片时长档位：后端 render schema 只接受 3~15 秒，超范围则不传（由后端用默认值） */
const renderDuration = computed(() => {
  const value = Number(video.value?.duration || 0)
  return value >= 3 && value <= 15 ? Math.round(value) : null
})

const durationBadge = computed(() => formatDuration(video.value?.duration || 0))

const fileMetaText = computed(() => {
  const size = formatSize(video.value?.size)
  return size ? `${size} · 已上传` : '已上传'
})

/** 输出画质只保留后端白名单内的档位（720P / 1080P），不提供未接入的 4K */
const resolutionOptions = computed(() =>
  (estimate.value?.options?.resolutions || []).filter((item) => !/4k/i.test(String(item)))
)

const estimateHint = computed(() => {
  const data = estimate.value
  if (!data || data.cost === null || data.cost === undefined) return '预计消耗 -- 额度'
  const minutes = Math.max(1, Math.round(Number(data.estimate_seconds || 0) / 60))
  return `预计消耗 ${data.cost} 额度 · 约 ${minutes} 分钟`
})

function toast(title) {
  uni.showToast({ title, icon: 'none' })
}

function formatSize(bytes) {
  const num = Number(bytes || 0)
  if (!num) return ''
  if (num >= 1024 * 1024) return `${(num / 1024 / 1024).toFixed(1)}MB`
  return `${Math.max(1, Math.round(num / 1024))}KB`
}

function requireLogin() {
  if (userStore.isLoggedIn) return true
  go(toLoginPath(currentPagePath()))
  return false
}

// ---------- 视频上传 ----------

/** 选择视频并上传（小程序走 chooseMedia，H5/App 走 chooseVideo，统一封装见 utils/media） */
function chooseVideo() {
  if (!requireLogin()) return
  chooseVideoFile()
    .then(async (meta) => {
      // 后端单文件上限 50MB，客户端先拦一道，避免白等一次必然失败的上传
      if (meta.size && meta.size > MAX_UPLOAD_MB * 1024 * 1024) {
        toast(`视频不能超过 ${MAX_UPLOAD_MB}MB`)
        return
      }

      videoUploading.value = true
      videoProgress.value = 0
      try {
        const data = await uploadMedia(meta.path, {
          onProgress: (percent) => {
            videoProgress.value = percent
          },
        })
        video.value = {
          url: data.url,
          localPath: meta.path,
          name: meta.name,
          size: meta.size || data.size || 0,
          duration: Math.round(meta.duration),
        }
      } catch (err) {
        console.error('上传视频失败', err)
        toast(err?.message || '上传失败，请稍后重试')
      } finally {
        videoUploading.value = false
      }
    })
    .catch((err) => {
      if (err && err.message !== 'CANCEL') console.error('选择视频失败', err)
    })
}

function togglePlay() {
  try {
    const ctx = uni.createVideoContext('renderVideo')
    if (ctx && typeof ctx.play === 'function') ctx.play()
  } catch (err) {
    console.error('播放预览视频失败', err)
  }
}

// ---------- AI 提取（复用对标视频拆解链路） ----------

/**
 * 用户侧没有独立的语音转文字接口，这里复用后端「对标视频拆解」能力：
 * deconstruct 建单后结果经 /v1/task/detail 的 result_text 回读，再从句子里抽出台词。
 */
async function extractScript() {
  if (extracting.value) return
  if (!video.value) {
    toast('请先上传视频')
    return
  }
  extracting.value = true
  try {
    const payload = { reference_video: video.value.url, device: 'mobile' }
    const seconds = Number(video.value.duration || 0)
    // 拆解侧的 duration 只接受 1~120 秒，超出范围时不传（由 worker 用 ffmpeg 自行探测）
    if (seconds >= 1 && seconds <= 120) payload.duration = Math.round(seconds)

    const res = await api.task.deconstruct.post(payload, { suppressGlobalError: true })
    const taskId = res && res.code === 1 ? res.data?.id : null
    if (!taskId) {
      toast(res?.message || '识别失败，请重试')
      return
    }
    const text = await pollDeconstruct(taskId)
    if (!text) {
      toast('未识别到台词，请手动输入')
      return
    }
    prompt.value = text
  } catch (err) {
    console.error('AI 提取口播文案失败', err)
    toast(err?.data?.message || err?.message || '识别失败，请重试')
  } finally {
    extracting.value = false
  }
}

function pollDeconstruct(taskId) {
  return new Promise((resolve) => {
    const startedAt = Date.now()
    const timer = setInterval(async () => {
      // 拆解是重任务，给足 3 分钟
      if (Date.now() - startedAt > 180000) {
        clearInterval(timer)
        resolve('')
        return
      }
      try {
        const res = await api.task.detail.post(
          { id: taskId },
          { suppressGlobalError: true }
        )
        const data = res && res.code === 1 ? res.data : null
        const raw = String(data?.result_text || '').trim()
        if (raw) {
          clearInterval(timer)
          resolve(extractNarration(raw))
        }
      } catch (err) {
        console.error('轮询拆解结果失败', err)
      }
    }, 3000)
    pollTimers.push(timer)
  })
}

/** 从拆解结果里抽出台词：优先按 JSON 结构取 narration/text，取不到就把原文当台词 */
function extractNarration(resultText) {
  const text = String(resultText || '').trim()
  if (!text) return ''
  try {
    const parsed = JSON.parse(text)
    const lines = []
    collectNarration(parsed, lines)
    return lines.length ? lines.join('\n') : ''
  } catch (err) {
    // 非 JSON 结果：后端直接把台词当纯文本回写，原样使用
    return text
  }
}

/** 递归遍历解析后的结构（分镜/段落数组），收集 narration / text 字段 */
function collectNarration(node, out) {
  if (!node) return
  if (Array.isArray(node)) {
    node.forEach((item) => collectNarration(item, out))
    return
  }
  if (typeof node !== 'object') return
  const narration = node.narration
  if (typeof narration === 'string' && narration.trim()) out.push(narration.trim())
  const text = node.text
  if (typeof text === 'string' && text.trim()) out.push(text.trim())
  Object.values(node).forEach((value) => {
    if (value && typeof value === 'object') collectNarration(value, out)
  })
}

// ---------- AI 润色 ----------

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
  const text = prompt.value.trim()
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
    prompt.value = content
  } catch (err) {
    console.error('AI 润色失败', err)
    toast(err?.data?.message || err?.message || '润色失败，请重试')
  } finally {
    polishing.value = false
  }
}

// ---------- 功能选择 ----------

function selectMode(key) {
  // 数字人路线必须登录（列表按账号维度返回自己的可用形象）
  if (key === 'digital' && !userStore.isLoggedIn) {
    go(toLoginPath(currentPagePath()))
    return
  }
  mode.value = key
}

async function loadDigitalList() {
  try {
    const res = await api.digital.list.post(
      { pageNum: 1, pageSize: 20 },
      { suppressGlobalError: true }
    )
    digitalList.value = res && res.code === 1 && Array.isArray(res.data) ? res.data : []
  } catch (err) {
    console.error('加载数字人列表失败', err)
    digitalList.value = []
  }
}

async function pickDigital() {
  if (!requireLogin()) return
  if (!digitalList.value.length) await loadDigitalList()
  if (!digitalList.value.length) {
    toast('暂无可用的数字人形象')
    return
  }
  uni.showActionSheet({
    itemList: digitalList.value.map((item) => String(item.name || '未命名形象')),
    success: ({ tapIndex }) => {
      const picked = digitalList.value[tapIndex]
      if (!picked) return
      digitalId.value = picked.id
      digitalName.value = String(picked.name || '未命名形象')
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择数字人失败', err)
    },
  })
}

function pickScene() {
  uni.chooseImage({
    count: 1,
    success: async (res) => {
      const path = res.tempFilePaths && res.tempFilePaths[0]
      if (!path) return
      try {
        const data = await uploadMedia(path, {
          onProgress: (percent) => toast(`上传中 ${percent}%`),
        })
        scene.value = data.url || ''
      } catch (err) {
        console.error('上传目标场景失败', err)
        toast(err?.message || '上传失败，请稍后重试')
      }
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择目标场景失败', err)
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
    voice.value = picked.value
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

// ---------- 预估 ----------

function buildEstimatePayload() {
  const payload = { type: 'render' }
  if (renderDuration.value) payload.duration = renderDuration.value
  if (resolution.value) payload.resolution = resolution.value
  return payload
}

async function runEstimate() {
  const seq = ++estimateSeq
  try {
    const res = await api.task.estimate.post(buildEstimatePayload(), {
      suppressGlobalError: true,
      suppressGlobalAuthError: true,
    })
    if (seq !== estimateSeq) return
    estimate.value = res && res.code === 1 && res.data ? res.data : null
    if (estimate.value) syncResolutionDefault()
  } catch (err) {
    console.error('预估换口播消耗失败', err)
    if (seq === estimateSeq) estimate.value = null
  }
}

/** 默认画质取后端下发的默认值（不在白名单内则回退第一档） */
function syncResolutionDefault() {
  if (resolution.value) return
  const options = resolutionOptions.value
  if (!options.length) return
  const preferred = estimate.value?.gen_resolution
  resolution.value = options.includes(preferred) ? preferred : options[0]
}

function scheduleEstimate() {
  if (estimateTimer) clearTimeout(estimateTimer)
  estimateTimer = setTimeout(runEstimate, 300)
}

watch([renderDuration, resolution], () => scheduleEstimate())

// ---------- 提交 ----------

async function submit() {
  if (submitting.value) return
  if (!video.value) {
    toast('请先上传视频')
    return
  }
  if (!prompt.value.trim()) {
    toast('请输入口播文案')
    return
  }
  if (mode.value === 'digital' && !digitalId.value) {
    toast('请选择数字人')
    return
  }
  if (mode.value === 'scene' && !scene.value) {
    toast('请上传目标场景')
    return
  }
  if (videoUploading.value) {
    toast('视频上传中，请稍候')
    return
  }
  if (!requireLogin()) return

  submitting.value = true
  try {
    if (!await toolCost.value?.ensure()) return
    const payload = {
      source_video: video.value.url,
      prompt: prompt.value.trim(),
      voice: voice.value,
      speed: Number(speed.value),
      device: 'mobile',
    }
    // 路线字段互斥：换声不传任何路线字段，换数字人只传 digital_id，换场景只传 scene
    if (mode.value === 'digital') payload.digital_id = digitalId.value
    if (mode.value === 'scene' && scene.value) payload.scene = scene.value
    if (dialect.value) payload.dialect = dialect.value
    if (renderDuration.value) payload.duration = renderDuration.value
    if (resolution.value) payload.resolution = resolution.value

    const res = await api.task.renderCreate.post(payload, { suppressGlobalError: true })
    if (!res || res.code !== 1) {
      toast(res?.message || '提交失败，请稍后重试')
      return
    }
    await toolCost.value?.refresh()
    toast('已提交生成')
    go('/pages/works/index')
  } catch (err) {
    console.error('创建视频换口播任务失败', err)
    toast(err?.data?.message || err?.message || '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

// ---------- 生命周期 ----------

onMounted(() => {
  voice.value = VOICE_OPTIONS[0].value
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
/* 页面内容避让「底部操作栏 + 底部导航」 */
.render {
  padding-bottom: calc(var(--nav-h) + 108px + constant(safe-area-inset-bottom));
  padding-bottom: calc(var(--nav-h) + 108px + env(safe-area-inset-bottom));
}

.render__body {
  padding: 18px 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: #f3eee4;
}

/* ============ 分区卡片 ============ */
.render__card {
  position: relative;
  background: #fbf8f0;
  border: 1px solid #ddd4c5;
  border-radius: 6px;
  box-shadow: 0 3px 12px rgba(62, 49, 35, 0.05);
  padding: 17px 16px;
}

.render__card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 16px;
  right: 16px;
  height: 1px;
  background: #b9aa96;
  opacity: 0.55;
}

.render__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.render__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.render__bar {
  width: 3px;
  height: 17px;
  border-radius: 0;
  background: #b23a2e;
}

.render__tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border: 1px solid rgba(178, 58, 46, 0.28);
  border-radius: 2px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(178, 58, 46, 0.04);
  color: #b23a2e;
}

.render__extract {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  color: var(--brand-primary);
}

/* ============ 上传区 ============ */
.render__zone {
  border: 1px dashed #b9aa96;
  border-radius: 3px;
  background: #f7f2e8;
  padding: 36px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: border-color var(--transition-fast), background-color var(--transition-fast);

  &:active {
    border-color: var(--brand-primary);
    background: var(--brand-primary-light);
  }
}

.render__zone-icon {
  width: 50px;
  height: 50px;
  border-radius: 2px;
  background: #b23a2e;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  box-shadow: 0 3px 8px rgba(178, 58, 46, 0.16);
}

.render__zone-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.render__zone-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.render__zone-btn {
  padding: 7px 18px;
  border: 1px solid rgba(178, 58, 46, 0.36);
  border-radius: 2px;
  background: rgba(178, 58, 46, 0.06);
  color: var(--brand-primary);
  font-size: 12px;
  font-weight: 500;
}

.render__zone-pct {
  font-size: 13px;
  font-weight: 600;
  color: var(--brand-primary);
}

/* ============ 视频预览 ============ */
.render__video {
  position: relative;
  border-radius: 3px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(31, 29, 26, 0.14);
  background: #1F1D1A;
}

.render__video-el {
  width: 100%;
  height: 200px;
  display: block;
}

.render__video-mask {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(180deg, transparent 48%, rgba(0, 0, 0, 0.42) 100%);
}

.render__play {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.render__badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  padding: 3px 8px;
  border-radius: 2px;
  background: rgba(0, 0, 0, 0.7);
  color: #ffffff;
  font-size: 11px;
  font-weight: 500;
}

.render__reupload {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 2px;
  background: rgba(0, 0, 0, 0.6);
  color: #ffffff;
  font-size: 12px;
}

.render__file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 12px;
}

.render__file-left {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.render__file-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.render__file-meta {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--text-muted);
}

/* ============ 文案 ============ */
.render__textarea {
  height: 128px;
  line-height: 1.6;
}

.render__counter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.render__counter {
  font-size: 12px;
  color: var(--text-muted);
}

.render__polish {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  font-weight: 500;
  color: var(--brand-primary);
}

/* ============ 功能选择 ============ */
.render__chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  margin: 0 -4px;
  padding-left: 4px;
  padding-right: 4px;
}

.render__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e0d8cc;
}

.render__row-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.render__row-value {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-tertiary);
}

.render__scene {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e0d8cc;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.render__scene-slot {
  height: 96px;
  border: 1px dashed #b9aa96;
  border-radius: 3px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;

  &:active {
    border-color: var(--brand-primary);
  }
}

.render__scene-img {
  width: 100%;
  height: 100%;
}

.render__scene-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-muted);
}

/* ============ 音色 / 更多设置 ============ */
.render__voice-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.render__voice-row picker {
  flex: 1;
  min-width: 0;
}

.render__preview-btn {
  flex-shrink: 0;
  height: 40px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  border: 1px solid rgba(178, 58, 46, 0.35);
  border-radius: 4px;
  color: #b23a2e;
  font-size: 12px;
  background: #fffaf3;
}

.render__preview-btn--active {
  background: #f9e8e2;
}

.render__select {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.render__select-text {
  flex: 1;
  min-width: 0;
}

.render__more {
  margin-top: 18px;
  border-top: 1px solid #e0d8cc;
  padding-top: 16px;
}

.render__more-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.render__more-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.render__arrow--open {
  transform: rotate(180deg);
}

.render__collapse {
  max-height: 0;
  overflow: hidden;
  transition: max-height var(--transition-slow);

  &--open {
    max-height: 560px;
  }
}

.render__collapse-inner {
  padding-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.render__setting {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.render__setting-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.render__setting-label {
  font-size: 14px;
  color: var(--text-tertiary);
}

.render__setting-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--brand-primary);
}

.render__setting-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.render__slider-marks {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
}

.render__dialects {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.render__quality {
  display: flex;
  gap: 8px;
}

.render__quality .render__option {
  flex: 1;
}

.render__option {
  padding: 8px 0;
  text-align: center;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: #f7f2e8;
  border: 1px solid #d8cfc1;
  border-radius: 2px;

  &--active {
    color: var(--brand-primary);
    background: rgba(178, 58, 46, 0.07);
    border-color: rgba(178, 58, 46, 0.42);
  }
}

/* ============ 底部固定操作 ============ */
.render__action {
  position: fixed;
  bottom: calc(60px + constant(safe-area-inset-bottom));
  bottom: calc(60px + env(safe-area-inset-bottom));
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: var(--page-max);
  background: rgba(251, 248, 240, 0.98);
  border-top: 1px solid #d8cfc1;
  padding: 12px 16px;
  z-index: 45;
  box-shadow: 0 -4px 12px rgba(62, 49, 35, 0.08);
}

.render__submit {
  height: 48px;
  border-radius: 3px;
  background: #b23a2e;
  box-shadow: 0 4px 10px rgba(178, 58, 46, 0.18);
  font-size: 16px;

  &--loading {
    opacity: 0.6;
  }
}

.render__hint {
  display: block;
  margin-top: 8px;
  text-align: center;
  font-size: 12px;
  color: #857b6d;
}
</style>
