<template>
  <view class="app-page studio">
    <AppNavBar title="创作工作室" solid />

    <!-- 已选模板：从首页「热门模板」带入时展示，可一键取消；未选模板时整行不出现 -->
    <view v-if="templateId" class="studio__template">
      <AppIcon name="layers" :size="16" color="#B23A2E" />
      <text class="studio__template-text app-truncate">已选模板：{{ templateTitle }}</text>
      <view class="studio__template-close" role="button" aria-label="取消选择模板" @click="clearTemplate" tabindex="0" @keydown.enter.stop.prevent="clearTemplate" @keydown.space.stop.prevent="clearTemplate">
        <AppIcon name="close" :size="16" color="#6B6357" :stroke-width="2.5" />
      </view>
    </view>

    <!-- 创作方式选择：两个大 tab，切换只换表单，不清空另一侧已填内容 -->
    <view class="studio__modes">
      <view
        class="studio__mode"
        :class="{ 'studio__mode--active': mode === 'remake' }"
        role="button"
        aria-label="视频复刻"
        @click="mode = 'remake'"
       tabindex="0" @keydown.enter.stop.prevent="mode = 'remake'" @keydown.space.stop.prevent="mode = 'remake'" :aria-pressed="mode === 'remake'">
        <view class="studio__mode-icon">
          <AppIcon name="refresh-cw" :size="28" :color="mode === 'remake' ? '#B23A2E' : '#6B6357'" />
        </view>
        <text class="studio__mode-title">视频复刻</text>
        <text class="studio__mode-desc">用参考视频开始创作</text>
      </view>
      <view
        class="studio__mode"
        :class="{ 'studio__mode--active': mode === 'grid' }"
        role="button"
        aria-label="九宫格出片"
        @click="mode = 'grid'"
       tabindex="0" @keydown.enter.stop.prevent="mode = 'grid'" @keydown.space.stop.prevent="mode = 'grid'" :aria-pressed="mode === 'grid'">
        <view class="studio__mode-icon">
          <AppIcon name="grid" :size="28" :color="mode === 'grid' ? '#B23A2E' : '#6B6357'" />
        </view>
        <text class="studio__mode-title">九宫格出片</text>
        <text class="studio__mode-desc">让图片串成一个故事</text>
      </view>
    </view>

    <!-- ============ 视频复刻表单 ============ -->
    <view v-show="mode === 'remake'" class="studio__form">
      <view class="replicate-modes">
        <button class="replicate-mode" :class="{ 'replicate-mode--active': isAction }" :aria-pressed="isAction" @click="changeReplicateMode('action')"><text>动作复刻</text><text class="remake-slot__hint">参考动作与节奏，可换人物、场景</text></button>
        <button class="replicate-mode" :class="{ 'replicate-mode--active': !isAction }" :aria-pressed="!isAction" @click="changeReplicateMode('commerce')"><text>带货复刻</text><text class="remake-slot__hint">替换商品，调整介绍文案</text></button>
      </view>
      <!-- 三步引导：把"怎么用"直接做成可点的状态指引，首屏即懂 -->
      <view class="studio__guide-note">
        <text class="studio__guide-note-title">{{ stepHeadings[remake.step].title }}</text>
        <text class="studio__guide-note-desc">{{ stepHeadings[remake.step].desc }}</text>
      </view>
      <view class="studio__guide">
        <view
          v-for="(s, i) in guideSteps"
          :key="i"
          class="studio__guide-step"
          :class="`studio__guide-step--${guideStepState(i)}`"
          role="button"
          :aria-label="s.title"
          @click="scrollToStep(i)"
         tabindex="0" @keydown.enter.stop.prevent="scrollToStep(i)" @keydown.space.stop.prevent="scrollToStep(i)">
          <view class="studio__guide-no">{{ guideStepState(i) === 'done' ? '✓' : i + 1 }}</view>
          <view class="studio__guide-body">
            <text class="studio__guide-title">{{ s.title }}</text>
            <text class="studio__guide-desc">{{ s.desc }}</text>
          </view>
        </view>
      </view>

      <!-- 上传对标视频 -->
      <view v-show="remake.step === 0" id="remake-upload" class="studio__card">
        <view class="studio__card-title">
          <text>选择对标视频</text>
          <text class="studio__required">*</text>
        </view>

        <view v-if="!remake.refVideo" class="studio__upload" role="button" aria-label="从我的素材库选择视频" @click="chooseRefVideo" tabindex="0" @keydown.enter.stop.prevent="chooseRefVideo" @keydown.space.stop.prevent="chooseRefVideo">
          <view v-if="remake.refUploading" class="studio__upload-progress">
            <text class="studio__upload-pct">正在上传… {{ remake.refProgress }}%</text>
          </view>
          <template v-else>
            <view class="studio__upload-icon">
              <AppIcon name="video-camera" :size="28" color="#B23A2E" />
            </view>
            <text class="studio__upload-title">从我的素材库选择视频</text>
            <text class="studio__upload-hint">支持 MP4 / MOV 格式，时长不超过 {{ maxReferenceSeconds }}s</text>
            <view class="studio__tip">
              <AppIcon name="info" :size="12" color="#B98236" :stroke-width="2.5" />
              <text>AI 将解析画面、人物与产品</text>
            </view>
          </template>
        </view>

        <view v-else class="studio__upload studio__upload--filled">
          <video
            :key="remake.refVideo.url"
            class="studio__reference-video"
            :src="remake.refVideo.url"
            controls
            playsinline
            object-fit="contain"
            @loadedmetadata="remake.previewError = ''"
            @error="remake.previewError = '视频加载失败，请检查链接是否可访问，或重新上传 MP4 视频'"
          />
          <text v-if="remake.previewError" class="remake-feedback__error">{{ remake.previewError }}</text>
          <view class="studio__file">
            <view class="studio__file-icon">
              <AppIcon name="film" :size="22" color="#B23A2E" />
            </view>
            <view class="studio__file-body">
              <text class="studio__file-name app-truncate">{{ remake.refVideo.name }}</text>
              <text class="studio__file-meta">{{ refVideoMetaText }}</text>
            </view>
            <text class="studio__file-retry" role="button" aria-label="重新选择对标视频" @click="retryRefVideo" tabindex="0" @keydown.enter.stop.prevent="retryRefVideo" @keydown.space.stop.prevent="retryRefVideo">重新选择</text>
          </view>
        </view>
        <!-- 粘贴视频链接入口（仅在未上传视频时展示）：直链复刻，跳过本地上传 -->
        <view v-if="!remake.refVideo" class="studio__link">
          <view v-if="!remake.linkMode" class="studio__link-entry" role="button" aria-label="粘贴视频链接" @click="remake.linkMode = true" tabindex="0" @keydown.enter.stop.prevent="remake.linkMode = true" @keydown.space.stop.prevent="remake.linkMode = true">
            <AppIcon name="share" :size="14" color="#B23A2E" />
            <text>粘贴视频链接</text>
          </view>
          <view v-else class="studio__link-box">
            <AppField
              class="studio__link-input"
              v-model="remake.linkUrl"
              placeholder="粘贴可访问的视频链接，如 https://.../a.mp4"
              confirm-type="done"
              @confirm="applyLink" aria-label="参考视频链接"/>
            <view class="studio__link-actions">
              <text class="studio__link-cancel" role="button" aria-label="取消粘贴视频链接" @click="remake.linkMode = false; remake.linkUrl = ''" tabindex="0" @keydown.enter.stop.prevent="remake.linkMode = false; remake.linkUrl = ''" @keydown.space.stop.prevent="remake.linkMode = false; remake.linkUrl = ''">取消</text>
              <text class="studio__link-confirm" role="button" aria-label="使用视频链接" @click="applyLink" tabindex="0" @keydown.enter.stop.prevent="applyLink" @keydown.space.stop.prevent="applyLink">使用链接</text>
            </view>
          </view>
          <text class="studio__link-hint">没有视频文件？先在抖音点「分享 → 保存到相册」，再回到这里上传；仅支持可直接访问的视频链接</text>
        </view>
      </view>

      <view v-if="remake.step === 0" class="remake-feedback">
        <text v-if="remake.detecting">正在分析人物、场景和产品，请稍候…</text>
        <text v-else-if="remake.detectError" class="remake-feedback__error">{{ remake.detectError }}</text>
        <text v-else>解析后再上传你的图片。不替换的元素将保留原片。</text>
      </view>

      <!-- 按原片元素组织素材，一元素可有多张参考图。 -->
      <view v-if="remake.step === 1" class="remake-materials">
        <view class="remake-source">
          <AppIcon name="film" :size="18" color="#B23A2E" />
          <text class="app-truncate">{{ remake.refVideo?.name }}</text>
          <text class="remake-source__count">识别到 {{ remake.elements.length }} 个元素</text>
        </view>
        <view v-for="group in elementGroups" :key="group.kind" class="studio__card">
          <view class="studio__card-title studio__material-head">
            <text>{{ group.label }}</text>
            <text class="studio__sub-hint">{{ group.elements.length }} 个原片元素</text>
            <text class="remake-material-action" role="button" @click="supplementElement(group.kind)" tabindex="0" @keydown.enter.stop.prevent="supplementElement(group.kind)" @keydown.space.stop.prevent="supplementElement(group.kind)">补充漏识别元素</text>
          </view>
          <text v-if="!group.elements.length" class="remake-empty">本次未识别到{{ group.label }}。可重新解析，或返回更换视频。</text>
          <view v-for="el in group.elements" :key="el.id" class="remake-slot">
            <view class="remake-slot__original">
              <image v-if="el.thumbnail" class="remake-slot__thumb" :src="el.thumbnail" mode="aspectFit" :alt="`${group.label}所在的原片完整画面`" />
              <view v-else class="remake-slot__thumb remake-slot__placeholder"><AppIcon name="image" :size="22" color="#9C9488" /></view>
              <view class="remake-slot__body">
                <text class="remake-slot__name">{{ el.label || group.label }}</text>
                <text v-if="el.description" class="remake-slot__meta">{{ el.description }}</text>
                <text v-if="el.observations?.length" class="remake-slot__meta">涉及 {{ el.observations.length }} 处画面</text>
                <text class="remake-slot__meta">原片完整画面 · 非元素裁切图{{ formatTime(el.time) ? ` · ${formatTime(el.time)}` : '' }}</text>
              </view>
            </view>
            <view class="remake-slot__actions">
              <text class="remake-slot__status">{{ elementImages(el).length ? '已选替换' : '保留原片' }}</text>
              <button v-if="elementImages(el).length" class="remake-material-action" @click="cancelElementReplacement(el)">取消替换</button>
              <text class="remake-material-action" role="button" @click="supplementElement(el.kind, el)" tabindex="0" @keydown.enter.stop.prevent="supplementElement(el.kind, el)" @keydown.space.stop.prevent="supplementElement(el.kind, el)">关联镜头</text>
            </view>
            <view class="remake-slot__images">
              <view v-for="img in elementImages(el)" :key="img.url" class="remake-photo">
                <view class="remake-photo__preview" role="button" :aria-label="`预览${el.label || group.label}参考图片`" @click="previewMaterial(img)" tabindex="0" @keydown.enter.stop.prevent="previewMaterial(img)" @keydown.space.stop.prevent="previewMaterial(img)">
                  <image :src="img.localPath || img.url" mode="aspectFill" :alt="`${el.label || group.label}参考图片`" />
                </view>
                <text class="remake-photo__primary" role="button" aria-label="设为主参考图" :aria-pressed="remake.slotBindings[el.id]?.url === img.url" @click="setPrimaryImage(el, img)" tabindex="0" @keydown.enter.stop.prevent="setPrimaryImage(el, img)" @keydown.space.stop.prevent="setPrimaryImage(el, img)">{{ remake.slotBindings[el.id]?.url === img.url ? '主参考图' : '设为主图' }}</text>
                <view class="remake-photo__remove" role="button" aria-label="删除此参考图片" @click="removeElementImage(img)" tabindex="0" @keydown.enter.stop.prevent="removeElementImage(img)" @keydown.space.stop.prevent="removeElementImage(img)"><AppIcon name="close" :size="12" color="#FFFFFF" /></view>
              </view>
              <view class="remake-photo remake-photo--add" role="button" :aria-label="`从我的素材为${el.label || group.label}选择图片`" @click="chooseReplaceImage(el)" tabindex="0" @keydown.enter.stop.prevent="chooseReplaceImage(el)" @keydown.space.stop.prevent="chooseReplaceImage(el)">
                <AppIcon name="plus" :size="22" color="#B23A2E" />
                <text>从我的素材选择</text>
              </view>
            </view>
            <text class="remake-material-action remake-slot__reuse" role="button" @click="reuseElementImage(el)" tabindex="0" @keydown.enter.stop.prevent="reuseElementImage(el)" @keydown.space.stop.prevent="reuseElementImage(el)">复用本次已选素材</text>
            <text class="remake-slot__hint">{{ elementImages(el).length ? '继续点 ＋，补充同一元素的不同角度' : '从我的素材选择替换图片，不选择则保留原片' }}</text>
          </view>
        </view>
        <text class="remake-materials__hint">共 {{ new Set(remake.replaceImages.map((image) => image.url)).size }}/8 张图片 · 不同产品分别上传到对应元素下</text>
        <text v-if="remake.replaceUploading" class="studio__replace-pct">正在上传… {{ remake.replaceProgress }}%</text>
        <view class="remake-back" role="button" aria-label="返回原视频步骤" @click="scrollToStep(0)" tabindex="0" @keydown.enter.stop.prevent="scrollToStep(0)" @keydown.space.stop.prevent="scrollToStep(0)">返回原视频 / 重新解析</view>
      </view>

      <!-- AI 拆解分镜：上传对标视频后拆解原片结构，可逐镜编辑画面描述（看得见的复刻 + 可控复刻） -->
      <view v-if="remake.refVideo && remake.step === 2 && remake.showAdvanced" class="studio__card studio__shots">
        <view class="studio__card-title">
          <text>AI 拆解分镜</text>
          <text class="studio__badge">免费 · 不扣额度</text>
        </view>

        <view v-if="!remake.shots.length && !remake.decomposing" class="studio__shots-empty">
          <text class="studio__shots-empty-text">拆解后你能看到每个镜头的画面与口播，并微调描述</text>
          <view class="studio__shots-btn" role="button" aria-label="AI 拆解分镜" @click="startDeconstruct" tabindex="0" @keydown.enter.stop.prevent="startDeconstruct" @keydown.space.stop.prevent="startDeconstruct">
            <AppIcon name="layers" :size="16" color="#FFFFFF" :stroke-width="2" />
            <text>AI 拆解分镜</text>
          </view>
        </view>

        <text v-else-if="remake.decomposing" class="studio__shots-loading">拆解中…</text>

        <view v-else class="studio__shots-list">
          <view v-for="shot in remake.shots" :key="shot.index" class="studio__shot">
            <image
              v-if="shot.frame"
              class="studio__shot-frame"
              :src="shot.frame"
              mode="aspectFill"
              aria-hidden="true"
            />
            <view class="studio__shot-body">
              <view class="studio__shot-head">
                <text class="studio__shot-no">镜头 {{ shot.index + 1 }}</text>
                <text class="studio__shot-time">{{ shotTimeText(shot) }}</text>
              </view>
              <AppTextarea
                v-model="shot.description"
                :aria-label="`原片镜头 ${shot.index + 1} 画面描述`"
                class="studio__shot-input"
                placeholder="此镜头没有逆推描述，建议补上画面与运镜…"
                placeholder-class="app-placeholder"
                :maxlength="300"
              />
              <text v-if="shot.narration" class="studio__shot-narration">原片口播：{{ shot.narration }}</text>
            </view>
          </view>
          <view class="studio__shots-redo" role="button" aria-label="重新拆解分镜" @click="startDeconstruct" tabindex="0" @keydown.enter.stop.prevent="startDeconstruct" @keydown.space.stop.prevent="startDeconstruct">
            <text>重新拆解</text>
          </view>
        </view>
      </view>

      <!-- 一句话目标（小白主入口）：用大白话描述想做成什么样，选填 -->
      <view v-if="remake.step === 2" class="remake-summary">
        <view class="remake-summary__head"><text>你的复刻素材</text><text role="button" aria-label="返回修改素材" @click="scrollToStep(1)" tabindex="0" @keydown.enter.stop.prevent="scrollToStep(1)" @keydown.space.stop.prevent="scrollToStep(1)">修改素材</text></view>
        <view class="remake-summary__counts"><text v-for="group in elementGroups" :key="group.kind">{{ group.label }} {{ group.replaced }} / {{ group.elements.length }}</text></view>
        <text class="remake-slot__hint">已替换 / 原片元素 · 未替换的内容尽量保留原片</text>
        <view v-for="group in elementGroups" :key="`${group.kind}-summary`" class="remake-summary__counts"><text>{{ group.label }}：{{ group.replaced ? `替换 ${group.replaced} 项` : '保留原片' }}</text></view>
        <text class="remake-slot__hint">参考视频：{{ remake.refVideo?.name || '已选视频' }}</text>
        <text class="remake-slot__hint">生成式复刻可能改变人物细节与动作，不是逐帧锁定的抠像换背景。</text>
      </view>
      <view v-show="remake.step === 2" id="remake-goal" class="studio__card studio__goal">
        <view class="studio__card-title">
          <text>补充你的要求</text>
          <text class="studio__sub-hint">选填，想做成什么样</text>
        </view>
        <AppTextarea
          v-model="remake.goal"
          class="studio__textarea"
          :placeholder="goalPlaceholder"
          placeholder-class="app-placeholder"
          :maxlength="200"
        />
        <view class="studio__goal-chips">
          <view
            v-for="chip in goalExamples"
            :key="chip"
            class="studio__chip"
            role="button"
            :aria-label="`使用目标示例：${chip}`"
            @click="remake.goal = chip"
           tabindex="0" @keydown.enter.stop.prevent="remake.goal = chip" @keydown.space.stop.prevent="remake.goal = chip">
            <text>{{ chip }}</text>
          </view>
        </view>
        <text class="studio__textarea-count">{{ (remake.goal || '').length }}/200</text>
      </view>

      <view v-if="remake.step === 2 && !isAction" class="studio__card">
        <view class="studio__card-title"><text>产品介绍文案</text><text class="studio__sub-hint">可修改，确认后用于生成</text></view>
        <text v-if="copyLoading" class="remake-feedback">正在识别素材并准备文案…</text>
        <text v-else-if="preparedCopy.error" class="remake-feedback remake-feedback__error">{{ preparedCopy.error }}</text>
        <text v-else-if="!remake.replaceImages.length" class="remake-feedback">没有替换素材时默认保留原片口播；你也可以手动填写新文案。</text>
        <view v-if="!copyLoading">
          <view class="studio__copy-field">
            <text class="remake-slot__hint">大标题</text>
            <AppField v-model="preparedCopy.title" class="app-field" aria-label="文案大标题" :maxlength="20" placeholder="视频标题（选填）" placeholder-class="app-placeholder" />
          </view>
          <view class="studio__copy-field">
            <text class="remake-slot__hint">副标题</text>
            <AppField v-model="preparedCopy.subtitle" class="app-field" aria-label="文案副标题" :maxlength="30" placeholder="补充介绍（选填）" placeholder-class="app-placeholder" />
          </view>
          <view class="studio__copy-field">
            <text class="remake-slot__hint">口播文案</text>
            <AppTextarea v-model="preparedCopy.script" aria-label="产品介绍口播" class="studio__textarea" :maxlength="500" placeholder="识别完成后可在这里修改，也可手动填写" placeholder-class="app-placeholder" />
          </view>
          <view v-if="(preparedCopy.script.trim() || preparedCopy.noNarration) && preparedCopy.source !== copySourceKey()" class="remake-back" role="button" aria-label="确认使用当前文案" @click="confirmManualCopy" tabindex="0" @keydown.enter.stop.prevent="confirmManualCopy" @keydown.space.stop.prevent="confirmManualCopy">确认使用当前文案</view>
        </view>
        <view v-if="remake.replaceImages.length && !copyLoading" class="remake-back" role="button" aria-label="重新生成产品介绍文案" @click="prepareRemakeCopy" tabindex="0" @keydown.enter.stop.prevent="prepareRemakeCopy" @keydown.space.stop.prevent="prepareRemakeCopy">{{ preparedCopy.source ? '重新生成（会替换当前文案）' : '识别素材并生成文案' }}</view>
        <text class="remake-slot__hint">提示词可以留空。请核对文案，不确定的价格、成分与功效不会主动补写。</text>
      </view>

      <!-- 创意档位（行内精简分段，与九宫格模式共用同一份后端档位） -->
      <view v-show="remake.step === 2 && !isAction" class="studio__quality-row">
        <text class="studio__quality-label">创意档位</text>
        <view class="studio__segment studio__segment--pill">
          <view
            v-for="level in creativeLevels"
            :key="level.key"
            class="studio__pill"
            :class="{ 'studio__pill--active': remake.creative === level.key }"
            role="button"
            :aria-label="`创意档位：${level.label}`"
            @click="remake.creative = level.key"
           tabindex="0" @keydown.enter.stop.prevent="remake.creative = level.key" @keydown.space.stop.prevent="remake.creative = level.key">
            <text>{{ level.label }}</text>
            <text
              v-if="remake.creative === level.key && level.key === REMOTE_DEFAULT_CREATIVE"
              class="studio__rec"
            >推荐</text>
          </view>
        </view>
      </view>

      <!-- 高级选项：仅保留后端真实存在的生成参数 -->
      <view v-show="remake.step === 2" class="studio__card studio__card--flush">
        <view class="studio__collapse-head" role="button" aria-label="展开或收起高级选项" :aria-expanded="remake.showAdvanced" @click="remake.showAdvanced = !remake.showAdvanced" tabindex="0" @keydown.enter.stop.prevent="remake.showAdvanced = !remake.showAdvanced" @keydown.space.stop.prevent="remake.showAdvanced = !remake.showAdvanced">
          <view class="studio__collapse-title">
            <AppIcon name="sparkles" :size="18" color="#6B6357" />
            <text>高级选项</text>
          </view>
          <view class="studio__collapse-right">
            <text class="studio__badge">不动也能出片 · 共 {{ ADVANCED_COUNT }} 项</text>
            <AppIcon
              name="chevron-down"
              :size="18"
              color="#6B6357"
              :class="remake.showAdvanced ? 'studio__arrow--open' : ''"
            />
          </view>
        </view>

        <view v-if="remake.showAdvanced" class="studio__collapse-body app-enter">
          <!-- 主角表现（上传了人物图时可选）：让换上去的新主角以跳舞/讲解方式表演 -->
          <view v-if="!isAction && remake.replaceImages.some((i) => i.role === 'person')" class="studio__sub">
            <view class="studio__sub-title">
              <text>主角表现</text>
              <text class="studio__sub-hint">换人物时选填</text>
            </view>
            <view class="studio__segment studio__segment--pill">
              <view
                v-for="la in leadActs"
                :key="la.key"
                class="studio__pill"
                :class="{ 'studio__pill--active': remake.leadAct === la.key }"
                role="button"
                :aria-label="`主角表现：${la.label}`"
                @click="remake.leadAct = remake.leadAct === la.key ? '' : la.key"
               tabindex="0" @keydown.enter.stop.prevent="remake.leadAct = remake.leadAct === la.key ? '' : la.key" @keydown.space.stop.prevent="remake.leadAct = remake.leadAct === la.key ? '' : la.key">
                <text>{{ la.label }}</text>
              </view>
            </view>
          </view>

          <!-- 视频时长 -->
          <view class="studio__row">
            <text class="studio__row-label">视频时长</text>
            <view class="studio__segment studio__segment--sm">
              <view
                v-for="item in durationOptions"
                :key="item"
                class="studio__seg"
                :class="{ 'studio__seg--active': remake.duration === item }"
                role="button"
                :aria-label="`视频时长：${item}秒`"
                @click="remake.duration = item"
               tabindex="0" @keydown.enter.stop.prevent="remake.duration = item" @keydown.space.stop.prevent="remake.duration = item">
                <text>{{ item }}s</text>
              </view>
            </view>
          </view>

          <!-- 画幅比例 -->
          <view class="studio__row" role="button" aria-label="选择画幅比例" @click="pickWith(ratioOptions, (v) => (remake.ratio = v))" tabindex="0" @keydown.enter.stop.prevent="pickWith(ratioOptions, (v) => (remake.ratio = v))" @keydown.space.stop.prevent="pickWith(ratioOptions, (v) => (remake.ratio = v))">
            <text class="studio__row-label">画幅比例</text>
            <view class="studio__row-value">
              <text>{{ remake.ratio || '--' }}</text>
              <AppIcon name="chevron-right" :size="16" color="#6B6357" />
            </view>
          </view>

          <!-- 清晰度 -->
          <view class="studio__row" role="button" aria-label="选择清晰度" @click="pickWith(resolutionOptions, (v) => (remake.resolution = v))" tabindex="0" @keydown.enter.stop.prevent="pickWith(resolutionOptions, (v) => (remake.resolution = v))" @keydown.space.stop.prevent="pickWith(resolutionOptions, (v) => (remake.resolution = v))">
            <text class="studio__row-label">清晰度</text>
            <view class="studio__row-value">
              <text>{{ remake.resolution || '--' }}</text>
              <AppIcon name="chevron-right" :size="16" color="#6B6357" />
            </view>
          </view>

          <!-- 复刻形态（默认不指定，沿用原片结构） -->
          <view v-if="!isAction" class="studio__row" role="button" aria-label="选择复刻形态" @click="pickWith(formatOptions, (v) => (remake.format = v))" tabindex="0" @keydown.enter.stop.prevent="pickWith(formatOptions, (v) => (remake.format = v))" @keydown.space.stop.prevent="pickWith(formatOptions, (v) => (remake.format = v))">
            <text class="studio__row-label">复刻形态</text>
            <view class="studio__row-value">
              <text>{{ formatLabel }}</text>
              <AppIcon name="chevron-right" :size="16" color="#6B6357" />
            </view>
          </view>

          <!-- 开头钩子 -->
          <view v-if="!isAction" class="studio__row" role="button" aria-label="选择开头钩子" @click="pickWith(hookOptions, (v) => (remake.hookBoost = v))" tabindex="0" @keydown.enter.stop.prevent="pickWith(hookOptions, (v) => (remake.hookBoost = v))" @keydown.space.stop.prevent="pickWith(hookOptions, (v) => (remake.hookBoost = v))">
            <view class="studio__row-label">
              <text>开头钩子</text>
              <AppIcon name="info" :size="14" color="#9C9488" />
            </view>
            <view class="studio__row-value">
              <text>{{ hookLabel }}</text>
              <AppIcon name="chevron-right" :size="16" color="#6B6357" />
            </view>
          </view>

          <!-- 真人素材处理 -->
          <view class="studio__row" role="button" aria-label="选择真人素材处理方式" @click="pickWith(REAL_PERSON_OPTIONS, (v) => (remake.realPerson = v))" tabindex="0" @keydown.enter.stop.prevent="pickWith(REAL_PERSON_OPTIONS, (v) => (remake.realPerson = v))" @keydown.space.stop.prevent="pickWith(REAL_PERSON_OPTIONS, (v) => (remake.realPerson = v))">
            <text class="studio__row-label">真人素材处理</text>
            <view class="studio__row-value">
              <text>{{ realPersonLabel }}</text>
              <AppIcon name="chevron-right" :size="16" color="#6B6357" />
            </view>
          </view>

          <!-- 去水印 -->
          <view class="studio__row" role="button" aria-label="选择去水印方式" @click="pickWith(WATERMARK_OPTIONS, (v) => (remake.watermark = v))" tabindex="0" @keydown.enter.stop.prevent="pickWith(WATERMARK_OPTIONS, (v) => (remake.watermark = v))" @keydown.space.stop.prevent="pickWith(WATERMARK_OPTIONS, (v) => (remake.watermark = v))">
            <text class="studio__row-label">去水印</text>
            <view class="studio__row-value">
              <text>{{ watermarkLabel }}</text>
              <AppIcon name="chevron-right" :size="16" color="#6B6357" />
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- ============ 九宫格出片表单（图片九宫格成片） ============ -->
    <view v-show="mode === 'grid'" class="studio__form">
      <!-- 三模式切换：提示词生成 / 上传9张拼合 / 上传1张分割 -->
      <view class="studio__card studio__card--flush">
        <view class="studio__segment studio__segment--pill">
          <view
            v-for="gm in gridModes"
            :key="gm.key"
            class="studio__pill"
            :class="{ 'studio__pill--active': grid.subMode === gm.key }"
            role="button"
            :aria-label="`九宫格模式：${gm.label}`"
            @click="grid.subMode = gm.key"
           tabindex="0" @keydown.enter.stop.prevent="grid.subMode = gm.key" @keydown.space.stop.prevent="grid.subMode = gm.key">
            <text>{{ gm.label }}</text>
          </view>
        </view>
      </view>

      <!-- 模式1:提示词生成九宫格 -->
      <view v-if="grid.subMode === 'prompt'" class="studio__card">
        <view class="studio__card-title">
          <text>画面描述</text>
          <text class="studio__required">*</text>
        </view>
        <AppTextarea
          v-model="grid.prompt"
          class="studio__textarea"
          placeholder="描述你想要的九宫格画面，AI 将生成 9 个不同构图/风格的照片并拼成 3×3"
          placeholder-class="app-placeholder"
          :maxlength="2000" aria-label="九宫格画面描述"/>
        <text class="studio__textarea-count">{{ (grid.prompt || '').length }}/2000</text>
      </view>

      <!-- 模式2:上传 9 张拼合 -->
      <view v-if="grid.subMode === 'upload'" class="studio__card">
        <view class="studio__card-title">
          <text>上传九宫格图片</text>
        </view>
        <view class="studio__grid">
          <view
            v-for="(cell, index) in grid.images"
            :key="index"
            class="studio__cell"
            :class="{ 'studio__cell--filled': !!cell }"
            role="button"
            :aria-label="cell ? `第${index + 1}张图片，点击管理` : `添加第${index + 1}张图片`"
            @click="handleGridCell(index)"
           tabindex="0" @keydown.enter.stop.prevent="handleGridCell(index)" @keydown.space.stop.prevent="handleGridCell(index)">
            <image
              v-if="cell"
              class="studio__cell-img"
              :src="cell.localPath || cell.url"
              mode="aspectFill"
              aria-hidden="true"
            />
            <view v-else class="studio__cell-content">
              <text v-if="grid.uploadingIndex === index" class="studio__cell-pct">
                {{ grid.uploadProgress }}%
              </text>
              <template v-else>
                <AppIcon name="plus" :size="24" color="#9C9488" />
                <text class="studio__cell-index">{{ index + 1 }}</text>
              </template>
            </view>
          </view>
        </view>
        <text class="studio__grid-hint">按顺序上传 9 张图片，空缺格将留白，最终拼成一张九宫格图</text>
      </view>

      <!-- 模式3:上传一张九宫格拆分 -->
      <view v-if="grid.subMode === 'split'" class="studio__card">
        <view class="studio__card-title">
          <text>上传九宫格照片</text>
          <text class="studio__required">*</text>
        </view>
        <view
          class="studio__upload studio__upload--split"
          role="button"
          aria-label="上传或管理九宫格照片"
          @click="handleSplitTap"
         tabindex="0" @keydown.enter.stop.prevent="handleSplitTap" @keydown.space.stop.prevent="handleSplitTap">
          <image
            v-if="grid.splitImage"
            class="studio__upload-img"
            :src="grid.splitImage.localPath || grid.splitImage.url"
            mode="aspectFill"
            aria-hidden="true"
          />
          <text v-else-if="grid.splitUploading" class="studio__upload-pct">
            {{ grid.splitProgress }}%
          </text>
          <template v-else>
            <view class="studio__upload-icon">
              <AppIcon name="image" :size="28" color="#B23A2E" />
            </view>
            <text class="studio__upload-title">点击上传九宫格照片</text>
            <text class="studio__upload-hint">将按 3×3 拆分为 9 张单图</text>
          </template>
        </view>
      </view>

      <!-- 更多设置：画幅 / 清晰度 -->
      <view class="studio__card studio__card--flush">
        <view class="studio__collapse-head" role="button" aria-label="展开或收起更多设置" :aria-expanded="grid.showMore" @click="grid.showMore = !grid.showMore" tabindex="0" @keydown.enter.stop.prevent="grid.showMore = !grid.showMore" @keydown.space.stop.prevent="grid.showMore = !grid.showMore">
          <view class="studio__collapse-title">
            <AppIcon name="settings" :size="20" color="#6B6357" />
            <text>更多设置</text>
          </view>
          <AppIcon
            name="chevron-down"
            :size="20"
            color="#6B6357"
            :class="grid.showMore ? 'studio__arrow--open' : ''"
          />
        </view>

        <view v-if="grid.showMore" class="studio__collapse-body app-enter">
          <view class="studio__row" role="button" @click="pickWith(ratioOptions, (v) => (grid.ratio = v))" tabindex="0" @keydown.enter.stop.prevent="pickWith(ratioOptions, (v) => (grid.ratio = v))" @keydown.space.stop.prevent="pickWith(ratioOptions, (v) => (grid.ratio = v))">
            <text class="studio__row-label">画幅比例</text>
            <view class="studio__row-value">
              <text>{{ grid.ratio || '--' }}</text>
              <AppIcon name="chevron-right" :size="16" color="#6B6357" />
            </view>
          </view>

          <view class="studio__row" role="button" @click="pickWith(resolutionOptions, (v) => (grid.resolution = v))" tabindex="0" @keydown.enter.stop.prevent="pickWith(resolutionOptions, (v) => (grid.resolution = v))" @keydown.space.stop.prevent="pickWith(resolutionOptions, (v) => (grid.resolution = v))">
            <text class="studio__row-label">清晰度</text>
            <view class="studio__row-value">
              <text>{{ grid.resolution || '--' }}</text>
              <AppIcon name="chevron-right" :size="16" color="#6B6357" />
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 底部生成栏：叠在底部导航之上，预估价与后端 estimate 同源 -->
    <view id="remake-generate" class="studio__generate">
      <view v-if="mode === 'remake' && remake.step < 2" class="studio__cost">
        <text class="studio__cost-label">第 {{ remake.step + 1 }} 步 / 共 3 步</text>
        <text class="remake-footer-hint">{{ remake.step === 0 ? '先了解原片' : '让素材一一对应' }}</text>
      </view>
      <view v-else class="studio__cost">
        <text class="studio__cost-label">预估消耗</text>
        <text class="studio__cost-value">{{ costText }} <text class="studio__cost-unit">额度</text></text>
      </view>
      <view
        class="studio__submit app-btn-brand"
        :class="{ 'studio__submit--loading': submitting || remake.detecting || remake.replaceUploading }"
        role="button"
        :aria-label="primaryActionLabel"
        :aria-disabled="submitting || remake.detecting || remake.replaceUploading"
        @click="handlePrimaryAction"
       tabindex="0" @keydown.enter.stop.prevent="handlePrimaryAction" @keydown.space.stop.prevent="handlePrimaryAction">
        <AppIcon name="zap" :size="20" color="#FFFFFF" :stroke-width="2.5" />
        <text>{{ primaryActionLabel }}</text>
      </view>
    </view>

    <AppTabBar active="create" />

    <!-- 生成进度浮层：提交后就地展示，抖音式"看着它出片"，不强制跳走 -->
    <view v-if="gen.visible" class="gen-pop">
      <view class="gen-pop__mask" aria-hidden="true" @click="closeGen" />
      <view class="gen-pop__sheet app-enter" role="dialog" aria-modal="true" aria-label="生成进度" @click.stop @keydown.esc.stop.prevent="closeGen">
        <view class="gen-pop__head">
          <text class="gen-pop__title">
            {{ genStatus.key === 'completed' ? '成片已生成' : genStatus.key === 'failed' ? '生成失败' : '正在生成' }}
          </text>
          <view class="gen-pop__close" role="button" aria-label="关闭" @click="closeGen" tabindex="0" @keydown.enter.stop.prevent="closeGen" @keydown.space.stop.prevent="closeGen">
            <AppIcon name="close" :size="18" color="#6B6357" :stroke-width="2.5" />
          </view>
        </view>

        <!-- 进行中：进度环 + 阶段 + 进度条 -->
        <view v-if="genStatus.key === 'processing'" class="gen-pop__body">
          <view class="gen-ring">
            <view class="gen-ring__track" />
            <view class="gen-ring__spin gen-ring__spin--outer" />
            <view class="gen-ring__spin gen-ring__spin--inner" />
            <text class="gen-ring__value">{{ genProgress }}%</text>
          </view>
          <text class="gen-pop__phase">{{ workStageText(gen.task ? gen.task.progress : 0) }}</text>
          <view class="gen-bar">
            <view class="gen-bar__fill" :style="{ transform: `scaleX(${genProgress / 100})` }" />
          </view>
          <text class="gen-pop__remain">{{ gen.task ? workRemainingText(gen.task) : '已提交，正在排队…' }}</text>
        </view>

        <!-- 失败：给出原因 + 返回修改 / 去作品页 -->
        <view v-else-if="genStatus.key === 'failed'" class="gen-pop__body">
          <view class="gen-pop__icon gen-pop__icon--fail">
            <AppIcon name="alert-circle" :size="40" color="#B23A2E" />
          </view>
          <text class="gen-pop__fail">{{ gen.task ? workFailReason(gen.task) : '生成失败，请稍后重试' }}</text>
          <view class="gen-pop__actions">
            <view class="gen-pop__btn gen-pop__btn--ghost" role="button" @click="closeGen" tabindex="0" @keydown.enter.stop.prevent="closeGen" @keydown.space.stop.prevent="closeGen">
              <text>返回修改</text>
            </view>
            <view class="gen-pop__btn gen-pop__btn--brand" role="button" @click="go('/pages/works/index')" tabindex="0" @keydown.enter.stop.prevent="go('/pages/works/index')" @keydown.space.stop.prevent="go('/pages/works/index')">
              <text>去作品页</text>
            </view>
          </view>
        </view>

        <!-- 成功：就地播放成片 + 继续创作 / 去作品页 -->
        <view v-else class="gen-pop__body">
          <view class="gen-pop__icon gen-pop__icon--ok">
            <AppIcon name="check-circle" :size="40" color="#4B7A5A" />
          </view>
          <video
            v-if="gen.task && gen.task.result_video"
            class="gen-pop__video"
            :src="gen.task.result_video"
            :controls="true"
            :autoplay="true"
            object-fit="contain"
          />
          <text v-if="gen.task?.element_review_note" class="remake-slot__hint">{{ gen.task.element_review_note }}</text>
          <view class="gen-pop__actions">
            <view class="gen-pop__btn gen-pop__btn--ghost" role="button" @click="afterGenCreate" tabindex="0" @keydown.enter.stop.prevent="afterGenCreate" @keydown.space.stop.prevent="afterGenCreate">
              <text>继续创作</text>
            </view>
            <view class="gen-pop__btn gen-pop__btn--brand" role="button" @click="go('/pages/works/index')" tabindex="0" @keydown.enter.stop.prevent="go('/pages/works/index')" @keydown.space.stop.prevent="go('/pages/works/index')">
              <text>去作品页</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { showAppModal, showAppActionSheet } from '@/utils/feedback'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import AppTextarea from '@/components/AppTextarea.vue'
