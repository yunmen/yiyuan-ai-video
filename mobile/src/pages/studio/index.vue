<template>
  <view class="app-page studio">
    <AppNavBar title="创作工作台" solid />

    <!-- 已选模板：从首页「热门模板」带入时展示，可一键取消；未选模板时整行不出现 -->
    <view v-if="templateId" class="studio__template">
      <AppIcon name="layers" :size="16" color="#4F46E5" />
      <text class="studio__template-text app-truncate">已选模板：{{ templateTitle }}</text>
      <view class="studio__template-close" role="button" aria-label="取消选择模板" @click="clearTemplate">
        <AppIcon name="close" :size="16" color="#64748B" :stroke-width="2.5" />
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
      >
        <view class="studio__mode-icon">
          <AppIcon name="refresh-cw" :size="28" :color="mode === 'remake' ? '#4F46E5' : '#64748B'" />
        </view>
        <text class="studio__mode-title">视频复刻</text>
        <text class="studio__mode-desc">对标爆款一键复刻</text>
      </view>
      <view
        class="studio__mode"
        :class="{ 'studio__mode--active': mode === 'grid' }"
        role="button"
        aria-label="九宫格出片"
        @click="mode = 'grid'"
      >
        <view class="studio__mode-icon">
          <AppIcon name="grid" :size="28" :color="mode === 'grid' ? '#4F46E5' : '#64748B'" />
        </view>
        <text class="studio__mode-title">九宫格出片</text>
        <text class="studio__mode-desc">九宫格图片成片</text>
      </view>
    </view>

    <!-- ============ 视频复刻表单 ============ -->
    <view v-show="mode === 'remake'" class="studio__form">
      <!-- 三步引导：把"怎么用"直接做成可点的状态指引，首屏即懂 -->
      <view class="studio__guide">
        <view
          v-for="(s, i) in guideSteps"
          :key="i"
          class="studio__guide-step"
          :class="`studio__guide-step--${guideStepState(i)}`"
          role="button"
          @click="scrollToStep(i)"
        >
          <view class="studio__guide-no">{{ guideStepState(i) === 'done' ? '✓' : i + 1 }}</view>
          <view class="studio__guide-body">
            <text class="studio__guide-title">{{ s.title }}</text>
            <text class="studio__guide-desc">{{ s.desc }}</text>
          </view>
        </view>
      </view>

      <!-- 上传对标视频 -->
      <view id="remake-upload" class="studio__card">
        <view class="studio__card-title">
          <text>上传对标视频</text>
          <text class="studio__required">*</text>
        </view>

        <view v-if="!remake.refVideo" class="studio__upload" role="button" @click="chooseRefVideo">
          <view v-if="remake.refUploading" class="studio__upload-progress">
            <text class="studio__upload-pct">上传中 {{ remake.refProgress }}%</text>
          </view>
          <template v-else>
            <view class="studio__upload-icon">
              <AppIcon name="video-camera" :size="28" color="#4F46E5" />
            </view>
            <text class="studio__upload-title">点击上传对标视频</text>
            <text class="studio__upload-hint">支持 MP4 / MOV 格式，时长不超过 {{ maxReferenceSeconds }}s</text>
            <view class="studio__tip">
              <AppIcon name="info" :size="12" color="#F59E0B" :stroke-width="2.5" />
              <text>上传爆款视频，AI 自动复刻</text>
            </view>
          </template>
        </view>

        <!-- 已上传：保持同一个虚线框，内容换成紧凑的文件状态 -->
        <view v-else class="studio__upload studio__upload--filled">
          <view class="studio__file">
            <view class="studio__file-icon">
              <AppIcon name="film" :size="22" color="#4F46E5" />
            </view>
            <view class="studio__file-body">
              <text class="studio__file-name app-truncate">{{ remake.refVideo.name }}</text>
              <text class="studio__file-meta">{{ refVideoMetaText }}</text>
            </view>
            <text class="studio__file-retry" role="button" @click="retryRefVideo">重新上传</text>
          </view>
        </view>
        <!-- 粘贴视频链接入口（仅在未上传视频时展示）：直链复刻，跳过本地上传 -->
        <view v-if="!remake.refVideo" class="studio__link">
          <view v-if="!remake.linkMode" class="studio__link-entry" role="button" @click="remake.linkMode = true">
            <AppIcon name="share" :size="14" color="#4F46E5" />
            <text>粘贴视频链接</text>
          </view>
          <view v-else class="studio__link-box">
            <input
              class="studio__link-input"
              v-model="remake.linkUrl"
              placeholder="粘贴可访问的视频链接，如 https://.../a.mp4"
              confirm-type="done"
              @confirm="applyLink"
            />
            <view class="studio__link-actions">
              <text class="studio__link-cancel" role="button" @click="remake.linkMode = false; remake.linkUrl = ''">取消</text>
              <text class="studio__link-confirm" role="button" @click="applyLink">使用链接</text>
            </view>
          </view>
          <text class="studio__link-hint">仅支持可直接访问的视频文件链接；抖音 / 小红书分享链接暂不支持</text>
        </view>
      </view>

      <!-- 原片元素识别预览（看得见的复刻）：上传/粘贴对标视频后 AI 识别可替换元素 -->
      <view v-if="remake.elements.length || remake.detecting" class="studio__card studio__elements">
        <view class="studio__card-title">
          <text>AI 识别原片元素</text>
          <text class="studio__sub-hint">可替换的槽位</text>
        </view>
        <text v-if="remake.detecting && !remake.elements.length" class="studio__elements-loading">识别中…</text>
        <scroll-view v-else scroll-x class="studio__elements-scroll">
          <view class="studio__elements-track">
            <view v-for="el in remake.elements" :key="el.id" class="studio__element">
              <image class="studio__element-thumb" :src="el.thumbnail" mode="aspectFill" />
              <view class="studio__element-tag">{{ kindLabel(el.kind) }}</view>
              <text class="studio__element-label app-truncate">{{ el.label || kindLabel(el.kind) }}</text>
              <text class="studio__element-time">{{ formatTime(el.time) }}</text>
            </view>
          </view>
        </scroll-view>
      </view>

      <!-- AI 拆解分镜：上传对标视频后拆解原片结构，可逐镜编辑画面描述（看得见的复刻 + 可控复刻） -->
      <view v-if="remake.refVideo" class="studio__card studio__shots">
        <view class="studio__card-title">
          <text>AI 拆解分镜</text>
          <text class="studio__sub-hint">看清原片结构，可改每镜画面</text>
        </view>

        <view v-if="!remake.shots.length && !remake.decomposing" class="studio__shots-empty">
          <text class="studio__shots-empty-text">拆解后你能看到每个镜头的画面与口播，并微调描述</text>
          <view class="studio__shots-btn" role="button" @click="startDeconstruct">
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
            />
            <view class="studio__shot-body">
              <view class="studio__shot-head">
                <text class="studio__shot-no">镜头 {{ shot.index + 1 }}</text>
                <text class="studio__shot-time">{{ shotTimeText(shot) }}</text>
              </view>
              <textarea
                v-model="shot.description"
                class="studio__shot-input"
                placeholder="此镜头没有逆推描述，建议补上画面与运镜…"
                :maxlength="300"
              />
              <text v-if="shot.narration" class="studio__shot-narration">原片口播：{{ shot.narration }}</text>
            </view>
          </view>
          <view class="studio__shots-redo" role="button" @click="startDeconstruct">
            <text>重新拆解</text>
          </view>
        </view>
      </view>

      <!-- 一句话目标（小白主入口）：用大白话描述想做成什么样，选填 -->
      <view id="remake-goal" class="studio__card studio__goal">
        <view class="studio__card-title">
          <text>一句话目标</text>
          <text class="studio__sub-hint">选填，想做成什么样</text>
        </view>
        <textarea
          v-model="remake.goal"
          class="studio__textarea"
          :placeholder="goalPlaceholder"
          :maxlength="200"
        />
        <view class="studio__goal-chips">
          <view
            v-for="chip in goalExamples"
            :key="chip"
            class="studio__chip"
            role="button"
            @click="remake.goal = chip"
          >
            <text>{{ chip }}</text>
          </view>
        </view>
        <text class="studio__textarea-count">{{ (remake.goal || '').length }}/200</text>
      </view>

      <!-- 创意档位（行内精简分段，与九宫格模式共用同一份后端档位） -->
      <view class="studio__quality-row">
        <text class="studio__quality-label">创意档位</text>
        <view class="studio__segment studio__segment--pill">
          <view
            v-for="level in creativeLevels"
            :key="level.key"
            class="studio__pill"
            :class="{ 'studio__pill--active': remake.creative === level.key }"
            role="button"
            @click="remake.creative = level.key"
          >
            <text>{{ level.label }}</text>
            <text
              v-if="remake.creative === level.key && level.key === REMOTE_DEFAULT_CREATIVE"
              class="studio__rec"
            >推荐</text>
          </view>
        </view>
      </view>

      <!-- 高级选项：仅保留后端真实存在的生成参数 -->
      <view class="studio__card studio__card--flush">
        <view class="studio__collapse-head" role="button" @click="remake.showAdvanced = !remake.showAdvanced">
          <view class="studio__collapse-title">
            <AppIcon name="sparkles" :size="18" color="#64748B" />
            <text>高级选项</text>
          </view>
          <view class="studio__collapse-right">
            <text class="studio__badge">可选 {{ ADVANCED_COUNT }} 项</text>
            <AppIcon
              name="chevron-down"
              :size="18"
              color="#64748B"
              :class="remake.showAdvanced ? 'studio__arrow--open' : ''"
            />
          </view>
        </view>

        <view v-show="remake.showAdvanced" class="studio__collapse-body">
          <!-- 主角表现（上传了人物图时可选）：让换上去的新主角以跳舞/讲解方式表演 -->
          <view v-if="remake.replaceImages.some((i) => i.role === 'person')" class="studio__sub">
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
                @click="remake.leadAct = remake.leadAct === la.key ? '' : la.key"
              >
                <text>{{ la.label }}</text>
              </view>
            </view>
          </view>

          <!-- 替换素材（选填）：上传要替换进去的图，并标注是商品/人物/场景 -->
          <view class="studio__sub">
            <view class="studio__sub-title">
              <text>替换素材</text>
              <text class="studio__sub-hint">选填，最多 9 张，点图可标注角色</text>
            </view>
            <view class="studio__replace-grid">
              <view
                v-for="(img, idx) in remake.replaceImages"
                :key="idx"
                class="studio__replace-cell"
                role="button"
                @click="handleReplaceImageTap(idx)"
              >
                <image class="studio__replace-img" :src="img.localPath || img.url" mode="aspectFill" />
                <view class="studio__replace-role" role="button" @click.stop="pickRole(idx)">
                  <text>{{ roleLabel(img.role) }}</text>
                </view>
              </view>
              <view
                v-if="remake.replaceImages.length < 9"
                class="studio__replace-cell studio__replace-cell--add"
                role="button"
                @click="chooseReplaceImage"
              >
                <AppIcon name="plus" :size="24" color="#94A3B8" />
                <text class="studio__replace-add">添加</text>
              </view>
            </view>
            <text v-if="remake.replaceUploading" class="studio__replace-pct">上传中 {{ remake.replaceProgress }}%</text>
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
                @click="remake.duration = item"
              >
                <text>{{ item }}s</text>
              </view>
            </view>
          </view>

          <!-- 画幅比例 -->
          <view class="studio__row" role="button" @click="pickWith(ratioOptions, (v) => (remake.ratio = v))">
            <text class="studio__row-label">画幅比例</text>
            <view class="studio__row-value">
              <text>{{ remake.ratio || '--' }}</text>
              <AppIcon name="chevron-right" :size="16" color="#64748B" />
            </view>
          </view>

          <!-- 清晰度 -->
          <view class="studio__row" role="button" @click="pickWith(resolutionOptions, (v) => (remake.resolution = v))">
            <text class="studio__row-label">清晰度</text>
            <view class="studio__row-value">
              <text>{{ remake.resolution || '--' }}</text>
              <AppIcon name="chevron-right" :size="16" color="#64748B" />
            </view>
          </view>

          <!-- 复刻形态（默认不指定，沿用原片结构） -->
          <view class="studio__row" role="button" @click="pickWith(formatOptions, (v) => (remake.format = v))">
            <text class="studio__row-label">复刻形态</text>
            <view class="studio__row-value">
              <text>{{ formatLabel }}</text>
              <AppIcon name="chevron-right" :size="16" color="#64748B" />
            </view>
          </view>

          <!-- 开头钩子 -->
          <view class="studio__row" role="button" @click="pickWith(hookOptions, (v) => (remake.hookBoost = v))">
            <view class="studio__row-label">
              <text>开头钩子</text>
              <AppIcon name="info" :size="14" color="#94A3B8" />
            </view>
            <view class="studio__row-value">
              <text>{{ hookLabel }}</text>
              <AppIcon name="chevron-right" :size="16" color="#64748B" />
            </view>
          </view>

          <!-- 真人素材处理 -->
          <view class="studio__row" role="button" @click="pickWith(REAL_PERSON_OPTIONS, (v) => (remake.realPerson = v))">
            <text class="studio__row-label">真人素材处理</text>
            <view class="studio__row-value">
              <text>{{ realPersonLabel }}</text>
              <AppIcon name="chevron-right" :size="16" color="#64748B" />
            </view>
          </view>

          <!-- 去水印 -->
          <view class="studio__row" role="button" @click="pickWith(WATERMARK_OPTIONS, (v) => (remake.watermark = v))">
            <text class="studio__row-label">去水印</text>
            <view class="studio__row-value">
              <text>{{ watermarkLabel }}</text>
              <AppIcon name="chevron-right" :size="16" color="#64748B" />
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
            @click="grid.subMode = gm.key"
          >
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
        <textarea
          v-model="grid.prompt"
          class="studio__textarea"
          placeholder="描述你想要的九宫格画面，AI 将生成 9 个不同构图/风格的照片并拼成 3×3"
          :maxlength="2000"
        />
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
            @click="handleGridCell(index)"
          >
            <image
              v-if="cell"
              class="studio__cell-img"
              :src="cell.localPath || cell.url"
              mode="aspectFill"
            />
            <text v-else-if="grid.uploadingIndex === index" class="studio__cell-pct">
              {{ grid.uploadProgress }}%
            </text>
            <template v-else>
              <AppIcon name="plus" :size="24" color="#94A3B8" />
              <text class="studio__cell-index">{{ index + 1 }}</text>
            </template>
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
          @click="handleSplitTap"
        >
          <image
            v-if="grid.splitImage"
            class="studio__upload-img"
            :src="grid.splitImage.localPath || grid.splitImage.url"
            mode="aspectFill"
          />
          <text v-else-if="grid.splitUploading" class="studio__upload-pct">
            {{ grid.splitProgress }}%
          </text>
          <template v-else>
            <view class="studio__upload-icon">
              <AppIcon name="image" :size="28" color="#4F46E5" />
            </view>
            <text class="studio__upload-title">点击上传九宫格照片</text>
            <text class="studio__upload-hint">将按 3×3 拆分为 9 张单图</text>
          </template>
        </view>
      </view>

      <!-- 更多设置：画幅 / 清晰度 -->
      <view class="studio__card studio__card--flush">
        <view class="studio__collapse-head" role="button" @click="grid.showMore = !grid.showMore">
          <view class="studio__collapse-title">
            <AppIcon name="settings" :size="20" color="#64748B" />
            <text>更多设置</text>
          </view>
          <AppIcon
            name="chevron-down"
            :size="20"
            color="#64748B"
            :class="grid.showMore ? 'studio__arrow--open' : ''"
          />
        </view>

        <view v-show="grid.showMore" class="studio__collapse-body">
          <view class="studio__row" role="button" @click="pickWith(ratioOptions, (v) => (grid.ratio = v))">
            <text class="studio__row-label">画幅比例</text>
            <view class="studio__row-value">
              <text>{{ grid.ratio || '--' }}</text>
              <AppIcon name="chevron-right" :size="16" color="#64748B" />
            </view>
          </view>

          <view class="studio__row" role="button" @click="pickWith(resolutionOptions, (v) => (grid.resolution = v))">
            <text class="studio__row-label">清晰度</text>
            <view class="studio__row-value">
              <text>{{ grid.resolution || '--' }}</text>
              <AppIcon name="chevron-right" :size="16" color="#64748B" />
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 底部生成栏：叠在底部导航之上，预估价与后端 estimate 同源 -->
    <view id="remake-generate" class="studio__generate">
      <view class="studio__cost">
        <text class="studio__cost-label">预估消耗</text>
        <text class="studio__cost-value">{{ costText }} <text class="studio__cost-unit">额度</text></text>
      </view>
      <view
        class="studio__submit app-btn-brand"
        :class="{ 'studio__submit--loading': submitting }"
        role="button"
        aria-label="立即生成"
        @click="handleGenerate"
      >
        <AppIcon name="zap" :size="20" color="#FFFFFF" :stroke-width="2.5" />
        <text>{{ submitting ? '提交中…' : '立即生成' }}</text>
      </view>
    </view>

    <AppTabBar active="create" />

    <!-- 生成进度浮层：提交后就地展示，抖音式"看着它出片"，不强制跳走 -->
    <view v-if="gen.visible" class="gen-pop">
      <view class="gen-pop__mask" role="button" aria-label="关闭" @click="closeGen" />
      <view class="gen-pop__sheet" @click.stop>
        <view class="gen-pop__head">
          <text class="gen-pop__title">
            {{ genStatus.key === 'success' ? '成片已生成' : genStatus.key === 'failed' ? '生成失败' : '正在生成' }}
          </text>
          <view class="gen-pop__close" role="button" aria-label="关闭" @click="closeGen">
            <AppIcon name="close" :size="18" color="#64748B" :stroke-width="2.5" />
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
            <view class="gen-bar__fill" :style="{ width: genProgress + '%' }" />
          </view>
          <text class="gen-pop__remain">{{ gen.task ? workRemainingText(gen.task) : '已提交，正在排队…' }}</text>
        </view>

        <!-- 失败：给出原因 + 返回修改 / 去作品页 -->
        <view v-else-if="genStatus.key === 'failed'" class="gen-pop__body">
          <view class="gen-pop__icon gen-pop__icon--fail">
            <AppIcon name="alert-circle" :size="40" color="#EF4444" />
          </view>
          <text class="gen-pop__fail">{{ gen.task ? workFailReason(gen.task) : '生成失败，请稍后重试' }}</text>
          <view class="gen-pop__actions">
            <view class="gen-pop__btn gen-pop__btn--ghost" role="button" @click="closeGen">
              <text>返回修改</text>
            </view>
            <view class="gen-pop__btn gen-pop__btn--brand" role="button" @click="go('/pages/works/index')">
              <text>去作品页</text>
            </view>
          </view>
        </view>

        <!-- 成功：就地播放成片 + 继续创作 / 去作品页 -->
        <view v-else class="gen-pop__body">
          <view class="gen-pop__icon gen-pop__icon--ok">
            <AppIcon name="check-circle" :size="40" color="#10B981" />
          </view>
          <video
            v-if="gen.task && gen.task.result_video"
            class="gen-pop__video"
            :src="gen.task.result_video"
            :controls="true"
            :autoplay="true"
            object-fit="contain"
          />
          <view class="gen-pop__actions">
            <view class="gen-pop__btn gen-pop__btn--ghost" role="button" @click="afterGenCreate">
              <text>继续创作</text>
            </view>
            <view class="gen-pop__btn gen-pop__btn--brand" role="button" @click="go('/pages/works/index')">
              <text>去作品页</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import AppTabBar from '@/components/AppTabBar.vue'
