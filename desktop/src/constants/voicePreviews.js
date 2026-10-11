// 音色试听样音映射:voice_type(value) -> 本地预生成 mp3 的访问路径(位于 desktop/public/tts_dump/)。
// 这些样音由 seed-audio-1.0 描述驱动生成(文案固定为"一源AI, 祝你身体健康"),
// 与 DOUBAO_VOICE_GROUPS 的正式预设音色并非同一合成链路,仅作为选音色前的试听参考。
import { DOUBAO_VOICE_GROUPS } from './doubaoVoices'

const VOICE_PREVIEW_MAP = {
  'zh_female_vv_uranus_bigtts': '/tts_dump/01_vivi.mp3',
  'zh_female_xiaohe_uranus_bigtts': '/tts_dump/02_xiaohe.mp3',
  'zh_female_sophie_uranus_bigtts': '/tts_dump/03_sophie.mp3',
  'zh_female_qingxinnvsheng_uranus_bigtts': '/tts_dump/04_qingxin.mp3',
  'zh_female_wenroushunv_uranus_bigtts': '/tts_dump/05_wenrou_shunv.mp3',
  'zh_female_zhixingnv_uranus_bigtts': '/tts_dump/06_zhixing_nv.mp3',
  'zh_female_qinqienv_uranus_bigtts': '/tts_dump/07_qinqie_nv.mp3',
  'zh_female_kefunvsheng_uranus_bigtts': '/tts_dump/08_kefu_nv.mp3',
  'zh_female_gaolengyujie_uranus_bigtts': '/tts_dump/09_gaoleng_yujie.mp3',
  'zh_female_cancan_uranus_bigtts': '/tts_dump/10_cancan.mp3',
  'zh_male_m191_uranus_bigtts': '/tts_dump/11_yunzhou.mp3',
  'zh_male_ruyaqingnian_uranus_bigtts': '/tts_dump/12_ruya_qingnian.mp3',
  'zh_male_cixingjieshuonan_uranus_bigtts': '/tts_dump/13_cixing_jieshuo.mp3',
  'zh_male_yangguangqingnian_uranus_bigtts': '/tts_dump/14_yangguang.mp3',
  'zh_male_wenrouxiaoge_uranus_bigtts': '/tts_dump/15_wenrou_xiaoge.mp3',
  'zh_male_yuanboxiaoshu_uranus_bigtts': '/tts_dump/16_yuanbo.mp3',
  'zh_male_jieshuoxiaoming_uranus_bigtts': '/tts_dump/17_jieshuo_xm.mp3',
  'zh_male_guanggaojieshuo_uranus_bigtts': '/tts_dump/18_ad_jieshuo.mp3',
  'saturn_zh_female_chengshujiejie_tob': '/tts_dump/19_chengshu_jj.mp3',
  'saturn_zh_male_chengshuzongcai_tob': '/tts_dump/20_chengshu_ceo.mp3',
}

export { VOICE_PREVIEW_MAP }

// 返回注入 preview 字段后的音色选项(供 n-select 使用),不改动 DOUBAO_VOICE_GROUPS 本身。
export function voiceOptionsWithPreview() {
  return DOUBAO_VOICE_GROUPS.map((group) => ({
    ...group,
    children: group.children.map((opt) =>
      VOICE_PREVIEW_MAP[opt.value]
        ? { ...opt, preview: VOICE_PREVIEW_MAP[opt.value] }
        : opt
    ),
  }))
}