import AppField from '@/components/AppField.vue'
import AppTabBar from '@/components/AppTabBar.vue'
import api from '@/api'
import { useUserStore } from '@/store/modules/user'
import { useGenConfig } from '@/composables/useGenConfig'
import { useContentPrepare } from '@/composables/useContentPrepare'
import { currentPagePath, go, toLoginPath, requireLogin } from '@/utils/navigation'
import { MAX_UPLOAD_MB, uploadMedia } from '@/utils/upload'
// 进度/状态语义与作品页同源：任务进度由 worker 回写，前端只读取并归一化展示
import {
  workStatus,
  normalizeProgress,
  workStageText,
  workRemainingText,
  workFailReason,
} from '@/utils/task'

/**
 * 创作工作台（视频复刻 / 九宫格出片）。
 *
 * 对应设计稿《创作工作台》的版面与文案，但把设计稿里没有后端字段的假数据换成了真实参数：
 * 创意档位取自 /gen-config 的 replicate_creative_levels；高级选项只保留 CreateSchema 里真实
 * 存在的字段；预估消耗来自 /v1/task/estimate（与下单扣减同源，避免「看到的价 ≠ 扣的价」）。
 * 所有素材先走 /v1/base/common/upload/file 换成可透传的绝对地址，再交给 /v1/task/create。
 *
 * 九宫格出片已改造为「图片九宫格成片」：
 *   - 提示词生成：AI 生成 9 张变体并拼成 3×3 九宫格图；
 *   - 上传 9 张拼合：用户上传 9 张图拼成一张九宫格图；
 *   - 上传 1 张拆分：用户上传一张九宫格原图，拆分为 9 张单图。
 * 统一走 /v1/task/image/create（后端 ImageCreateSchema 的 grid / split 字段）。
 */