import api from '@/api'
import { useUserStore } from '@/store/modules/user'
import { useGenConfig } from '@/composables/useGenConfig'
import { currentPagePath, go, toLoginPath } from '@/utils/navigation'
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

// 视频复刻高级选项的真实条目数（替换意图/替换素材/时长/画幅/清晰度/形态/钩子/真人处理/去水印）
const ADVANCED_COUNT = 9
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

// 提交后的就地生成进度浮层：提交不强制跳走，抖音式"看着它出片"
const gen = reactive({ taskId: null, visible: false, task: null })
let genTimer = null
let deconstructTimer = null
const genStatus = computed(() => (gen.task ? workStatus(gen.task.status) : { key: 'processing', label: '生成中' }))
const genProgress = computed(() => (gen.task ? normalizeProgress(gen.task.progress) : 0))

// 两张表单各自持有本地状态：切换创作方式后回来，已填内容与设置都还在
const remake = reactive({
  refVideo: null, // { url, name, duration, size }
  refUploading: false,
  refProgress: 0,
  goal: '', // 一句话目标（小白主入口，选填，≤200 字）
  intent: [], // 替换意图多选：product/person/scene
  replaceImages: [], // 替换素材图（≤9）：{ url, localPath, role }
  replaceUploading: false,
  replaceProgress: 0,
  elements: [], // 原片元素识别结果（detect-elements）：{ id, kind, label, time, thumbnail }
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
  isFoodShop.value
    ? ['换成我家招牌菜', '突出门店人气和烟火气', '更有食欲、适合发抖音团购']
    : ['更电影感', '适合发小红书', '更有反转', '画面更精致'],
)
/** 一句话目标占位提示：餐饮形态给餐饮示例，其余保持通用 */
const goalPlaceholder = computed(() =>
  isFoodShop.value
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

/** 探测本地视频时长（部分平台 chooseVideo 不回传 duration），失败返回 0 */
function probeVideoSeconds(src) {
  return new Promise((resolve) => {
    if (typeof document === 'undefined' || !src) {
      resolve(0)
      return
    }
    const el = document.createElement('video')
    el.preload = 'metadata'
    el.muted = true
    const done = (value) => resolve(Number(value) || 0)
    el.onloadedmetadata = () => done(el.duration)
    el.onerror = () => done(0)
    el.src = src
    setTimeout(() => done(0), 8000)
  })
}

/** 统一整理 chooseVideo 的返回值：本地路径 / 文件名 / 大小 / 时长 */
async function resolveVideoMeta(res) {
  const tempFile = res && res.tempFile
  const path = (res && (res.tempFilePath || (res.tempFilePaths && res.tempFilePaths[0]))) || ''
  const name = (tempFile && tempFile.name) || (res && res.name) || fileNameOf(path)
  const size = Number((tempFile && tempFile.size) || (res && res.size) || 0)
  let duration = Number((res && res.duration) || 0)
  if (!duration && path) duration = await probeVideoSeconds(path)
  return { path, name, size, duration: Math.round(duration) }
}

// ---------- 上传 ----------

function chooseRefVideo() {
  uni.chooseVideo({
    sourceType: ['album', 'camera'],
    success: async (res) => {
      const meta = await resolveVideoMeta(res)
      if (!meta.path) return
      // 后端限制参考视频时长，超出直接拦截，避免白等一次上传
      if (meta.duration && meta.duration > maxReferenceSeconds.value) {
        toast(`视频时长不能超过 ${maxReferenceSeconds.value}s`)
        return
      }
      if (meta.size && meta.size > MAX_UPLOAD_MB * 1024 * 1024) {
        toast(`视频不能超过 ${MAX_UPLOAD_MB}MB`)
        return
      }
      remake.refUploading = true
      remake.refProgress = 0
      try {
        const data = await uploadMedia(meta.path, {
          onProgress: (percent) => {
            remake.refProgress = percent
          },
        })
        remake.refVideo = {
          url: data.url,
          name: meta.name || '对标视频',
          duration: meta.duration,
          size: meta.size || data.size || 0,
        }
        // 上传后立即识别原片可替换元素，给"看得见的复刻"预览
        runDetectElements(remake.refVideo.url)
      } catch (err) {
        console.error('上传对标视频失败', err)
        toast(err?.message || '上传失败，请稍后重试')
      } finally {
        remake.refUploading = false
      }
    },
    fail: (err) => {
      // 用户主动取消不算异常，避免刷屏
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择对标视频失败', err)
    },
  })
}

/** 重新上传：先清掉旧的文件状态，再重新选择 */
function retryRefVideo() {
  remake.refVideo = null
  chooseRefVideo()
}

/** 参考视频上传/粘贴后，调用 detect-elements 识别原片可替换元素（人物/产品/场景），用于"看得见的复刻"预览 */
async function runDetectElements(url) {
  if (!url) return
  remake.elements = []
  remake.detecting = true
  try {
    const res = await api.task.detectElements.post({ reference_video: url }, { suppressGlobalError: true })
    if (res && res.code === 1 && res.data && Array.isArray(res.data.elements)) {
      remake.elements = res.data.elements
    }
  } catch (err) {
    console.error('识别原片元素失败', err)
  } finally {
    remake.detecting = false
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
    if (!res || res.code !== 1 || !res.data) {
      toast(res?.message || '拆解失败，请稍后重试')
      remake.decomposing = false
      return
    }
    remake.deconstructId = res.data.id
    pollDeconstruct()
  } catch (err) {
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
  try {
    const res = await api.task.detail.post({ id: remake.deconstructId }, { suppressGlobalError: true })
    if (!res || res.code !== 1 || !res.data) return
    const key = workStatus(res.data.status).key
    if (key === 'success') {
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
  runDetectElements(url)
}

// 替换素材图：支持多张(≤9)，每张标注角色(商品/人物/场景)后下发 image_roles
function chooseReplaceImage() {
  if (remake.replaceUploading) return
  if (remake.replaceImages.length >= 9) {
    toast('最多上传 9 张替换素材')
    return
  }
  uni.chooseImage({
    count: 1,
    success: async (res) => {
      const path = res.tempFilePaths && res.tempFilePaths[0]
      if (!path) return
      remake.replaceUploading = true
      remake.replaceProgress = 0
      try {
        const data = await uploadMedia(path, {
          onProgress: (percent) => {
            remake.replaceProgress = percent
          },
        })
        // 只选了一个意图时，新图默认归到该意图；随后用 AI 识别结果覆盖（更准确），失败则保留默认
        const defaultRole = remake.intent.length === 1 ? remake.intent[0] : 'product'
        const img = { url: data.url, localPath: path, role: defaultRole }
        remake.replaceImages.push(img)
        // 上传后立即让 AI 预标角色（人物/产品/场景），减少手动点选，提升替换准确率
        try {
          const cres = await api.task.classifyImages.post({ urls: [data.url] }, { suppressGlobalError: true })
          const roles = cres && cres.code === 1 && cres.data ? cres.data.roles : null
          const aiRole = roles && roles[data.url]
          if (aiRole) img.role = aiRole
        } catch (err) {
          console.error('替换图角色识别失败，沿用默认角色', err)
        }
      } catch (err) {
        console.error('上传替换素材失败', err)
        toast(err?.message || '上传失败，请稍后重试')
      } finally {
        remake.replaceUploading = false
      }
    },
    fail: (err) => {
      if (!/cancel/i.test(String(err?.errMsg || ''))) console.error('选择替换素材失败', err)
    },
  })
}

function handleReplaceImageTap(idx) {
  if (remake.replaceUploading) return
  uni.showActionSheet({
    itemList: ['替换', '删除'],
    success: ({ tapIndex }) => {
      if (tapIndex === 0) {
        remake.replaceImages.splice(idx, 1)
        chooseReplaceImage()
      } else if (tapIndex === 1) {
        remake.replaceImages.splice(idx, 1)
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
  uni.showActionSheet({
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

function chooseGridImage(index) {
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
  uni.showActionSheet({
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
  uni.showActionSheet({
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
  uni.showActionSheet({
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

function buildRemakePayload() {
  const materials = [remake.refVideo.url, ...remake.replaceImages.map((i) => i.url)]
  const payload = {
    materials,
    real_person_strategy: remake.realPerson,
    remove_watermark: remake.watermark,
    device: 'mobile',
  }
  if (remake.creative) payload.creative_level = remake.creative
  if (remake.hookBoost) payload.hook_boost = remake.hookBoost
  if (remake.format) payload.format = remake.format
  // 主角表现：仅「换人物」时生效，决定新主角以跳舞/讲解方式表演（与后端 lead_act 白名单一致）
  // 主角表现：仅在上传了「人物」角色素材时生效，决定新主角以跳舞/讲解方式表演
  if (remake.replaceImages.some((i) => i.role === 'person') && remake.leadAct) payload.lead_act = remake.leadAct
  if (remake.duration) payload.duration = Number(remake.duration)
  if (remake.ratio) payload.ratio = remake.ratio
  if (remake.resolution) payload.resolution = remake.resolution
  if (remake.goal && remake.goal.trim()) payload.goal = remake.goal.trim().slice(0, 200)
  // 替换意图：用户显式选择优先；否则由上传图的角色推导，与后端 resolve_intent 口径一致
  const intent = remake.intent.length
    ? remake.intent
    : [...new Set(remake.replaceImages.map((i) => i.role).filter(Boolean))]
  if (intent.length) payload.intent = intent
  // 素材图 → 角色：强提示视觉模型"这张是商品/人物/场景"，显著提升替换准确率
  const imageRoles = {}
  remake.replaceImages.forEach((i) => {
    if (i.role) imageRoles[i.url] = i.role
  })
  if (Object.keys(imageRoles).length) payload.image_roles = imageRoles
  if (templateId.value) payload.template_id = templateId.value
  // 拆解分镜：把用户可编辑的逐镜逆推描述平铺进 remark 下发生成（与桌面端 Replicate.vue 同源），
  // 让"看得见的复刻"真正影响出片；字段缺省时各段沿用原片，不臆造画面。
  if (remake.shots.length) {
    const lines = remake.shots.map(
      (s) =>
        `镜头${s.index + 1}(${Number(s.start).toFixed(1)}-${Number(s.end).toFixed(1)}s): ${
          s.description || s.narration || '参考原片'
        }`,
    )
    payload.remark = lines.join('\n')
  }
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
const guideSteps = [
  { title: '上传对标视频', desc: '任意爆款 / 探店 / 好物视频，本地或直链' },
  { title: '描述想改成什么样', desc: '上传替换图 + 一句话说清（选填）' },
  { title: '一键出片', desc: 'AI 拆解后自动生成，原地看进度' },
]
/** 引导步骤状态：done=已完成 / active=当前 / todo=未到 */
function guideStepState(i) {
  const hasVideo = !!remake.refVideo
  const described = !!(remake.goal && remake.goal.trim()) || remake.replaceImages.length > 0
  if (i === 0) return hasVideo ? 'done' : 'active'
  if (i === 1) return !hasVideo ? 'todo' : described ? 'done' : 'active'
  return !hasVideo || !described ? 'todo' : 'active'
}
/** 点引导步骤滚动到对应区块，帮用户"直接上手" */
function scrollToStep(i) {
  const sel = ['#remake-upload', '#remake-goal', '#remake-generate'][i]
  if (sel) uni.pageScrollTo({ selector: sel, duration: 300 })
}

async function handleGenerate() {
  if (submitting.value) return
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
  // 建单前预检：服务端结构化校验，缺失项直接引导用户补齐，避免生成失败才报缺素材
  try {
    const prePayload = {
      materials: [remake.refVideo.url, ...remake.replaceImages.map((i) => i.url)],
      intent: remake.intent.length ? remake.intent : undefined,
      reference_video: remake.refVideo.url,
      duration: remake.refVideo.duration || undefined,
    }
    const preRes = await api.task.precheck.post(prePayload, { suppressGlobalError: true })
    if (preRes && preRes.code === 1 && preRes.data) {
      // 真人照片做「换人物」属提示项（非阻断），其余为硬缺失，需先补齐再建单
      const blocking = (preRes.data.missing || []).filter((m) => m.field !== 'real_person_unsupported')
      if (blocking.length) {
        toast(`${blocking[0].label}：${blocking[0].hint}`)
        return
      }
    }
  } catch (err) {
    // 预检接口异常不阻断建单：以 create 的兜底校验为准
    console.error('预检失败，继续建单', err)
  }

  submitting.value = true
  try {
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
  try {
    const res = await api.task.detail.post({ id: gen.taskId }, { suppressGlobalError: true })
    if (res && res.code === 1 && res.data) {
      gen.task = res.data
      const status = workStatus(res.data.status).key
      if (status === 'success' || status === 'failed') {
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
  if (estimateTimer) clearTimeout(estimateTimer)
  remake.refVideo = null
  remake.replaceImages = []
  remake.intent = []
  remake.goal = ''
  remake.elements = []
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

/* ============ 已选模板 ============ */
.studio__template {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 16px 0;
  padding: 12px 14px;
  background: var(--brand-primary-light);
  border: 1px solid rgba(79, 70, 229, 0.15);
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
  gap: 8px;
  padding: 16px;
  background: var(--bg-card);
}

.studio__mode {
  flex: 1;
  padding: 14px 12px;
  border-radius: var(--radius-lg);
  border: 2px solid var(--border-light);
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  transition: all var(--transition-fast);

  &--active {
    border-color: var(--brand-primary);
    background: var(--brand-primary-light);
  }
}

.studio__mode-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.studio__mode-title {
  font-size: 13px;
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
  padding: 12px 16px;
}

.studio__card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 16px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 12px;

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
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--grad-brand-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.studio__upload-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.studio__upload-hint {
  font-size: 12px;
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
  aspect-ratio: 1 / 1;
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
  width: 100%;
  height: 100%;
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
  background: var(--bg-input, #f8fafc);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  box-sizing: border-box;
}

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
  background: var(--bg-card);
  border-top: 1px solid var(--border-light);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  z-index: 99;
  box-shadow: 0 -4px 12px rgba(15, 23, 42, 0.06);
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
  height: 48px;

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
  aspect-ratio: 1 / 1;
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
  background: rgba(15, 23, 42, 0.62);
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
  padding: 10px 12px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-input, #f8fafc);
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
  font-size: 11px;
  color: var(--text-muted);
}

/* ============ 原片元素识别预览（看得见的复刻） ============ */
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
  background: rgba(15, 23, 42, 0.62);
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
  z-index: 400;
  display: flex;
  align-items: flex-end;
  justify-content: center;

  &__mask {
    position: absolute;
    inset: 0;
    background: rgba(15, 23, 42, 0.5);
  }

  &__sheet {
    position: relative;
    width: 100%;
    padding: 20px 16px calc(20px + env(safe-area-inset-bottom));
    background: var(--bg-card);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.12);
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
    width: 32px;
    height: 32px;
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
      animation: app-pop 0.3s ease-out;
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
    background: #000000;
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
  animation: app-glow 2.2s ease-in-out infinite;

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
    animation: app-spin 1.1s linear infinite;
  }

  &__spin--inner {
    inset: 6px;
    border-bottom-color: #a5b4fc;
    border-left-color: #a5b4fc;
    animation: app-spin 1.9s linear infinite reverse;
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
    transition: width 0.7s cubic-bezier(0.4, 0, 0.2, 1);
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
    background: #e2e8f0;
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
.studio__guide {
  display: flex;
  gap: 8px;
  margin: 12px 16px 0;
}
.studio__guide-step {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
}
.studio__guide-step--active {
  border-color: var(--brand-primary);
  background: var(--brand-primary-light);
}
.studio__guide-step--done {
  border-color: rgba(16, 185, 129, 0.4);
}
.studio__guide-no {
  flex: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #ffffff;
  background: var(--text-muted);
}
.studio__guide-step--active .studio__guide-no {
  background: var(--brand-primary);
}
.studio__guide-step--done .studio__guide-no {
  background: #10b981;
}
.studio__guide-body {
  flex: 1;
  min-width: 0;
}
.studio__guide-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.studio__guide-desc {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--text-muted);
}

</style>
