// 豆包语音合成 2.0 官方音色列表(火山引擎)
// 来源: https://docs.volcengine.com/docs/6561/1257544 (音色列表--豆包语音)
// 仅作前端下拉选项;worker 侧 audio_tool 会把 voice 透传给 TTS 网关,
// 无效 ID 由网关校验,前端不在此做硬校验(避免与官方清单脱节)。
//
// ⚠️ 两个必须遵守的约定:
//  1) 每个分组必须写 `type: 'group'`。Naive UI 的 createValOptMap 只对 `type==='group'`
//     的节点递归收集 children 的 value;漏掉它会把分组当普通选项,导致所有音色 value
//     查不到 → 选中态回退显示成 voice_type 英文 ID(而非中文名)。
//  2) 本清单只收录普通话/英文音色名,**不含方言音色 ID**。注意这不等于"不支持方言":
//     豆包语音 2.0 音色(*_uranus_bigtts)官方标注自带多方言能力(粤语/上海/河南/北京/
//     天津/四川/陕西/东北),见火山引擎《音色列表--豆包语音》(2026-09 版)。
//     这里禁用的是管理端手工填写的清单外方言 ID(多为小模型音色,网关是否开通未验证),
//     避免用户白跑一次必然失败的任务;正式开方言需先确认网关的方言触发方式。
export const DOUBAO_VOICE_GROUPS = [
  {
    type: 'group',
    label: '中文女声',
    children: [
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
    ],
  },
  {
    type: 'group',
    label: '中文男声',
    children: [
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
    ],
  },
  {
    type: 'group',
    label: '风格化（Saturn）',
    children: [
      { label: '调皮公主', value: 'saturn_zh_female_tiaopigongzhu_tob' },
      { label: '爽朗少年', value: 'saturn_zh_male_shuanglangshaonian_tob' },
      { label: '天才同桌', value: 'saturn_zh_male_tiancaitongzhuo_tob' },
      { label: '知性灿灿', value: 'saturn_zh_female_cancan_tob' },
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
    ],
  },
  {
    type: 'group',
    label: '英文音色',
    children: [
      { label: 'Tim（男）', value: 'en_male_tim_uranus_bigtts' },
      { label: 'Dacey（女）', value: 'en_female_dacey_uranus_bigtts' },
      { label: 'Stokie（女）', value: 'en_female_stokie_uranus_bigtts' },
    ],
  },
]

// voice_type → 中文名 反查表:供渲染层兜底显示(避免任何路径下把英文 ID 直接甩给用户)
const VOICE_NAME_MAP = DOUBAO_VOICE_GROUPS.reduce((acc, group) => {
  group.children.forEach((opt) => { acc[opt.value] = opt.label })
  return acc
}, {})

/**
 * 取 voice_type 对应的中文名;不在官方清单内时返回空串。
 * @param {string} value TTS voice_type
 * @returns {string} 中文名,未知返回 ''
 */
export function voiceTypeLabel(value) {
  return VOICE_NAME_MAP[value] || ''
}

// 方言/小众音色关键词:覆盖火山引擎与常见网关的方言命名(粤语/四川/河南/上海…及 cantonese/dialect 等)
const DIALECT_KEYWORDS = [
  'cantonese', '粤语', 'yue', 'sichuan', '四川', 'dialect', '方言',
  'henan', '河南', 'shanghai', '上海', 'minnan', '闽南', 'hakka', '客家',
  'wenzhou', '温州', 'chongqing', '重庆', 'nanjing', '南京', 'tianjin', '天津',
  'xiamen', '厦门', 'harbin', '哈尔滨',
]

/**
 * 判断一个 voice_type 是否疑似方言/小众音色(当前 TTS 网关不支持,选中会合成失败)。
 * 官方清单本身不含方言,方言只可能来自管理端手工填写,因此按关键词识别并在 UI 上标注风险。
 * @param {string} value TTS voice_type
 * @returns {boolean} 命中方言关键词返回 true
 */
export function isDialectVoice(value) {
  return DIALECT_KEYWORDS.some((k) => String(value || '').toLowerCase().includes(k))
}

/**
 * 把「当前形象绑定的音色」补进下拉选项。
 *
 * 背景:管理端「数字人 → 音色」是自由文本输入,运营可能填了官方清单之外的 ID
 * (含方言,而当前 TTS 网关不支持)。这类值在下拉里没有对应项,Naive UI 会回退把
 * 英文 ID 当 label 显示。这里显式插一条兜底项:既有中文可读说明,也能让用户看清
 * 这个音色可能不可用,而不是提交后才失败。
 *
 * @param {Array} groups 官方音色分组
 * @param {string} value 当前绑定的 voice_type
 * @returns {Array} 补齐兜底项后的新分组数组(不修改入参)
 */
export function withCurrentVoiceOption(groups, value) {
  const v = (value || '').trim()
  if (!v || VOICE_NAME_MAP[v]) return groups
  const dialect = isDialectVoice(v)
  const item = {
    label: dialect ? `自定义音色（方言，当前网关不支持）：${v}` : `自定义音色（不在官方清单）：${v}`,
    value: v,
    disabled: dialect,   // 方言直接不可选,避免用户白跑一次失败任务
  }
  return [{ type: 'group', label: '当前形象绑定', children: [item] }, ...groups]
}