const userStore = useUserStore()
const {
  loadGenConfig,
  creativeLevels,
  hookBoosts,
  replicateFormats,
  replicateIntents,
  leadActs,
  defaultRatio,
  defaultResolution,
  maxReferenceSeconds,
} = useGenConfig()

// 视频复刻高级选项的真实条目数（主角表现/时长/画幅/清晰度/形态/钩子/真人处理/去水印）
const ADVANCED_COUNT = 8
/** 复刻默认创意档位：忠实复刻（与桌面端/后端参考视频默认同源，小白不调参即"像原片"） */
const REMOTE_DEFAULT_CREATIVE = 'faithful'

/** 后端真人是处理策略（CreateSchema.real_person_strategy）；auto=沿用系统默认 */
const REAL_PERSON_OPTIONS = [
  { key: 'auto', label: '智能处理' },
  { key: 'stylize', label: '写实化保留' },
  { key: 'drop', label: '直接丢弃' },
]
/** 后端去水印策略（CreateSchema.remove_watermark）；auto=自动检测后分级处理 */
const WATERMARK_OPTIONS = [
  { key: 'auto', label: '自动' },
  { key: 'crop', label: '仅裁剪' },
  { key: 'delogo', label: '仅修补' },
  { key: 'off', label: '关闭' },
]

/** 九宫格固定 9 格，空位为 null */
function createGridCells() {
  return Array.from({ length: 9 }, () => null)
}

/** 图片九宫格成片的三种子模式 */
const gridModes = [
  { key: 'prompt', label: '提示词生成' },
  { key: 'upload', label: '上传9张拼合' },
  { key: 'split', label: '上传九宫格拆分' },
]

const mode = ref('remake')
const templateId = ref(null)
const templateTitle = ref('')
const submitting = ref(false)
const { loading: copyLoading, run: runContentPrepare, stop: stopContentPrepare } = useContentPrepare()
const preparedCopy = reactive({ title: '', subtitle: '', script: '', error: '', source: '', noNarration: false, speechBudget: null })
// 文案与素材、要求的快照绑定，避免旧结果覆盖用户当前内容。
let copySequence = 0

// 提交后的就地生成进度浮层：提交不强制跳走，抖音式"看着它出片"
const gen = reactive({ taskId: null, visible: false, task: null })
let genTimer = null
let deconstructTimer = null
const genStatus = computed(() => (gen.task ? workStatus(gen.task.status) : { key: 'processing', label: '生成中' }))
const genProgress = computed(() => (gen.task ? normalizeProgress(gen.task.progress) : 0))

// 两张表单各自持有本地状态：切换创作方式后回来，已填内容与设置都还在
const remake = reactive({
  replicateMode: 'action', // 默认动作复刻，不自动生成营销文案。
  step: 0, // 三步流程：原视频、分类素材、确认生成。
  parsed: false,
  analysisId: '', // 服务端解析凭证，生成时核验原片和账号。
  analysisVersion: null,
  detectError: '',
  previewError: '',
  refVideo: null, // { url, name, duration, size }
  refUploading: false,
  refProgress: 0,
  goal: '', // 一句话目标（小白主入口，选填，≤200 字）
  intent: [], // 替换意图多选：product/person/scene
  replaceImages: [], // 替换素材图（≤9）：{ url, localPath, role }
  replaceUploading: false,
  replaceProgress: 0,
  elements: [], // 原片元素识别结果（detect-elements）：{ id, kind, label, time, thumbnail }
  slotBindings: {},
  detecting: false,
  linkMode: false, // 是否展开"粘贴视频链接"输入
  linkUrl: '',
  showAdvanced: false,
  creative: '',
  duration: null,
  ratio: '',
  resolution: '',
  format: '',
  hookBoost: '',
  realPerson: 'auto',
  watermark: 'auto',
  leadAct: '', // 主角表现（仅换人物时生效）：dance=跳舞律动 / pitch=推广种草
  // —— AI 拆解分镜（看得见的复刻 + 可控复刻）——
  deconstructId: null, // 拆解任务 id（轮询 /detail 读取分镜）
  decomposing: false, // 拆解进行中
  shots: [], // 归一化分镜：[{ index, start, end, duration, narration, description, frame }]
})

const isAction = computed(() => remake.replicateMode === 'action')
/** 切换模式保留通用素材，清除带货专属草稿前先确认，并失效在途文案请求。 */
function changeReplicateMode(next) {
  if (next === remake.replicateMode || submitting.value || remake.detecting || remake.refUploading || remake.replaceUploading) return
  const apply = () => {
    resetPreparedCopy()
    remake.replicateMode = next
    remake.step = 0
    remake.goal = ''
    remake.intent = []
  }
  if (remake.goal || preparedCopy.title || preparedCopy.subtitle || preparedCopy.script || remake.replaceImages.some((img) => img.role === 'product')) {
    showAppModal({ title: '切换复刻方式', content: '切换后将清空文案和补充要求。已选素材保留，动作复刻不会提交商品素材。', success: ({ confirm }) => { if (confirm) apply() } })
  } else apply()
}

const grid = reactive({
  subMode: 'prompt', // 图片九宫格子模式:prompt/upload/split
  prompt: '',
  images: createGridCells(),
  uploadingIndex: -1,
  uploadProgress: 0,
  splitImage: null, // { url, localPath }
  splitUploading: false,
  splitProgress: 0,
  showMore: false,
  ratio: '',
  resolution: '',
})

// 对标视频更换后，旧的分镜拆解结果随之失效，清掉避免误导后续生成
watch(() => remake.refVideo, () => {
  resetShots()
  remake.slotBindings = {}
  remake.elements = []
  remake.replaceImages = []
  remake.parsed = false
  remake.analysisId = ''
  remake.analysisVersion = null
  remake.detectError = ''
  remake.step = 0
  detectSequence += 1
  remake.detecting = false
})

// 请求版本用于防止更换视频后，旧解析响应覆盖新视频。
let detectSequence = 0
const stepHeadings = computed(() => [
  { title: '先选一条你想复刻的视频', desc: isAction.value ? '参考原片动作、节奏和运镜，不需要填写产品文案。' : '参考商品展示方式，按需替换商品、人物与场景。' },
  { title: '想替换什么？', desc: '从我的素材选择参考图，不替换的内容尽量保留原片。' },
  { title: isAction.value ? '确认设置并生成' : '确认文案与生成设置', desc: '补充要求选填。生成式复刻不能保证人物与动作逐帧不变。' },
])
/** 动作只展示人物场景，带货优先商品；识别结果不改变创作模式。 */
const elementGroups = computed(() => (isAction.value ? ['person', 'scene'] : ['product', 'person', 'scene']).map((kind) => {
  const elements = remake.elements.filter((el) => el.kind === kind)
  return { kind, label: kindLabel(kind), elements, replaced: elements.filter((el) => elementImages(el).length).length }
}))
/** 底部主操作随步骤变化，不允许跳过解析与素材确认。 */
const primaryActionLabel = computed(() => {
  if (submitting.value) return '提交中…'
  if (mode.value !== 'remake') return '立即生成'
  if (remake.detecting) return '正在解析…'
  if (remake.replaceUploading) return '素材上传中…'
  return ['解析视频', '确认素材，下一步', '生成视频'][remake.step]
})

const estimate = ref(null)
let estimateTimer = null
let estimateSeq = 0

const gridCount = computed(() => grid.images.filter(Boolean).length)

/** 计费相关输入：任一变化即重新预估（与后端 estimate 的入参一一对应） */
const billingKey = computed(() =>
  [
    mode.value,
    remake.refVideo ? 'v' : '',
    remake.replaceImages.length ? 'p' : '',
    grid.subMode,
    gridCount.value,
    remake.duration ?? '',
    remake.ratio,
    remake.resolution,
    grid.ratio,
    grid.resolution,
    templateId.value ?? '',
  ].join('|')
)

/** 时长档位 / 画幅 / 清晰度全部来自 estimate.options，前端不写死任何档位 */
const durationOptions = computed(() => estimate.value?.options?.durations || [])
const ratioOptions = computed(() =>
  (estimate.value?.options?.ratios || []).map((v) => ({ key: v, label: v }))
)
const resolutionOptions = computed(() =>
  (estimate.value?.options?.resolutions || []).map((v) => ({ key: v, label: v }))
)
// 「不指定」不是后端白名单取值，而是「不传该字段、沿用原片结构」的显式表述
const formatOptions = computed(() => [
  { key: '', label: '不指定' },
  ...replicateFormats.value.map((o) => ({ key: o.key, label: o.label })),
])
// 开头钩子不传时由后端按创意档位联动兜底，这里把「自动生成」显式呈现给用户
const hookOptions = computed(() => [
  { key: '', label: '自动生成' },
  ...hookBoosts.value.map((o) => ({ key: o.key, label: o.label })),
])

/** 是否选中「美食探店」复刻形态：餐饮语境下把引导话术换成菜品/门店口语，降低餐饮用户的表达门槛 */
const isFoodShop = computed(() => remake.format === 'food_shop')
/** 餐饮形态下的角色口语化称谓：菜品/门店/出镜人（key 与后端替换意图同源，仅展示文案不同） */
const FOOD_ROLE_LABELS = { product: '菜品', person: '出镜人', scene: '门店' }
/** 一句话目标示例 chip（小白主入口引导）：餐饮形态给餐饮话术，其余保持通用 */
const goalExamples = computed(() =>
  isAction.value ? ['保留原片动作与节奏', '只替换场景，保留人物', '保留原片运镜'] : isFoodShop.value
    ? ['换成我家招牌菜', '突出门店人气和烟火气', '更有食欲、适合发抖音团购']
    : ['更电影感', '适合发小红书', '更有反转', '画面更精致'],
)
/** 一句话目标占位提示：餐饮形态给餐饮示例，其余保持通用 */
const goalPlaceholder = computed(() =>
  isAction.value ? '例如：只换成海边，保留原片舞蹈动作与运镜' : isFoodShop.value
    ? '例如：把菜品换成我家招牌菜、突出门店人气；或更有食欲、更适合发抖音'
    : '例如：换成我的产品做成口播带货；或更电影感、适合发小红书',
)

// 替换素材可标注的角色（与替换意图同源，来自后端 replicate_intents）；
// 后端未下发时回退内置白名单，保证标注入口始终可用
const roleOptions = computed(() => {
  const base = replicateIntents.value.length
    ? replicateIntents.value
    : [
        { key: 'product', label: '商品' },
        { key: 'person', label: '人物' },
        { key: 'scene', label: '场景' },
      ]
  if (!isFoodShop.value) return base
  return base.map((o) => ({ ...o, label: FOOD_ROLE_LABELS[o.key] || o.label }))
})
function roleLabel(role) {
  const hit = roleOptions.value.find((o) => o.key === role)
  return hit ? hit.label : '未标注'
}


/** 从「键 → 文案」选项里取展示文案，取不到回退默认文案 */
function labelOf(options, key, fallback) {
  const hit = options.find((o) => o.key === key)
  return hit ? hit.label : fallback
}

const formatLabel = computed(() => labelOf(formatOptions.value, remake.format, '不指定'))
const hookLabel = computed(() => labelOf(hookOptions.value, remake.hookBoost, '自动生成'))
const realPersonLabel = computed(() => labelOf(REAL_PERSON_OPTIONS, remake.realPerson, '智能处理'))
const watermarkLabel = computed(() => labelOf(WATERMARK_OPTIONS, remake.watermark, '自动'))

/** 预估消耗：拿不到后端结果时展示占位符，绝不编造数字 */
const costText = computed(() => {
  const cost = estimate.value?.cost
  return cost === null || cost === undefined ? '--' : String(cost)
})

/** 已上传视频的「时长 / 大小」，缺一项就只显示另一项 */
const refVideoMetaText = computed(() => {
  const file = remake.refVideo
  if (!file) return ''
  const parts = []
  if (file.duration) parts.push(`${file.duration}s`)
  const size = formatSize(file.size)
  if (size) parts.push(size)
  return parts.join(' / ')
})

function toast(title) {
  uni.showToast({ title, icon: 'none' })
}

/** 路径取文件名（H5 拿不到 File 对象时的兜底展示） */
function fileNameOf(path) {
  const text = String(path || '').split('?')[0]
  const idx = text.lastIndexOf('/')
  return idx >= 0 ? text.slice(idx + 1) : text
}

function formatSize(bytes) {
  const num = Number(bytes || 0)
  if (!num) return ''
  if (num >= 1024 * 1024) return `${(num / 1024 / 1024).toFixed(1)}MB`
  return `${Math.max(1, Math.round(num / 1024))}KB`
}

// ---------- 上传 ----------

/** 从本人素材库选择已上传的视频，复用原地址，不重复上传或自动解析。 */
function chooseRefVideo() {
  if (!requireLogin()) return
  uni.navigateTo({
    url: '/pages/materials/index?mode=select&kind=video',
    events: {
      materialSelected: applyReferenceMaterial,
    },
    fail: () => toast('素材库打开失败，请稍后重试'),
  })
}

/** 校验素材类型及已知大小、时长；历史未知时长交由后端解析校验。 */
function applyReferenceMaterial(item) {
  if (item?.kind !== 'video' || !item.url) {
    toast('请选择已上传的视频素材')
    return
  }
  const duration = Number(item.duration || 0)
  const size = Number(item.size || 0)
  if (duration > maxReferenceSeconds.value) {
    toast(`视频时长不能超过 ${maxReferenceSeconds.value}s`)
    return
  }
  if (size > MAX_UPLOAD_MB * 1024 * 1024) {
    toast(`视频不能超过 ${MAX_UPLOAD_MB}MB`)
    return
  }
  remake.refVideo = {
    url: item.url,
    name: item.filename || '对标视频',
    duration,
    size,
  }
}

/** 重新选择成功后才替换原视频，取消选择保留当前流程。 */
function retryRefVideo() {
  chooseRefVideo()
}

/** 用户主动解析原片；仅当前视频的有效结果可以推进到素材步骤。 */
async function runDetectElements(url) {
  if (!requireLogin() || !url || remake.detecting) return
  const sequence = ++detectSequence
  remake.detectError = ''
  remake.parsed = false
  remake.analysisId = ''
  remake.analysisVersion = null
  remake.elements = []
  remake.replaceImages = []
  remake.slotBindings = {}
  resetShots()
  remake.detecting = true
  try {
    const res = await api.task.detectElements.post({ reference_video: url }, { suppressGlobalError: true, timeout: 120000 })
    if (sequence !== detectSequence || remake.refVideo?.url !== url) return
    if (res?.code !== 1 || !Array.isArray(res.data?.elements)) throw new Error(res?.message || '解析失败，请重新尝试')
    const elements = res.data.elements.filter((el) => el.id && ['person', 'scene', 'product'].includes(el.kind))
    remake.analysisId = res.data.analysis_id
    remake.analysisVersion = res.data.analysis_version
    remake.elements = elements
    remake.replaceImages = []
    remake.slotBindings = {}
    remake.parsed = true
    remake.step = 1
    uni.pageScrollTo({ scrollTop: 0, duration: 200 })
  } catch (err) {
    if (sequence !== detectSequence) return
    console.error('识别原片元素失败', err)
    remake.detectError = err?.message || '解析失败，请检查网络后重试'
  } finally {
    if (sequence === detectSequence) remake.detecting = false
  }
}