// 可选方言清单:与火山引擎官方「方言口音」对齐(川渝含重庆/四川、粤语、东北、北京、天津、
// 河南、上海、陕西、台湾、广西)。注意这里列的是「口音/方言」,并非独立音色 —— 豆包语音 2.0
// 音色自带多方言能力,靠「指令遵循」触发(见 docs 方言方案)。
// value 为语义键(稳定、与网关无关);keywords 用于从口播文案里识别用户写的方言要求。
export const DIALECT_OPTIONS = [
  { value: 'chuanyu', label: '川渝（含重庆/四川）', keywords: ['川渝', '重庆', '重庆话', '四川', '四川话', '川普', '成渝'] },
  { value: 'cantonese', label: '粤语（广东话）', keywords: ['粤语', '广东', '广州', '白话', '广府', 'yue', 'cantonese'] },
  { value: 'dongbei', label: '东北话', keywords: ['东北', '辽宁', '吉林', '黑龙江', '东北话'] },
  { value: 'beijing', label: '北京话（京腔）', keywords: ['北京', '京腔', '京片子', '北平', '北京话'] },
  { value: 'tianjin', label: '天津话', keywords: ['天津', '天津话'] },
  { value: 'henan', label: '河南话', keywords: ['河南', '中原', '河南话'] },
  { value: 'shanghai', label: '上海话', keywords: ['上海', '沪语', '吴语', '上海话'] },
  { value: 'shanxi', label: '陕西话（关中）', keywords: ['陕西', '西安', '关中', '西安话'] },
  { value: 'taiwan', label: '台湾腔', keywords: ['台湾', '台普', '湾湾', '台湾腔'] },
  { value: 'guangxi', label: '广西话', keywords: ['广西', '桂柳', '南宁', '广西话'] },
]

/**
 * 从口播文案里识别用户写出的方言要求(如「用重庆方言说:...」)。
 * 命中任一方言的关键词即返回该方言的语义键;未命中返回 ''。
 * 仅做意图识别,**不改写文案** —— 是否剥离指令由调用方(页面)决定,守「口播逐字念出」底线。
 * @param {string} text 口播文案
 * @returns {string} 方言语义键(如 'chuanyu'),未命中返回 ''
 */
export function detectDialectInText(text) {
  const t = String(text || '').toLowerCase()
  if (!t.trim()) return ''
  // 优先完全匹配「xx方言/xx话」这类明确写法,再退回单关键词(避免把含「川」的字误判)
  for (const opt of DIALECT_OPTIONS) {
    if (opt.keywords.some((k) => k.length >= 3 && t.includes(k.toLowerCase()))) return opt.value
  }
  for (const opt of DIALECT_OPTIONS) {
    if (opt.keywords.some((k) => k.length < 3 && t.includes(k.toLowerCase()))) return opt.value
  }
  return ''
}

// ---- 方言指令前缀剥离(成片口播专用) ----
// 用户可能在台词里写「用xx方言说：…」「xx话：…」「请用xx话说，…」等指令性前缀。识别到后,
// 从「实际传给 TTS 的口播文本」里去掉这段前缀(方言指令不该被数字人念出来),方言本身仍通过
// dialect 字段生效。仅当「方言名 + 触发词(说/念/讲/播/读/版/：/，)」结构齐备时才剥离,
// 避免误伤正常含地名的文案(如「北京欢迎你」「话说天下」没有触发词,不会被剥离)。
// 不含具体方言名的「用方言说：」也会被剥离,但此时 dialect 无法解析,需用户手动在下拉选。
const DIALECT_STRIP_NAMES = [
  '重庆话', '四川话', '天津话', '河南话', '上海话', '西安话', '台湾腔', '广西话', '北京话',
  '川渝', '重庆', '四川', '川普', '成渝', '粤语', '广东', '广州', '白话', '广府',
  '东北', '辽宁', '吉林', '黑龙江', '北京', '京腔', '京片子', '北平',
  '天津', '河南', '中原', '上海', '沪语', '吴语', '陕西', '西安', '关中',
  '台湾', '台普', '湾湾', '广西', '桂柳', '南宁',
].sort((a, b) => b.length - a.length)

const DIALECT_STRIP_RE = new RegExp(
  '^(?:(?:用|请用|请|让|帮|给我)\\s*)?(?:我|你|他|她)?\\s*(?:' +
  DIALECT_STRIP_NAMES.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') +
  '|方言)\\s*(?:方言|话|腔|口音)?\\s*(?:(?:说|念|讲|播|读|来|版|报|唱)\\s*[：:：，,]?|[：:：，,])\\s*',
  'u'
)

/**
 * 从口播文本里剥离「用xx方言说：」这类方言指令前缀,返回真正要念的内容。
 * 无前缀或不含触发词结构时原样返回(不误伤)。仅做文本清洗,不影响方言识别与 dialect 字段。
 * @param {string} text 口播文案(可能含方言指令前缀)
 * @returns {string} 去掉指令前缀后的口播文本
 */
export function stripDialectInstruction(text) {
  const t = String(text || '').trim()
  if (!t) return ''
  return t.replace(DIALECT_STRIP_RE, '').trim()
}

/**
 * 判断口播文本是否含「方言指令前缀」(剥离后内容会变)。用于提示用户:写了指令却未能解析出
 * 具体方言时,需手动在「方言」下拉选择,否则按普通话合成。
 * @param {string} text 口播文案
 * @returns {boolean} 含可剥离的方言指令返回 true
 */
export function hasDialectInstruction(text) {
  const t = String(text || '').trim()
  if (!t) return false
  return DIALECT_STRIP_RE.test(t)
}