/** 原片元素 kind → 中文（与替换意图同源：person/product/scene） */
const KIND_LABELS = { person: '人物', product: '产品', scene: '场景' }
function kindLabel(kind) {
  return KIND_LABELS[kind] || String(kind || '元素')
}

/** 秒 → mm:ss（detect-elements 的时间戳展示用） */
function formatTime(sec) {
  const s = Number(sec || 0)
  if (!s) return ''
  const m = Math.floor(s / 60)
  const r = Math.floor(s % 60)
  return `${m}:${String(r).padStart(2, '0')}`
}

function slotBindingFor(element) {
  return remake.slotBindings[element.id] || null
}

function bindElement(element) {
  if (!remake.replaceImages.length) {
    toast('请先上传替换素材')
    return
  }
  const options = remake.replaceImages.map((image, index) => `${index + 1}. ${fileNameOf(image.url) || '替换素材'}`)
  options.push('取消绑定')
  showAppActionSheet({
    itemList: options,
    success: ({ tapIndex }) => {
      if (tapIndex === options.length - 1) {
        unbindElement(element)
        return
      }
      const image = remake.replaceImages[tapIndex]
      if (image) remake.slotBindings[element.id] = image
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('绑定原片元素失败', err)
    },
  })
}

function unbindElement(element) {
  delete remake.slotBindings[element.id]
}

/** 补充漏识别元素或关联已有元素，镜头必须来自当前原片的成功拆解。 */
async function supplementElement(kind, element = null) {
  if (!remake.shots.length) {
    toast('请先拆解分镜，完成后再补充或关联元素')
    await startDeconstruct()
    return
  }
  let label = element?.label || ''
  if (!element) {
    const result = await new Promise((resolve) => showAppModal({
      title: `补充原片${kindLabel(kind)}`, editable: true,
      placeholderText: '填写原片中漏识别的元素，不用于新增原片外商品',
      success: resolve, fail: () => resolve({ confirm: false }),
    }))
    if (!result.confirm || !result.content?.trim()) return
    label = result.content.trim().slice(0, 200)
  }
  const selection = await new Promise((resolve) => showAppActionSheet({
    itemList: remake.shots.map((shot, index) => `镜头 ${index + 1} · ${shotTimeText(shot)}`),
    success: resolve, fail: () => resolve(null),
  }))
  if (!selection) return
  const analysisId = remake.analysisId
  try {
    const res = await api.task.updateAnalysis.post({
      analysis_id: analysisId, analysis_version: remake.analysisVersion,
      reference_video: remake.refVideo.url, deconstruct_id: remake.deconstructId,
      shot_index: selection.tapIndex, element_id: element?.id, kind, label,
    }, { suppressGlobalError: true })
    if (analysisId !== remake.analysisId) return
    if (!res || res.code !== 1 || !res.data) return toast(res?.message || '更新元素失败')
    remake.analysisId = res.data.analysis_id
    remake.analysisVersion = res.data.analysis_version
    remake.elements = res.data.elements
    resetPreparedCopy()
    toast('原片元素与镜头关联已更新')
  } catch (err) {
    console.error('补充原片元素失败', err)
    toast(err?.message || '更新元素失败，请重试')
  }
}

/** 为当前元素切换主参考图，不改变其他元素对同一图片的绑定。 */
function setPrimaryImage(element, image) {
  remake.slotBindings[element.id] = image
}

/** 复用同分类已上传素材，不重复上传，也不覆盖原元素绑定。 */
function reuseElementImage(element) {
  const bound = new Set(elementImages(element).map((image) => image.url))
  const candidates = [...new Map(remake.replaceImages.filter((image) => image.role === element.kind && !bound.has(image.url)).map((image) => [image.url, image])).values()]
  if (!candidates.length) return toast('暂无可复用的同分类素材，请先上传图片')
  showAppActionSheet({
    itemList: candidates.map((image, index) => `素材 ${index + 1} · ${fileNameOf(image.url)}`),
    success: ({ tapIndex }) => {
      const image = candidates[tapIndex]
      if (!image || !remake.elements.some((item) => item.id === element.id)) return
      const reused = { ...image, elementId: element.id }
      remake.replaceImages.push(reused)
      if (!remake.slotBindings[element.id]) remake.slotBindings[element.id] = reused
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('复用素材失败', err)
    },
  })
}

// ---------- AI 拆解分镜（看得见的复刻 + 可控复刻） ----------

/** 清空拆解结果（更换对标视频 / 继续创作 / 离开页面时调用） */
function resetShots() {
  remake.shots = []
  remake.deconstructId = null
  remake.decomposing = false
  stopDeconstructPoll()
}

/** 拆解结果（result_text 字符串）→ 归一化分镜数组，容错解析 */
function parseStoryboard(text) {
  if (!text) return []
  let obj = text
  if (typeof text === 'string') {
    try {
      obj = JSON.parse(text)
    } catch (err) {
      console.error('解析分镜 JSON 失败', err)
      return []
    }
  }
  const raw = Array.isArray(obj) ? obj : obj && obj.shots ? obj.shots : []
  return normalizeShots(raw)
}

/** 单条分镜归一化：补齐缺省字段，数值化时间（秒） */
function normalizeShots(raw) {
  return (raw || []).map((s) => ({
    index: Number(s.index) || 0,
    start: Number(s.start) || 0,
    end: Number(s.end) || 0,
    duration: Number(s.duration) || 0,
    narration: s.narration || '',
    description: s.description || '',
    frame: s.frame || '',
  }))
}

/** 镜头时间区间展示（保留一位小数秒，如 0.0s - 2.5s） */
function shotTimeText(shot) {
  return `${Number(shot.start).toFixed(1)}s - ${Number(shot.end).toFixed(1)}s`
}

/** 提交拆解：不扣额度，只分析原片结构；结果经 /detail 的 result_text 回读 */
async function startDeconstruct() {
  if (remake.decomposing) return
  if (!remake.refVideo) {
    toast('请先上传对标视频')
    return
  }
  if (!userStore.isLoggedIn) {
    go(toLoginPath(currentPagePath()))
    return
  }
  const sourceVideo = remake.refVideo.url
  const sequence = detectSequence
  remake.decomposing = true
  remake.shots = []
  try {
    const res = await api.task.deconstruct.post(
      {
        reference_video: remake.refVideo.url,
        intent: remake.intent.length ? remake.intent : undefined,
        goal: remake.goal && remake.goal.trim() ? remake.goal.trim().slice(0, 200) : undefined,
        format: remake.format || undefined,
        creative_level: remake.creative || undefined,
        hook_boost: remake.hookBoost || undefined,
        device: 'mobile',
      },
      { suppressGlobalError: true },
    )
    if (sequence !== detectSequence || sourceVideo !== remake.refVideo?.url) return
    if (!res || res.code !== 1 || !res.data) {
      toast(res?.message || '拆解失败，请稍后重试')
      remake.decomposing = false
      return
    }
    remake.deconstructId = res.data.id
    pollDeconstruct()
  } catch (err) {
    if (sequence !== detectSequence || sourceVideo !== remake.refVideo?.url) return
    console.error('拆解分镜失败', err)
    toast(err?.data?.message || err?.message || '拆解失败，请稍后重试')
    remake.decomposing = false
  }
}

/** 每 2s 轮询拆解任务状态，直到成功/失败 */
function pollDeconstruct() {
  stopDeconstructPoll()
  deconstructTimer = setInterval(fetchDeconstructStatus, 2000)
  fetchDeconstructStatus()
}

function stopDeconstructPoll() {
  if (deconstructTimer) {
    clearInterval(deconstructTimer)
    deconstructTimer = null
  }
}

/** 轮询拆解进度：成功解析分镜、失败给出原因并停轮询 */
async function fetchDeconstructStatus() {
  if (!remake.deconstructId) return
  const taskId = remake.deconstructId
  const sequence = detectSequence
  try {
    const res = await api.task.detail.post({ id: taskId }, { suppressGlobalError: true })
    if (taskId !== remake.deconstructId || sequence !== detectSequence) return
    if (!res || res.code !== 1 || !res.data) return
    const key = workStatus(res.data.status).key
    if (key === 'completed') {
      remake.shots = parseStoryboard(res.data.result_text)
      remake.decomposing = false
      stopDeconstructPoll()
    } else if (key === 'failed') {
      remake.decomposing = false
      stopDeconstructPoll()
      toast(res.data.fail_reason ? `拆解失败：${res.data.fail_reason}` : '拆解失败，请稍后重试')
    }
  } catch (err) {
    console.error('轮询拆解进度失败', err)
  }
}

/** 粘贴视频直链：跳过本地上传，直接作为对标视频（仅支持可直接访问的视频文件链接） */
function applyLink() {
  const url = (remake.linkUrl || '').trim()
  if (!/^https?:\/\//i.test(url)) {
    toast('请输入以 http(s) 开头的可访问视频链接')
    return
  }
  remake.linkMode = false
  remake.linkUrl = ''
  remake.refVideo = {
    url,
    name: fileNameOf(url) || '链接视频',
    duration: 0,
    size: 0,
    remote: true,
  }
}

function chooseReplaceImage(element) {
  if (!requireLogin() || remake.replaceUploading || !element?.id) return
  const sourceUrl = remake.refVideo?.url
  const analysisId = remake.analysisId
  uni.navigateTo({
    url: `/pages/materials/index?mode=select&kind=image&role=${encodeURIComponent(element.kind)}`,
    events: {
      materialSelected: (item) => {
        if (remake.refVideo?.url !== sourceUrl || remake.analysisId !== analysisId) return
        if (!remake.elements.some((el) => el.id === element.id && el.kind === element.kind)) return
        if (!item?.url || item.kind !== 'image' || item.needs_confirmation || item.role !== element.kind) {
          toast('请选择用途匹配的图片素材')
          return
        }
        if (remake.replaceImages.some((image) => image.url === item.url && image.elementId === element.id)) return
        const urls = new Set(remake.replaceImages.map((image) => image.url))
        if (!urls.has(item.url) && urls.size >= 8) {
          toast('最多选择 8 张替换素材，原视频占用一个素材名额')
          return
        }
        const img = { url: item.url, localPath: item.url, role: item.role, elementId: element.id }
        remake.replaceImages.push(img)
        if (!remake.slotBindings[element.id]) remake.slotBindings[element.id] = img
      },
    },
  })
}

function handleReplaceImageTap(idx) {
  if (remake.replaceUploading) return
  showAppActionSheet({
    itemList: ['替换', '删除'],
    success: ({ tapIndex }) => {
      if (tapIndex === 0) {
        remake.replaceImages.splice(idx, 1)
        chooseReplaceImage()
      } else if (tapIndex === 1) {
        const removed = remake.replaceImages[idx]
        remake.replaceImages.splice(idx, 1)
        if (removed) {
          Object.keys(remake.slotBindings).forEach((slotId) => {
            if (remake.slotBindings[slotId].url === removed.url) delete remake.slotBindings[slotId]
          })
        }
      }
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('替换素材操作失败', err)
    },
  })
}

/** 为某张替换图选择角色（商品/人物/场景；选中美食探店形态时显示为菜品/出镜人/门店） */
function pickRole(idx) {
  const options = roleOptions.value
  showAppActionSheet({
    itemList: options.map((o) => o.label),
    success: ({ tapIndex }) => {
      const picked = options[tapIndex]
      if (picked) remake.replaceImages[idx].role = picked.key
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择角色失败', err)
    },
  })
}

/** 登录后选择九宫格指定位置的上传素材。 */
function chooseGridImage(index) {
  if (!requireLogin()) return
  uni.chooseImage({
    count: 1,
    success: async (res) => {
      const path = res.tempFilePaths && res.tempFilePaths[0]
      if (!path) return
      grid.uploadingIndex = index
      grid.uploadProgress = 0
      try {
        const data = await uploadMedia(path, {
          onProgress: (percent) => {
            grid.uploadProgress = percent
          },
        })
        grid.images[index] = { url: data.url, localPath: path }
      } catch (err) {
        console.error('上传九宫格图片失败', err)
        toast(err?.message || '上传失败，请稍后重试')
      } finally {
        grid.uploadingIndex = -1
      }
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择九宫格图片失败', err)
    },
  })
}

function handleGridCell(index) {
  if (grid.uploadingIndex !== -1) return
  if (!grid.images[index]) {
    chooseGridImage(index)
    return
  }
  showAppActionSheet({
    itemList: ['替换', '删除'],
    success: ({ tapIndex }) => {
      if (tapIndex === 0) {
        grid.images[index] = null
        chooseGridImage(index)
      } else if (tapIndex === 1) {
        grid.images[index] = null
      }
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('九宫格图片操作失败', err)
    },
  })
}

/** 选择并上传一张九宫格原图（分割模式使用） */
function chooseSplitImage() {
  if (!requireLogin()) return
  uni.chooseImage({
    count: 1,
    success: async (res) => {
      const path = res.tempFilePaths && res.tempFilePaths[0]
      if (!path) return
      grid.splitUploading = true
      grid.splitProgress = 0
      try {
        const data = await uploadMedia(path, {
          onProgress: (percent) => {
            grid.splitProgress = percent
          },
        })
        grid.splitImage = { url: data.url, localPath: path }
      } catch (err) {
        console.error('上传九宫格原图失败', err)
        toast(err?.message || '上传失败，请稍后重试')
      } finally {
        grid.splitUploading = false
      }
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择九宫格原图失败', err)
    },
  })
}

function handleSplitTap() {
  if (grid.splitUploading) return
  if (!grid.splitImage) {
    chooseSplitImage()
    return
  }
  showAppActionSheet({
    itemList: ['替换', '删除'],
    success: ({ tapIndex }) => {
      if (tapIndex === 0) {
        grid.splitImage = null
        chooseSplitImage()
      } else if (tapIndex === 1) {
        grid.splitImage = null
      }
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('九宫格原图操作失败', err)
    },
  })
}

// ---------- 设置项选择 ----------

/** 统一用 ActionSheet 承载「行内无分段控件」的设置项，选中后回填标签 */
function pickWith(options, onPick) {
  if (!options.length) {
    toast('选项加载中，请稍后重试')
    return
  }
  showAppActionSheet({
    itemList: options.map((o) => o.label),
    success: ({ tapIndex }) => {
      const picked = options[tapIndex]
      if (picked) onPick(picked.key)
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择设置项失败', err)
    },
  })
}

// ---------- 预估 ----------

function buildEstimatePayload() {
  let payload = {}
  if (mode.value === 'grid') {
    // 图片九宫格成片统一按 image 类型预估(grid/split 均按 9 张计费)
    payload = { type: 'image', num_images: 9 }
    if (grid.subMode === 'split') payload.split = true
    else payload.grid = '3x3'
    if (grid.ratio) payload.ratio = grid.ratio
    if (grid.resolution) payload.resolution = grid.resolution
  } else {
    payload = { type: 'video' }
    payload.has_reference_video = !!remake.refVideo
    if (remake.duration) payload.duration = Number(remake.duration)
    if (remake.ratio) payload.ratio = remake.ratio
    if (remake.resolution) payload.resolution = remake.resolution
  }
  if (templateId.value) payload.template_id = templateId.value
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
    if (res && res.code === 1 && res.data) {
      estimate.value = res.data
      applyEstimateDefaults(res.data)
    } else {
      estimate.value = null
    }
  } catch (err) {
    console.error('预估生成消耗失败', err)
    if (seq === estimateSeq) estimate.value = null
  }
}

/** 用后端返回的真实档位补默认值（只在用户尚未选择时兜底） */
function applyEstimateDefaults(data) {
  const durations = data?.options?.durations
  if (remake.duration == null && Array.isArray(durations) && durations.length) {
    remake.duration = Number(data.gen_duration) || Number(durations[0])
  }
}

/** 输入变化后防抖预估，避免连续点选时打出一串请求 */
function scheduleEstimate() {
  if (estimateTimer) clearTimeout(estimateTimer)
  estimateTimer = setTimeout(runEstimate, 300)
}

watch(billingKey, scheduleEstimate)

// ---------- 模板 ----------

async function loadTemplate(id) {
  try {
    const res = await api.template.detail.post({ id }, { suppressGlobalError: true })
    if (res && res.code === 1 && res.data && res.data.title) {
      templateTitle.value = String(res.data.title).trim()
    } else {
      templateTitle.value = `模板 #${id}`
    }
  } catch (err) {
    console.error('加载模板详情失败', err)
    templateTitle.value = `模板 #${id}`
  }
}

function clearTemplate() {
  templateId.value = null
  templateTitle.value = ''
}

// ---------- 提交 ----------

/** 当前模式有效素材统一用于预检、角色和分组，避免隐藏商品仍随任务提交。 */
function activeReplaceImages() {
  return remake.replaceImages.filter((img) => !isAction.value || ['person', 'scene'].includes(img.role))
}
/** 构造模式明确且素材绑定一致的复刻请求。 */
function buildRemakePayload() {
  const images = activeReplaceImages()
  const materials = [remake.refVideo.url, ...new Set(images.map((i) => i.url))]
  const payload = {
    materials,
    replicate_mode: remake.replicateMode,
    real_person_strategy: remake.realPerson,
    remove_watermark: remake.watermark,
    device: 'mobile',
  }
  if (!isAction.value && remake.creative) payload.creative_level = remake.creative
  if (!isAction.value && remake.hookBoost) payload.hook_boost = remake.hookBoost
  if (!isAction.value && remake.format) payload.format = remake.format
  // 主角表现：仅「换人物」时生效，决定新主角以跳舞/讲解方式表演（与后端 lead_act 白名单一致）
  // 主角表现：仅在上传了「人物」角色素材时生效，决定新主角以跳舞/讲解方式表演
  if (!isAction.value && images.some((i) => i.role === 'person') && remake.leadAct) payload.lead_act = remake.leadAct
  if (remake.duration) payload.duration = Number(remake.duration)
  if (remake.ratio) payload.ratio = remake.ratio
  if (remake.resolution) payload.resolution = remake.resolution
  if (remake.goal && remake.goal.trim()) payload.goal = remake.goal.trim().slice(0, 200)
  // 替换意图：用户显式选择优先；否则由上传图的角色推导，与后端 resolve_intent 口径一致
  const intent = [...new Set(images.map((i) => i.role).filter(Boolean))]
  if (intent.length) payload.intent = intent
  // 素材图 → 角色：强提示视觉模型"这张是商品/人物/场景"，显著提升替换准确率
  const imageRoles = {}
  images.forEach((i) => {
    if (i.role) imageRoles[i.url] = i.role
  })
  if (Object.keys(imageRoles).length) payload.image_roles = imageRoles
  payload.analysis_id = remake.analysisId
  payload.analysis_version = remake.analysisVersion
  // 按元素提交素材组，同一地址可以出现在多个组内而不覆盖绑定。
  payload.material_groups = remake.elements.filter((el) => (!isAction.value || el.kind !== 'product') && elementImages(el).length).map((el) => ({
    element_id: el.id,
    images: [...new Set(elementImages(el).map((img) => img.url))],
    primary_image: remake.slotBindings[el.id]?.url || elementImages(el)[0].url,
  }))
  if (templateId.value) payload.template_id = templateId.value
  // 文案与分镜共用现有 remark 协议；规范分隔符避免口播被解析成额外指令。
  const lines = (isAction.value ? [] : [['大标题', preparedCopy.title], ['副标题', preparedCopy.subtitle], ['口播文案', preparedCopy.script]])
    .filter(([, value]) => value.trim())
    .map(([label, value]) => `${label}:${value.replace(/[;；\r\n]+/g, '，')}`)
  remake.shots.forEach((s) => {
    lines.push(`镜头${s.index + 1}(${Number(s.start).toFixed(1)}-${Number(s.end).toFixed(1)}s): ${s.description || (!isAction.value && s.narration) || '参考原片'}`)
  })
  if (lines.length) payload.remark = lines.join('\n')
  return payload
}

/** 构造图片九宫格成片建单参数（走 /v1/task/image/create） */
function buildGridPayload() {
  const payload = { device: 'mobile' }
  if (grid.subMode === 'split') {
    payload.materials = [grid.splitImage.url]
    payload.split = true
  } else if (grid.subMode === 'upload') {
    payload.materials = grid.images.filter(Boolean).map((cell) => cell.url)
    payload.grid = '3x3'
  } else {
    payload.prompt = grid.prompt.trim()
    payload.grid = '3x3'
    payload.num_images = 9
  }
  if (grid.ratio) payload.ratio = grid.ratio
  if (grid.resolution) payload.resolution = grid.resolution
  if (templateId.value) payload.template_id = templateId.value
  return payload
}

// ---------- 三步引导（首屏即把"怎么用"做成可点的状态指引） ----------
const guideSteps = computed(() => [
  { title: '参考视频', desc: '选择并解析' },
  { title: '替换素材', desc: '按需替换' },
  { title: isAction.value ? '确认生成' : '文案与生成', desc: '确认后提交' },
])
/** 引导状态按当前步骤展示，而不是以是否填写可选项判断。 */
function guideStepState(i) {
  return i < remake.step ? 'done' : i === remake.step ? 'active' : 'todo'
}
/** 步骤只允许返回；前进必须经过当前步骤的主操作校验。 */
function scrollToStep(i) {
  if (remake.detecting || remake.replaceUploading || submitting.value) return
  if (i > remake.step && !(i === 1 && remake.parsed)) return
  remake.step = i
  uni.pageScrollTo({ scrollTop: 0, duration: 200 })
}
/** 获取元素的全部参考图，支持同一产品的多角度素材。 */
function elementImages(element) {
  return remake.replaceImages.filter((img) => img.elementId === element.id)
}
/** 只解除本次元素绑定，不删除素材库记录或修改用途。 */
function cancelElementReplacement(element) {
  if (remake.replaceUploading || submitting.value) return
  remake.replaceImages = remake.replaceImages.filter((img) => img.elementId !== element.id)
  delete remake.slotBindings[element.id]
}
/** 删除图片并同步主参考图，避免提交已删除素材。 */
function removeElementImage(image) {
  if (remake.replaceUploading) return
  remake.replaceImages = remake.replaceImages.filter((img) => img !== image)
  const remaining = remake.replaceImages.find((img) => img.elementId === image.elementId)
  if (!remaining) delete remake.slotBindings[image.elementId]
  else if (remake.slotBindings[image.elementId]?.url === image.url || !remake.slotBindings[image.elementId]) {
    remake.slotBindings[image.elementId] = remaining
  }
}
/** 预览当前步骤内已上传的参考图片。 */
function previewMaterial(image) {
  uni.previewImage({ current: image.localPath || image.url, urls: remake.replaceImages.map((img) => img.localPath || img.url) })
}
/** 文案输入快照：要求或素材变化后旧文案不能静默用于新任务。 */
function copySourceKey() {
  return JSON.stringify([remake.replicateMode, remake.analysisId, remake.deconstructId, remake.refVideo?.url, remake.goal.trim(), remake.replaceImages.map((img) => [img.url, img.role, img.elementId])])
}
/** 失效旧请求并清除旧素材文案，避免更换商品后沿用原商品介绍。 */
function resetPreparedCopy() {
  copySequence += 1
  stopContentPrepare()
  Object.assign(preparedCopy, { title: '', subtitle: '', script: '', error: '', source: '', noNarration: false, speechBudget: null })
}
watch(() => JSON.stringify([remake.refVideo?.url, remake.replaceImages.map((img) => [img.url, img.role, img.elementId])]), resetPreparedCopy)
watch(() => remake.goal, () => {
  copySequence += 1
  stopContentPrepare()
  preparedCopy.source = ''
  preparedCopy.error = remake.replaceImages.length ? '要求已修改，请重新生成文案后确认。' : ''
})
/** 结合真实上传图与选填要求生成文案，失败允许手工填写，旧响应不得回写。 */
async function prepareRemakeCopy() {
  if (!requireLogin()) return
  if (isAction.value || !remake.replaceImages.length || copyLoading.value) return
  const current = ++copySequence
  const source = copySourceKey()
  preparedCopy.error = ''
  try {
    const copy = await runContentPrepare(remake.goal.trim(), {
      intent: 'replicate',
      analysis_id: remake.analysisId, analysis_version: remake.analysisVersion,
      reference_video: remake.refVideo.url, deconstruct_id: remake.deconstructId || undefined,
      material_groups: buildRemakePayload().material_groups,
      requirements: remake.goal.trim(),
      template_title: templateTitle.value || '上传素材介绍',
      duration: remake.duration || remake.refVideo?.duration || 0,
      images: [...new Set(remake.replaceImages.map((img) => img.url))],
      roles: [...new Map(remake.replaceImages.map((img) => [img.url, img.role])).values()],
    })
    if (current === copySequence && source === copySourceKey()) {
      Object.assign(preparedCopy, copy, { source: '', error: '请核对产品名称、规格与口播事实，确认后再生成。' })
    }
  } catch (err) {
    if (current !== copySequence || err?.cancelled) return
    console.error('准备产品介绍文案失败', err)
    preparedCopy.error = err?.message || '文案准备失败，请重试或手动填写'
  }
}
/** 用户主动修改即视为确认当前素材与要求，不自动覆盖手工文案。 */
function confirmManualCopy() {
  if (preparedCopy.speechBudget != null && preparedCopy.script.length > preparedCopy.speechBudget) {
    return toast(`口播超过原片窗口，请压缩至${preparedCopy.speechBudget}字以内`)
  }
  preparedCopy.source = copySourceKey()
  preparedCopy.error = ''
}
/** 统一处理解析、素材确认和生成三个阶段的主按钮。 */
async function handlePrimaryAction() {
  if (!requireLogin()) return
  if (submitting.value || remake.detecting || remake.replaceUploading || remake.refUploading) return
  if (mode.value !== 'remake') return handleGenerate()
  if (remake.step === 0) {
    if (!remake.refVideo) return toast('请先上传原视频')
    return runDetectElements(remake.refVideo.url)
  }
  if (remake.step === 1) {
    if (!remake.parsed) return toast('请先解析原视频')
    remake.step = 2
    uni.pageScrollTo({ scrollTop: 0, duration: 200 })
    if (!isAction.value && preparedCopy.source !== copySourceKey()) await prepareRemakeCopy()
    return
  }
  return handleGenerate()
}

/** 校验并创建任务，预检与建单共用提交锁，进行中的任务只恢复进度。 */
async function handleGenerate() {
  if (submitting.value) return
  if (gen.taskId && workStatus(gen.task?.status).key === 'processing') {
    gen.visible = true
    return
  }
  if (mode.value === 'remake' && !isAction.value && copyLoading.value) return toast('文案准备中，请稍候')
  if (mode.value === 'remake' && !isAction.value && remake.replaceImages.length && ((!preparedCopy.script.trim() && !preparedCopy.noNarration) || preparedCopy.source !== copySourceKey())) {
    toast('请先生成或手动确认产品介绍文案')
    return
  }
  // 必填校验：文案取自设计稿
  if (mode.value === 'remake' && !remake.refVideo) {
    toast('请先上传对标视频')
    return
  }
  if (mode.value === 'grid') {
    if (grid.subMode === 'prompt' && !grid.prompt.trim()) {
      toast('请填写画面描述')
      return
    }
    if (grid.subMode === 'upload' && gridCount.value < 2) {
      toast('请至少上传 2 张图片用于拼合')
      return
    }
    if (grid.subMode === 'split' && !grid.splitImage) {
      toast('请上传一张九宫格照片')
      return
    }
  }
  if (remake.refUploading || remake.replaceUploading || grid.uploadingIndex !== -1 || grid.splitUploading) {
    toast('素材上传中，请稍候')
    return
  }
  // 生成要归属到账号，未登录先去登录
  if (!userStore.isLoggedIn) {
    go(toLoginPath(currentPagePath()))
    return
  }
  // 额度不足时不提交，直接引导充值
  if (estimate.value && estimate.value.enough === false) {
    toast('额度不足，请先充值')
    go('/pages/recharge/index')
    return
  }
  submitting.value = true
  try {
    // 建单前预检：仅复刻执行，九宫格没有参考视频。
    if (mode.value === 'remake') {
      const preRes = await api.task.precheck.post({
        materials: buildRemakePayload().materials,
        intent: buildRemakePayload().intent,
        image_roles: buildRemakePayload().image_roles,
        reference_video: remake.refVideo.url,
        duration: remake.refVideo.duration || undefined,
      }, { suppressGlobalError: true })
      if (!preRes || preRes.code !== 1 || !preRes.data) {
        toast(preRes?.message || '预检失败，请重试')
        return
      }
      const blocking = (preRes.data.missing || []).filter((m) => m.field !== 'real_person_unsupported')
      if (blocking.length) {
        toast(`${blocking[0].label}：${blocking[0].hint}`)
        return
      }
    }
    const isGrid = mode.value === 'grid'
    const payload = isGrid ? buildGridPayload() : buildRemakePayload()
    const res = await (isGrid ? api.task.imageCreate : api.task.create).post(payload, { suppressGlobalError: true })
    if (!res || res.code !== 1) {
      toast(res?.message || '提交失败，请稍后重试')
      return
    }
    // 提交成功不跳走，就地展示生成进度（抖音式"看着它出片"）
    startGenProgress(res.data.id)
  } catch (err) {
    // 建单被业务拒绝时后端会给出「缺什么素材」的可执行文案，原样透传给用户
    console.error('创建生成任务失败', err)
    toast(err?.data?.message || err?.message || '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

/** 建单成功后进入就地进度浮层，开始轮询任务详情（与作品页同一进度语义） */
function startGenProgress(taskId) {
  gen.taskId = taskId
  gen.task = null
  gen.visible = true
  fetchGenStatus()
  if (genTimer) clearInterval(genTimer)
  genTimer = setInterval(fetchGenStatus, 3000)
}

/** 拉取任务最新状态：进度/状态由 worker 回调落库，这里只读取 */
async function fetchGenStatus() {
  if (!gen.taskId) return
  const taskId = gen.taskId
  try {
    const res = await api.task.detail.post({ id: taskId }, { suppressGlobalError: true })
    if (taskId !== gen.taskId) return
    if (res && res.code === 1 && res.data) {
      gen.task = res.data
      const status = workStatus(res.data.status).key
      if (status === 'completed' || status === 'failed') {
        if (genTimer) {
          clearInterval(genTimer)
          genTimer = null
        }
      }
    }
  } catch (err) {
    console.error('轮询生成进度失败', err)
  }
}

/** 关闭浮层：仍在生成中的任务不中断，用户可在「我的作品」继续看进度 */
function closeGen() {
  gen.visible = false
}

/** 生成完成后「继续创作」：清空表单，留在工作台 */
function afterGenCreate() {
  gen.visible = false
  resetShots()
  remake.refVideo = null
  remake.replaceImages = []
  remake.intent = []
  remake.goal = ''
  remake.elements = []
  remake.slotBindings = {}
  remake.linkMode = false
  remake.linkUrl = ''
  grid.images = createGridCells()
  grid.splitImage = null
  grid.subMode = 'prompt'
  grid.prompt = ''
}

// ---------- 生命周期 ----------

onLoad((options) => {
  const id = Number(options && options.template_id)
  if (Number.isFinite(id) && id > 0) {
    templateId.value = id
    loadTemplate(id)
  }
})

onMounted(async () => {
  await loadGenConfig()
  // 默认档位与规格都来自后端业务配置，前端不写死
  remake.creative = remake.creative || REMOTE_DEFAULT_CREATIVE
  remake.ratio = remake.ratio || defaultRatio.value
  remake.resolution = remake.resolution || defaultResolution.value
  grid.ratio = grid.ratio || defaultRatio.value
  grid.resolution = grid.resolution || defaultResolution.value
  scheduleEstimate()
})

onUnload(() => {
  // 离开页面时清掉进度轮询与未提交的本地素材状态，避免残留定时器/临时文件引用
  if (genTimer) {
    clearInterval(genTimer)
    genTimer = null
  }
  stopDeconstructPoll()
  resetPreparedCopy()
  if (estimateTimer) clearTimeout(estimateTimer)
  remake.refVideo = null
  remake.replaceImages = []
  remake.intent = []
  remake.goal = ''
  remake.elements = []
  remake.slotBindings = {}
  remake.linkMode = false
  remake.linkUrl = ''
  grid.images = createGridCells()
  grid.splitImage = null
})
</script>

<style lang="scss" scoped>
/* 页面内容避让「底部生成栏 + 底部导航」，避免最后一张卡片被遮住 */
.studio {
  padding-bottom: calc(var(--nav-h) + 84px + constant(safe-area-inset-bottom));
  padding-bottom: calc(var(--nav-h) + 84px + env(safe-area-inset-bottom));
}

/* 三步复刻以原片与用户素材的对应关系作为视觉主线。 */
.remake-feedback, .remake-materials__hint, .remake-empty {
  display: block;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.7;
}
.remake-feedback { padding: 4px 8px 20px; }
.remake-feedback__error { color: var(--state-error); }
.remake-source { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; font-size: 12px; }
.remake-source > .app-truncate { flex: 1; min-width: 0; }
.remake-source__count { flex-shrink: 0; color: var(--text-muted); }
.remake-slot { padding: 16px 0; border-top: 1px solid var(--border-light); }
.replicate-modes { display: flex; gap: 12px; margin-bottom: 16px; }
.replicate-mode { flex: 1; min-width: 0; margin: 0; padding: 14px 10px; text-align: left; font-size: 15px; line-height: 1.6; border: 1px solid var(--border-light); border-radius: 12px; background: var(--bg-page); color: var(--text-main); }
.replicate-mode--active { border-color: var(--brand-primary); }
.remake-slot__original { display: flex; flex-direction: column; gap: 10px; }
.remake-slot__thumb { width: 100%; height: 220px; flex-shrink: 0; border-radius: 7px; background: var(--bg-page); }
.remake-slot__placeholder { display: flex; align-items: center; justify-content: center; }
.remake-slot__body { flex: 1; min-width: 0; }
.remake-slot__name { display: block; font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.remake-slot__meta, .remake-slot__hint { display: block; margin-top: 5px; font-size: 11px; line-height: 1.6; color: var(--text-muted); }
.remake-slot__status { flex-shrink: 0; font-size: 11px; color: var(--brand-primary); }
.remake-slot__actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; }
/* 元素说明与操作分行，避免手机上将描述挤成逐字排列。 */
.remake-material-action { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 8px 12px; border-radius: var(--radius-full); background: var(--bg-hover); color: var(--brand-primary); font-size: 12px; font-weight: 400; line-height: 1.5; text-align: center; }
.remake-slot__reuse { margin-top: 8px; }
.remake-slot__images { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 14px 0 8px; }
.remake-photo { position: relative; min-width: 0; padding: 4px; border-radius: var(--radius-md); background: var(--paper-100); }
.remake-photo__preview { height: 86px; border-radius: var(--radius-sm); overflow: hidden; }
.remake-photo__preview > image { width: 100%; height: 100%; }
.remake-photo__primary { display: flex; align-items: center; justify-content: center; min-height: 44px; padding: 6px 2px; margin-top: 4px; border-radius: var(--radius-sm); background: var(--paper-card); color: var(--brand-primary); font-size: 11px; line-height: 1.5; text-align: center; }
.remake-photo__primary[aria-pressed='true'] { background: var(--brand-primary-light); font-weight: 600; }
.remake-photo--add { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 138px; gap: 7px; border: 1px dashed var(--border-medium); background: var(--brand-primary-light); color: var(--brand-primary); font-size: 11px; }
/* 删除热区留在图片内，避免与相邻素材的主参考按钮交叠。 */
.remake-photo__remove { position: absolute; right: 4px; top: 4px; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; border-radius: var(--radius-sm); background: rgba(37,36,31,0.72); }
.remake-back { padding: 18px 0; text-align: center; color: var(--brand-primary); font-size: 13px; }
.remake-summary { padding: 16px; margin-bottom: 16px; border: 5px solid var(--paper-100); background: var(--paper-card); border-radius: 24px; }
.remake-summary__head { display: flex; align-items: center; justify-content: space-between; font-size: 14px; font-weight: 600; }
.remake-summary__head > text:last-child { padding: 8px 0 8px 12px; font-size: 12px; color: var(--brand-primary); font-weight: 400; }
.remake-summary__counts { display: flex; flex-wrap: wrap; gap: 16px; margin: 10px 0; font-size: 12px; }
.remake-auto-note { display: flex; align-items: flex-start; gap: 8px; padding: 2px 4px 18px; color: var(--text-secondary); font-size: 12px; line-height: 1.7; }
.remake-auto-note > text { flex: 1; }
.remake-footer-hint { display: block; margin-top: 4px; font-size: 13px; font-weight: 600; }
@media (prefers-reduced-motion: reduce) {
  .studio__upload { transition: none; }
}

/* ============ 已选模板 ============ */
.studio__template {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 16px 0;
  padding: 12px 14px;
  background: var(--brand-primary-light);
  border: 1px solid rgba(178, 58, 46, 0.15);
  border-radius: var(--radius-md);
}

.studio__template-text {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--brand-primary);
}

.studio__template-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

/* ============ 创作方式选择 ============ */
.studio__modes {
  display: flex;
  gap: 10px;
  padding: 14px var(--page-gutter) 8px;
  background: var(--bg-page);
  border-bottom: none;
}

.studio__mode {
  flex: 1;
  padding: 13px 10px;
  border-radius: 20px;
  border: 4px solid var(--paper-100);
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  transition: all var(--transition-fast);

  min-height: 90px;

  &--active {
    border-color: var(--brand-primary-light);
    box-shadow: inset 0 0 0 1px rgba(178, 58, 46, 0.18);
    background: var(--brand-primary-lighter);
  }
}

.studio__mode-icon {
  width: 36px;
  height: 25px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.studio__mode-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.studio__mode--active .studio__mode-title {
  color: var(--brand-primary);
  font-weight: 600;
}

.studio__mode-desc {
  font-size: 11px;
  color: var(--text-muted);
}

/* ============ 表单容器 / 卡片 ============ */
.studio__form {
  padding: 10px var(--page-gutter);
}

.studio__card {
  background: var(--paper-card);
  border-radius: 24px;
  padding: 16px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 16px;

  border: 5px solid var(--paper-100);

  &--flush {
    margin-bottom: 0;
  }
}

.studio__card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

/* 分类标题保留说明，补充操作在窄屏下独占一行。 */
.studio__material-head { flex-wrap: wrap; }
.studio__material-head > .remake-material-action { margin-left: auto; }

.studio__required {
  color: var(--state-error);
}

/* ============ 上传区 ============ */
.studio__upload {
  border: 2px dashed var(--border-medium);
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  text-align: center;
  transition: all var(--transition-fast);

  &:active {
    border-color: var(--brand-primary);
    background: var(--brand-primary-light);
  }

  /* 已上传：仍是同一个虚线框，只是内容更紧凑 */
  &--filled {
    padding: 18px 16px;

    &:active {
      border-color: var(--border-medium);
      background: var(--bg-card);
    }
  }
}

.studio__reference-video {
  width: 100%;
  height: 200px;
  margin-bottom: 16px;
  border-radius: var(--radius-md);
  background: #151515;
}

.studio__upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.studio__upload-pct {
  font-size: 13px;
  font-weight: 600;
  color: var(--brand-primary);
}

.studio__upload-icon {
  width: 52px;
  height: 52px;
  border-radius: 17px;
  background: var(--paper-card);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  border: 5px solid var(--paper-100);
}

.studio__upload-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.studio__upload-hint {
  font-size: 10px;
  color: var(--text-tertiary);
}

.studio__tip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--state-warning-light);
  color: var(--state-warning);
  font-size: 11px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  margin-top: 8px;
}

.studio__file {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  text-align: left;
}

.studio__file-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  background: var(--grad-brand-soft);
  display: flex;
  align-items: center;
  justify-content: center;
}

.studio__file-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.studio__file-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.studio__file-meta {
  font-size: 12px;
  color: var(--text-tertiary);
}

.studio__file-retry {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--brand-primary);
}

/* ============ 创意档位（行内分段） ============ */
.studio__quality-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  margin-bottom: 12px;
}

.studio__quality-label {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.studio__segment {
  display: flex;
  background: var(--bg-hover);
  border-radius: var(--radius-md);
  padding: 3px;

  &--pill {
    border-radius: var(--radius-full);
    gap: 2px;
  }

  &--sm {
    width: auto;
  }
}

.studio__seg {
  flex: 1;
  padding: 8px 12px;
  text-align: center;
  font-size: 13px;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);

  &--active {
    background: var(--bg-card);
    color: var(--text-primary);
    font-weight: 500;
    box-shadow: var(--shadow-sm);
  }
}

.studio__segment--sm .studio__seg {
  flex: none;
  padding: 6px 10px;
  font-size: 12px;
}

.studio__pill {
  position: relative;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-tertiary);
  border-radius: var(--radius-full);
  white-space: nowrap;
  transition: all var(--transition-fast);

  &--active {
    background: var(--grad-brand);
    color: #ffffff;
    font-weight: 600;
    box-shadow: var(--shadow-brand);
  }
}

.studio__rec {
  position: absolute;
  top: -6px;
  right: -4px;
  background: var(--state-warning);
  color: #ffffff;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: var(--radius-full);
  line-height: 1.4;
}

/* ============ 折叠区 ============ */
.studio__collapse-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
}

.studio__collapse-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.studio__collapse-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.studio__badge {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  background: var(--bg-hover);
  padding: 3px 8px;
  border-radius: var(--radius-full);
}

.studio__arrow--open {
  transform: rotate(180deg);
}

/* ============ 子分组 / 设置项 ============ */
.studio__sub {
  padding: 14px 0;
  border-bottom: 1px solid var(--border-light);
}

.studio__sub-title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.studio__sub-hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
}

.studio__product {
  display: flex;
  align-items: center;
  gap: 12px;
}

.studio__product-box {
  width: 80px;
  height: 80px;
  flex-shrink: 0;
  border: 2px dashed var(--border-medium);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: var(--text-muted);
  overflow: hidden;
  transition: all var(--transition-fast);

  &:active {
    border-color: var(--brand-primary);
    background: var(--brand-primary-light);
  }
}

.studio__product-img {
  width: 100%;
  height: 100%;
}

.studio__product-add {
  font-size: 10px;
}

.studio__product-pct {
  font-size: 12px;
  font-weight: 600;
  color: var(--brand-primary);
}

.studio__product-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.studio__product-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.studio__product-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

.studio__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: none;
  }
}

.studio__row-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.studio__row-label-wrap {
  display: flex;
  flex-direction: column;
}

.studio__row-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.studio__row-value {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-tertiary);
}

/* ============ 九宫格上传 ============ */
.studio__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.studio__cell {
  position: relative;
  padding-top: 100%;
  border: 2px dashed var(--border-medium);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  overflow: hidden;

  &--filled {
    border-style: solid;
    border-color: var(--border-light);
  }
}

.studio__cell-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.studio__cell-content {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.studio__cell-index {
  font-size: 12px;
  margin-top: 4px;
}

.studio__cell-pct {
  font-size: 12px;
  font-weight: 600;
  color: var(--brand-primary);
}

.studio__grid-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

.studio__textarea {
  width: 100%;
  min-height: 100px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-page);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  box-sizing: border-box;
}

/* 文案确认是独立表单步骤，标签与输入保持一致的纵向间距。 */
.studio__copy-field { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }

.studio__textarea-count {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-tertiary);
  text-align: right;
}

.studio__upload--split {
  min-height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.studio__upload-img {
  width: 100%;
  height: 180px;
  border-radius: var(--radius-md);
}

/* ============ 创意档位（卡片） ============ */
.studio__qualities {
  display: flex;
  gap: 8px;
}

.studio__quality {
  flex: 1;
  padding: 14px 8px;
  border-radius: var(--radius-md);
  border: 2px solid var(--border-light);
  background: var(--bg-card);
  text-align: center;
  position: relative;
  transition: all var(--transition-fast);

  &--active {
    border-color: var(--brand-primary);
    background: var(--brand-primary-light);
  }
}

.studio__quality-name {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.studio__quality--active .studio__quality-name {
  color: var(--brand-primary);
  font-weight: 600;
}

.studio__quality-desc {
  display: block;
  font-size: 11px;
  line-height: 1.4;
  color: var(--text-tertiary);
}

.studio__quality-tag {
  position: absolute;
  top: -8px;
  right: 8px;
  background: var(--grad-hot);
  color: #ffffff;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: var(--radius-full);
}

/* ============ 底部生成栏 ============ */
.studio__generate {
  position: fixed;
  bottom: calc(var(--nav-h) + constant(safe-area-inset-bottom));
  bottom: calc(var(--nav-h) + env(safe-area-inset-bottom));
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: var(--page-max);
  background: var(--bg-page);
  border-top: none;
  padding: 10px var(--page-gutter);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  z-index: var(--z-action);
  box-shadow: none;
}

.studio__cost {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.studio__cost-label {
  font-size: 11px;
  color: var(--text-muted);
}

.studio__cost-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--brand-primary);
}

.studio__cost-unit {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-tertiary);
}

.studio__submit {
  flex: 1;
  min-height: 48px;
  height: auto;
  line-height: 1.5;

  border-radius: var(--radius-full);

  &--loading {
    opacity: 0.6;
  }
}

/* ============ 一句话目标（小白主入口） ============ */
.studio__goal {
  margin-bottom: 12px;
}

.studio__goal-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.studio__chip {
  padding: 6px 12px;
  font-size: 12px;
  color: var(--brand-primary);
  background: var(--brand-primary-light);
  border-radius: var(--radius-full);
  transition: all var(--transition-fast);

  &:active {
    opacity: 0.7;
  }
}

/* ============ 替换素材（多图 + 角色标注） ============ */
.studio__replace-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.studio__replace-cell {
  position: relative;
  padding-top: 100%;
  border: 2px dashed var(--border-medium);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  overflow: hidden;

  &--add {
    border-style: dashed;
    background: var(--bg-card);

    &:active {
      border-color: var(--brand-primary);
      background: var(--brand-primary-light);
    }
  }
}

.studio__replace-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.studio__replace-add {
  font-size: 10px;
  margin-top: 2px;
}

.studio__replace-role {
  position: absolute;
  left: 4px;
  bottom: 4px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  color: #ffffff;
  background: rgba(31, 29, 26, 0.62);
  border-radius: var(--radius-full);
}

.studio__replace-pct {
  display: block;
  margin-top: 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--brand-primary);
}

/* ============ 粘贴视频链接入口 ============ */
.studio__link {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-light);
}

.studio__link-entry {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--brand-primary);

  min-height: 44px;
  justify-content: center;

  &:active {
    opacity: 0.7;
  }
}

.studio__link-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.studio__link-input {
  width: 100%;
  /* uni-input 默认高度不足以容纳内边距，需明确保留可输入与触控的空间。 */
  min-height: 48px;
  padding: 10px 12px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-page);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  box-sizing: border-box;
}

.studio__link-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  font-size: 13px;
}

.studio__link-cancel {
  color: var(--text-muted);
}

.studio__link-confirm {
  font-weight: 600;
  color: var(--brand-primary);
}

.studio__link-hint {
  display: block;
  margin-top: 8px;
  font-size: 10px;
  color: var(--text-muted);
  line-height: 1.8;
}

/* ============ 原片元素识别预览（看得见的复刻） ============ */
.studio__elements-hint {
  display: block;
  margin: -4px 0 10px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-muted);
}

.studio__elements-loading {
  font-size: 13px;
  color: var(--text-muted);
}

.studio__elements-scroll {
  width: 100%;
  white-space: nowrap;
}

.studio__elements-track {
  display: inline-flex;
  gap: 10px;
}

.studio__element {
  position: relative;
  width: 96px;
  flex-shrink: 0;
  padding-bottom: 4px;
  border-radius: var(--radius-md);
}

.studio__element--bound {
  background: var(--brand-primary-light);
}

.studio__element-action {
  display: block;
  margin-top: 6px;
  padding: 4px 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--brand-primary);
  background: var(--brand-primary-light);
  border-radius: var(--radius-sm);
}

.studio__element-binding {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-top: 4px;
  padding: 4px 5px;
  border: 1px solid rgba(178, 58, 46, 0.2);
  background: var(--bg-card);
  border-radius: var(--radius-sm);
}

.studio__element-binding-img {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  border-radius: 3px;
}

.studio__element-binding-text {
  flex: 1;
  min-width: 0;
  font-size: 9px;
  color: var(--text-secondary);
}

.studio__element-binding-cancel {
  flex-shrink: 0;
  font-size: 10px;
  color: var(--brand-primary);
}

.studio__element-thumb {
  width: 96px;
  height: 96px;
  border-radius: var(--radius-md);
  background: var(--bg-hover);
}

.studio__element-tag {
  position: absolute;
  top: 4px;
  left: 4px;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 600;
  color: #ffffff;
  background: rgba(31, 29, 26, 0.62);
  border-radius: var(--radius-full);
}

.studio__element-label {
  display: block;
  width: 96px;
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

.studio__element-time {
  display: block;
  font-size: 10px;
  color: var(--text-muted);
}

/* ============ 生成进度浮层（提交后就地展示，抖音式"看着它出片"） ============ */
.gen-pop {
  position: fixed;
  inset: 0;
  z-index: var(--z-overlay);
  display: flex;
  align-items: flex-end;
  justify-content: center;

  &__mask {
    position: absolute;
    inset: 0;
    background: rgba(31, 29, 26, 0.5);
  }

  &__sheet {
    position: relative;
    width: 100%;
    max-width: var(--page-max);
    max-height: 90vh;
    overflow-y: auto;
    border: 6px solid var(--paper-100);
    border-bottom: none;
    padding: 20px 16px calc(20px + env(safe-area-inset-bottom));
    background: var(--bg-card);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    box-shadow: 0 -8px 24px rgba(31, 29, 26, 0.12);
  }

  &__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  &__title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
  }

  &__close {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: var(--bg-hover);
  }

  &__body {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  &__phase {
    margin: 14px 0 12px;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
  }

  &__remain {
    margin-top: 12px;
    font-size: 12px;
    color: var(--text-muted);
  }

  &__icon {
    margin-bottom: 12px;

    &--ok {
      animation: app-enter 500ms var(--ease-out);
    }
  }

  &__fail {
    font-size: 13px;
    color: var(--state-error);
    text-align: center;
    margin-bottom: 16px;
    line-height: 1.5;
  }

  &__video {
    width: 100%;
    height: 240px;
    border-radius: var(--radius-lg);
    background: #1F1D1A;
    margin-bottom: 16px;
  }

  &__actions {
    display: flex;
    gap: 12px;
    width: 100%;
    margin-top: 16px;
  }

  &__btn {
    flex: 1;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-full);
    font-size: 14px;
    font-weight: 600;

    &--ghost {
      background: var(--bg-hover);
      color: var(--text-secondary);
    }

    &--brand {
      background: var(--grad-brand);
      color: #ffffff;
    }
  }
}

/* 进度环（与作品页同源观感） */
.gen-ring {
  position: relative;
  width: 72px;
  height: 72px;
  animation: app-breathe 2.2s var(--ease-out) infinite;

  &__track,
  &__spin {
    position: absolute;
    border-radius: 50%;
    border: 2px solid transparent;
  }

  &__track {
    inset: 0;
    border-color: var(--border-light);
  }

  &__spin--outer {
    inset: 0;
    border-top-color: var(--brand-primary);
    border-right-color: var(--brand-primary);
    animation: app-spin 1.1s var(--ease-out) infinite;
  }

  &__spin--inner {
    inset: 6px;
    border-bottom-color: #E0AFA6;
    border-left-color: #E0AFA6;
    animation: app-spin 1.9s var(--ease-out) infinite reverse;
  }

  &__value {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
  }
}

.gen-bar {
  position: relative;
  width: 70%;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--bg-hover);
  overflow: hidden;

  &__fill {
    height: 100%;
    border-radius: var(--radius-full);
    background: var(--grad-brand);
    width: 100%;
    transform-origin: left center;
    transition: transform 700ms var(--ease-out);
  }
}

/* ============ AI 拆解分镜 ============ */
.studio__shots {
  &-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    padding: 8px 4px 4px;
  }

  &-empty-text {
    font-size: 12px;
    color: var(--text-muted);
    text-align: center;
    line-height: 1.5;
  }

  &-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 38px;
    padding: 0 18px;
    border-radius: var(--radius-full);
    background: var(--grad-brand);
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
  }

  &-loading {
    display: block;
    padding: 16px 0;
    font-size: 13px;
    color: var(--text-secondary);
    text-align: center;
  }

  &-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 4px;
  }

  &-redo {
    margin-top: 4px;
    align-self: center;
    padding: 6px 16px;
    border-radius: var(--radius-full);
    background: var(--bg-hover);
    font-size: 12px;
    color: var(--text-secondary);
  }
}

.studio__shot {
  display: flex;
  gap: 10px;
  padding: 10px;
  background: var(--bg-hover);
  border-radius: var(--radius-md);

  &-frame {
    flex: 0 0 72px;
    width: 72px;
    height: 96px;
    border-radius: var(--radius-sm);
    background: #E7E0D1;
  }

  &-body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  &-head {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 8px;
    align-items: center;
    justify-content: space-between;
  }

  &-no {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }

  &-time {
    font-size: 11px;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }

  &-input {
    width: 100%;
    min-height: 52px;
    padding: 8px 10px;
    font-size: 12px;
    line-height: 1.5;
    color: var(--text-primary);
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-sm);
  }

  &-narration {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.4;
  }
}
/* ============ 三步引导 ============ */
.studio__guide-note {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin: 0 0 14px;
  padding: 2px 2px 0;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
}
.studio__guide-note-title {
  font-size: 23px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-serif);
}
.studio__guide-note-desc {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-tertiary);
  margin-top: 5px;
}
.studio__guide {
  display: flex;
  gap: 6px;
  margin: 0 0 18px;
}
.studio__guide-step {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 4px;
  background: var(--paper-100);
  border: none;
  border-radius: var(--radius-md);
  min-height: 76px;
  flex-direction: column;
  text-align: center;
}
.studio__guide-step--active {
  border-color: var(--brand-primary);
  background: var(--brand-primary-light);
  box-shadow: inset 0 0 0 1px rgba(178,58,46,.16);
}
.studio__guide-step--done {
  border-color: rgba(75, 122, 90, 0.4);
  background: var(--state-success-light);
}
.studio__guide-no {
  flex: none;
  width: 23px;
  height: 23px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-tertiary);
  background: var(--paper-card);
}
.studio__guide-step--active .studio__guide-no {
  background: var(--brand-primary);
}
.studio__guide-step--done .studio__guide-no {
  background: #4B7A5A;
}
.studio__guide-body {
  flex: 1;
  min-width: 0;
}
.studio__guide-title {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
}
.studio__guide-desc {
  display: block;
  margin-top: 2px;
  font-size: 10px;
  line-height: 1.4;
  color: var(--text-muted);
}

/* 窄屏下只调整文字和留白，触控区仍保持至少 44px。 */
@media screen and (max-width: 360px) {
  .studio__mode-desc { font-size: 10px; }
  .studio__guide-desc { font-size: 9px; }
  .studio__upload { padding: 20px 8px; }
  .studio__material-head > .remake-material-action { flex-basis: 100%; }
  .remake-slot__images { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .studio__segment--pill { flex-wrap: wrap; border-radius: var(--radius-lg); }
  .studio__collapse-head { flex-wrap: wrap; gap: 8px; }
  .studio__quality-row > .studio__segment { width: 100%; }
}
</style>
