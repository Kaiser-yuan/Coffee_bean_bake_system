<template>
  <div class="curve-page">
    <!-- 顶部导航栏 -->
    <div class="page-header">
      <div class="header-left">
        <button class="btn btn-text" @click="$router.back()">← 返回</button>
        <h2 class="page-heading">
          {{ isCompare ? `多锅对比 (${batchIds.length} 锅)` : '曲线分析' }}
        </h2>
        <span v-if="!isCompare && currentBatch" class="text-sm text-secondary">
          {{ getBeanName(currentBatch.id) }} · {{ currentBatch.actualDate || currentBatch.plannedDate }}
          <span
            v-for="tag in batchSourceLabels(currentBatch.entryMode, currentBatch.inventoryEffective)"
            :key="tag"
            class="batch-source-tag"
          >{{ tag }}</span>
        </span>
      </div>
      <div class="header-right">
        <input
          ref="curveFileInput"
          type="file"
          accept=".csv,text/csv"
          hidden
          @change="onCurveFileSelected"
        />
        <button
          v-if="!isCompare && currentBatch"
          class="btn btn-secondary"
          :disabled="uploadingCurve"
          @click="curveFileInput?.click()"
        >
          {{ uploadingCurve ? '上传解析中…' : (curves.length ? '重新上传曲线' : '上传曲线 CSV') }}
        </button>
        <!-- 问卷按钮：只有已完成批次才显示 -->
        <button
          v-if="!isCompare && currentBatch && currentBatch.status === 'completed' && !questionnaireCreated"
          class="btn btn-secondary"
          @click="createQuestionnaire"
        >
          发起评价问卷
        </button>
        <button
          v-if="!isCompare && currentBatch && questionnaireCreated"
          class="btn btn-secondary"
          disabled
        >
          {{ questionnaireStatusText }}
        </button>
        <button
          v-if="!isCompare && currentBatch && questionnaireShareCode"
          class="btn btn-secondary"
          @click="copyQuestionnaireLink"
        >
          复制问卷链接
        </button>
        <button
          v-if="!isCompare && currentBatch && questionnaireId"
          class="btn btn-secondary"
          @click="goToQuestionnaireDetail"
        >
          查看评价详情
        </button>
        <span v-if="!isCompare && currentBatch && currentBatch.status !== 'completed'" class="text-xs text-tertiary">
          待批次完成后才可发起问卷
        </span>
        <button
          v-if="!isCompare && currentBatch"
          class="btn btn-primary"
          @click="goToReview"
        >
          进入复盘
        </button>
      </div>
    </div>

    <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>

    <LoadingState v-if="loading" text="加载曲线数据…" />
    <ErrorState v-else-if="error" title="曲线加载失败" :message="loadError" :retry="true" @retry="fetchCurves" />

    <template v-else-if="curves.length">
      <!-- KPI 横向摘要条 -->
      <section class="kpi-bar" v-if="!isCompare && currentBatch">
        <div class="kpi-item">
          <span class="kpi-label">总时长</span>
          <span class="kpi-val num">{{ formatTime(currentBatch.totalTime || 0) }}</span>
        </div>
        <div class="kpi-divider"></div>
        <div class="kpi-item">
          <span class="kpi-label">发展率</span>
          <span class="kpi-val num">{{ currentBatch.developmentRatio ? currentBatch.developmentRatio.toFixed(1) + '%' : '-' }}</span>
        </div>
        <div class="kpi-divider"></div>
        <div class="kpi-item">
          <span class="kpi-label">失重率</span>
          <span class="kpi-val num">{{ currentBatch.weightLossRate ? currentBatch.weightLossRate.toFixed(1) + '%' : '-' }}</span>
        </div>
        <div class="kpi-divider"></div>
        <div class="kpi-item">
          <span class="kpi-label">投豆量</span>
          <span class="kpi-val num">{{ currentBatch.beanWeightIn }}g</span>
        </div>
        <div class="kpi-divider"></div>
        <div class="kpi-item">
          <span class="kpi-label">出豆量</span>
          <span class="kpi-val num">{{ currentBatch.beanWeightOut ? currentBatch.beanWeightOut + 'g' : '未录入' }}</span>
        </div>
        <div class="kpi-divider"></div>
        <div class="kpi-item">
          <span class="kpi-label">养豆天数</span>
          <span class="kpi-val num">{{ beanAgeDays > 0 ? beanAgeDays + '天' : '-' }}</span>
        </div>
      </section>

      <!-- 曲线工作区 -->
      <section class="curve-workspace">
        <!-- 图例控件 — 放在工作区顶部 -->
        <div class="workspace-legend">
          <div class="legend-group">
            <span class="legend-label">指标</span>
            <label
              v-for="channel in channels"
              :key="channel.key"
              class="legend-item"
              :class="{ dimmed: !channel.visible }"
              @click="toggleChannel(channel.key)"
            >
              <span class="legend-line" :style="{ background: channel.color }"></span>
              {{ channel.label }}
            </label>
          </div>

          <div v-if="isCompare" class="legend-group">
            <span class="legend-label">批次</span>
            <label
              v-for="(c, i) in curves"
              :key="c.id"
              class="legend-item"
              :class="{ dimmed: !batchVisible[i] }"
              @click="toggleBatch(i)"
            >
              <span class="legend-dot" :style="{ background: batchColors[i] }"></span>
              {{ getBatchShortLabel(c.roastingBatchId) }}
            </label>
          </div>

          <!-- 多锅查看模式切换 -->
          <div v-if="isCompare" class="legend-group">
            <span class="legend-label">模式</span>
            <button
              class="btn btn-xs"
              :class="compareMode === 'batch' ? 'btn-primary' : 'btn-secondary'"
              @click="compareMode = 'batch'"
            >按批次</button>
            <button
              class="btn btn-xs"
              :class="compareMode === 'channel' ? 'btn-primary' : 'btn-secondary'"
              @click="compareMode = 'channel'"
            >按指标</button>
          </div>

          <!-- 对齐方式选择 — 仅对比模式 (P0-2) -->
          <div v-if="isCompare" class="legend-group">
            <span class="legend-label">对齐</span>
            <select v-model="compareAlignBy" class="align-select" @change="fetchCurves">
              <option v-for="o in ALIGN_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>
          </div>
        </div>

        <!-- 对比诊断：缺失曲线 / 缺失事件 (P0-2) -->
        <div v-if="isCompare && compareWarnings.length" class="compare-warnings">
          <span v-for="(w, i) in compareWarnings" :key="i" class="warn-item">⚠ {{ w }}</span>
        </div>

        <!-- 图表主体 -->
        <div class="chart-container" ref="mainChartRef"></div>
      </section>

      <!-- 事件时间轴 -->
      <section class="events-bar" v-if="!isCompare && currentCurve">
        <span class="text-xs text-tertiary font-medium">关键事件</span>
        <span
          v-for="ev in currentCurve.events"
          :key="ev.type"
          class="event-tag"
          :class="ev.type"
        >
          {{ ev.label }}: {{ formatTime(ev.time) }}
        </span>
      </section>
    </template>

    <EmptyState v-else icon="📈" title="该批次暂无曲线数据" description="点击右上角“上传曲线 CSV”，支持 Kaleido M1 KLDO V101 文件。" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchCurves as fetchCurvesSvc, fetchCurve, uploadCurve, getLastComparisonWarnings } from '../services/curveService'
import { ApiError } from '../api/http'
import { createQuestionnaire as createQuestionnaireSvc } from '../services/questionnaireService'
import { fetchRoastContext, getGreenBeanByBatch, invalidateRoastContext, type RoastContext } from '../services/greenBeanContextService'
import type { RoastingCurve } from '../types'
import { batchSourceLabels } from '../utils/batchLabels'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import EmptyState from '../components/common/EmptyState.vue'
import * as echarts from 'echarts'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref(false)
const loadError = ref('请确认后端服务和曲线数据状态。')
const uploadError = ref('')
const uploadingCurve = ref(false)
const curveFileInput = ref<HTMLInputElement>()
const curves = ref<RoastingCurve[]>([])
const batchVisible = ref<boolean[]>([])
const compareMode = ref<'batch' | 'channel'>('batch')
const questionnaireCreated = ref(false)
const questionnaireStatusText = ref('')
const questionnaireId = ref('')
const questionnaireShareCode = ref('')
const roastContext = ref<RoastContext>({ greenBeans: [], purchaseBatches: [], roastingBatches: [] })

// Curve comparison alignment + diagnostics (P0-2).
// compareAlignBy mirrors the backend align_by: none|charge|yellowing|first_crack_start|drop.
const compareAlignBy = ref<'none' | 'charge' | 'yellowing' | 'first_crack_start' | 'drop'>('charge')
const compareWarnings = ref<string[]>([])

const ALIGN_OPTIONS: { value: typeof compareAlignBy.value; label: string }[] = [
  { value: 'none', label: '原始时间' },
  { value: 'charge', label: '入豆' },
  { value: 'yellowing', label: '转黄' },
  { value: 'first_crack_start', label: '一爆开始' },
  { value: 'drop', label: '出豆' },
]

// 指标通道定义 — 单锅：指标颜色+线型；多锅：批次颜色+指标线型
const channels = ref([
  { key: 'beanTempCelsius', label: '豆温 BT', color: '#df5b45', visible: true, lineStyle: 'solid' as const },
  { key: 'environmentTempCelsius', label: '环境温 ET', color: '#e5a029', visible: true, lineStyle: 'solid' as const },
  { key: 'rorCelsiusPerMinute', label: 'RoR · 右轴', color: '#3478d4', visible: true, lineStyle: 'dashed' as const },
  { key: 'heatingPowerPercent', label: '火力 HP', color: '#8b5cc7', visible: true, lineStyle: 'step' as const },
  { key: 'smokeDamperPercent', label: '风门 SM', color: '#20a184', visible: true, lineStyle: 'step' as const },
  { key: 'rollerPercent', label: '滚筒 RL', color: '#718096', visible: true, lineStyle: 'step' as const },
])

const batchColors = ['#df5b45', '#3478d4', '#1f9d68', '#8b5cc7', '#e5a029', '#d94b4b']
const mainChartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const isCompare = computed(() => route.name === 'curve-compare')
const batchIds = computed(() => {
  if (isCompare.value) {
    return (route.params.ids as string).split(',').filter(Boolean)
  }
  return [route.params.batchId as string]
})

const currentBatch = computed(() => {
  if (isCompare.value) return null
  return roastContext.value.roastingBatches.find(b => b.id === batchIds.value[0])
})

const currentCurve = computed(() => curves.value[0])

const beanAgeDays = computed(() => {
  if (!currentBatch.value?.actualDate) return 0
  const bakeDate = new Date(currentBatch.value.actualDate)
  const today = new Date()
  return Math.floor((today.getTime() - bakeDate.getTime()) / (1000 * 60 * 60 * 24))
})

function getBeanName(batchId: string) {
  const batch = roastContext.value.roastingBatches.find(b => b.id === batchId)
  if (!batch) return '-'
  return getGreenBeanByBatch(roastContext.value, batch)?.name || '-'
}

function getBatchShortLabel(batchId: string) {
  const b = roastContext.value.roastingBatches.find(b => b.id === batchId)
  if (!b) return batchId
  const gb = getGreenBeanByBatch(roastContext.value, b)
  return `${gb?.name || ''} (${b.actualDate || b.plannedDate})`
}

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

function goToReview() {
  if (currentBatch.value) {
    router.push(`/review/${currentBatch.value.id}`)
  }
}

const questionnaireShareUrl = computed(() => {
  if (!questionnaireShareCode.value) return ''
  const base = `${window.location.origin}${window.location.pathname}`
  return `${base}${base.endsWith('/') ? '' : '/'}#/eval/${questionnaireShareCode.value}`
})

async function writeClipboardText(text: string) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // Fall back for non-secure contexts such as plain http://server-ip.
    }
  }

  const input = document.createElement('textarea')
  input.value = text
  input.setAttribute('readonly', 'true')
  input.style.position = 'fixed'
  input.style.left = '-9999px'
  document.body.appendChild(input)
  input.select()
  const copied = document.execCommand('copy')
  document.body.removeChild(input)
  return copied
}

async function copyQuestionnaireLink() {
  if (!questionnaireShareUrl.value) return
  const copied = await writeClipboardText(questionnaireShareUrl.value)
  window.alert(copied ? '已复制评价链接' : `复制失败，请手动复制：${questionnaireShareUrl.value}`)
}

function goToQuestionnaireDetail() {
  if (questionnaireId.value) router.push(`/evaluations/${questionnaireId.value}`)
}

function applyQuestionnaireState(q: { id: string; shareCode: string; status: string } | null) {
  questionnaireCreated.value = !!q
  questionnaireId.value = q?.id || ''
  questionnaireShareCode.value = q?.shareCode || ''
  questionnaireStatusText.value = q
    ? (q.status === 'open' ? '评价进行中' : '评价已关闭')
    : ''
}

async function createQuestionnaire() {
  if (!currentBatch.value) return
  const questionnaire = await createQuestionnaireSvc(currentBatch.value.id)
  applyQuestionnaireState(questionnaire)
  const updated = roastContext.value.roastingBatches.find(b => b.id === currentBatch.value?.id)
  if (updated) updated.evaluationStatus = 'open'
}

function toggleChannel(key: string) {
  const ch = channels.value.find(c => c.key === key)
  if (ch) ch.visible = !ch.visible
  renderChart()
}

function toggleBatch(index: number) {
  batchVisible.value[index] = !batchVisible.value[index]
  renderChart()
}

async function fetchCurves() {
  // Dispose any previous ECharts instance first: on re-upload / batch switch
  // the old container is destroyed, so a stale instance would draw nowhere.
  chart?.dispose()
  chart = null

  loading.value = true
  error.value = false
  loadError.value = '请确认后端服务和曲线数据状态。'
  let shouldRender = false

  try {
    const allCurves = batchIds.value.length > 1
      ? await fetchCurvesSvc(batchIds.value, compareAlignBy.value)
      : [await fetchCurve(batchIds.value[0])].filter(Boolean) as RoastingCurve[]
    curves.value = batchIds.value
      .map(id => allCurves.find(c => c.roastingBatchId === id))
      .filter(Boolean) as RoastingCurve[]
    batchVisible.value = curves.value.map(() => true)

    // Surface backend comparison warnings (missing curves / events) for the user.
    compareWarnings.value = getLastComparisonWarnings()

    // Check if questionnaire already exists
    if (!isCompare.value && currentBatch.value) {
      const qs = await import('../services/questionnaireService')
      const allQ = await qs.fetchQuestionnaires()
      const existingQ = allQ.find(q => q.roastingBatchId === currentBatch.value!.id)
      applyQuestionnaireState(existingQ || null)
    }

    shouldRender = curves.value.length > 0
  } catch (e) {
    error.value = true
    loadError.value = e instanceof ApiError ? e.message : '曲线加载失败'
  } finally {
    // End loading FIRST so the v-if container is mounted before we draw.
    loading.value = false
  }

  // Only render after the container is back in the DOM.
  if (shouldRender) {
    await nextTick()
    renderChart()
  }
}

async function onCurveFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !currentBatch.value) return

  uploadError.value = ''
  if (!file.name.toLowerCase().endsWith('.csv')) {
    uploadError.value = '请选择 .csv 曲线文件'
    return
  }

  uploadingCurve.value = true
  try {
    await uploadCurve(currentBatch.value.id, file)
    invalidateRoastContext()
    roastContext.value = await fetchRoastContext()
    await fetchCurves()
  } catch (e) {
    uploadError.value = e instanceof ApiError ? e.message : '曲线上传或解析失败'
  } finally {
    uploadingCurve.value = false
  }
}

function renderChart() {
  if (!mainChartRef.value || !curves.value.length) return

  if (!chart) {
    chart = echarts.init(mainChartRef.value)
  }

  const visibleChannels = channels.value.filter(c => c.visible)
  const gridLeft = 60
  const gridTop = 10

  // X-axis value per point. In comparison mode with an alignment event,
  // use aligned_seconds (relative to the event) so curves overlay; fall back
  // to elapsed_seconds otherwise. Single-pot mode always uses elapsed_seconds.
  const useAlign = isCompare.value && compareAlignBy.value !== 'none'
  const xOf = (p: { elapsedSeconds: number; alignedSeconds?: number }) =>
    useAlign ? (p.alignedSeconds ?? p.elapsedSeconds) : p.elapsedSeconds

  const builtSeries: any[] = []

  if (!isCompare.value) {
    // 单锅模式：指标颜色 + 线型区分
    visibleChannels.forEach(ch => {
      curves.value.forEach(curve => {
        const points = curve.points
        const values = points.map(p => [xOf(p), p[ch.key as keyof typeof p]])
          .filter(v => v[1] !== undefined && v[1] !== null)

        const isStep = ['heatingPowerPercent', 'smokeDamperPercent', 'rollerPercent'].includes(ch.key)
        const needsSecondaryGrid = ['heatingPowerPercent', 'smokeDamperPercent', 'rollerPercent'].includes(ch.key)
        const gridIdx = needsSecondaryGrid ? 1 : 0

        builtSeries.push({
          name: ch.label,
          type: 'line',
          xAxisIndex: gridIdx,
          yAxisIndex: needsSecondaryGrid ? 2 : (ch.key === 'rorCelsiusPerMinute' ? 1 : 0),
          data: values,
          smooth: false,
          step: isStep ? 'end' : false,
          lineStyle: {
            color: ch.color,
            width: 1.5,
            type: ch.lineStyle === 'dashed' ? 'dashed' : 'solid',
          },
          itemStyle: { color: ch.color },
          symbol: 'none',
        })
      })
    })
  } else if (compareMode.value === 'batch') {
    // 多锅按批次对比：批次颜色 + 线型区分指标
    visibleChannels.forEach(ch => {
      curves.value.forEach((curve, bi) => {
        if (!batchVisible.value[bi]) return
        const points = curve.points
        const values = points.map(p => [xOf(p), p[ch.key as keyof typeof p]])
          .filter(v => v[1] !== undefined && v[1] !== null)

        const isStep = ['heatingPowerPercent', 'smokeDamperPercent', 'rollerPercent'].includes(ch.key)
        const needsSecondaryGrid = ['heatingPowerPercent', 'smokeDamperPercent', 'rollerPercent'].includes(ch.key)
        const gridIdx = needsSecondaryGrid ? 1 : 0

        builtSeries.push({
          name: `${ch.label}·批次${bi + 1}`,
          type: 'line',
          xAxisIndex: gridIdx,
          yAxisIndex: needsSecondaryGrid ? 2 : (ch.key === 'rorCelsiusPerMinute' ? 1 : 0),
          data: values,
          smooth: false,
          step: isStep ? 'end' : false,
          lineStyle: {
            color: batchColors[bi],
            width: 2,
            type: ch.lineStyle === 'dashed' ? 'dashed' : 'solid',
          },
          itemStyle: { color: batchColors[bi] },
          symbol: 'none',
        })
      })
    })
  } else {
    // 多锅按指标对比：只显示一个指标，不同颜色区分批次
    const singleChannel = visibleChannels[0] || channels.value[0]
    curves.value.forEach((curve, bi) => {
      if (!batchVisible.value[bi]) return
      const points = curve.points
      const values = points.map(p => [xOf(p), p[singleChannel.key as keyof typeof p]])
        .filter(v => v[1] !== undefined && v[1] !== null)

      builtSeries.push({
        name: `${singleChannel.label}·批次${bi + 1}`,
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: values,
        smooth: false,
        step: false,
        lineStyle: { color: batchColors[bi], width: 2 },
        itemStyle: { color: batchColors[bi] },
        symbol: 'none',
      })
    })
  }

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e5e9f2',
      textStyle: { fontSize: 11, color: '#172033' },
      formatter: (params: any) => {
        if (!Array.isArray(params)) params = [params]
        const time = params[0]?.data?.[0]
        let html = `<div style="font-weight:600;margin-bottom:4px">${formatTime(time)}</div>`
        params.forEach((p: any) => {
          html += `<div style="display:flex;gap:12px;justify-content:space-between">
            <span style="color:${p.color}">${p.seriesName}</span>
            <span class="num">${p.data?.[1]}</span>
          </div>`
        })
        return html
      },
    },
    legend: { show: false },
    grid: [
      { left: gridLeft, right: 80, top: gridTop, height: '42%' },
      { left: gridLeft, right: 80, top: '58%', height: '14%' },
    ],
    xAxis: [
      {
        type: 'value',
        gridIndex: 0,
        axisLabel: { fontSize: 10, color: '#5d6880', formatter: (v: number) => formatTime(v) },
        splitLine: { lineStyle: { color: '#e5e9f2' } },
        minInterval: 30,
      },
      {
        type: 'value',
        gridIndex: 1,
        axisLabel: { fontSize: 10, color: '#5d6880', formatter: (v: number) => formatTime(v) },
        splitLine: { lineStyle: { color: '#e5e9f2' } },
        minInterval: 30,
      },
    ],
    yAxis: [
      {
        gridIndex: 0, type: 'value',
        name: '°C',
        nameTextStyle: { fontSize: 10, color: '#df5b45' },
        splitLine: { lineStyle: { color: '#e5e9f2' } },
        axisLabel: { fontSize: 10, color: '#df5b45' },
        min: 0,
      },
      {
        gridIndex: 0, type: 'value',
        name: '°C/分钟',
        nameTextStyle: { fontSize: 10, color: '#3478d4' },
        splitLine: { show: false },
        axisLabel: { fontSize: 10, color: '#3478d4' },
        min: 0, max: 15,
      },
      {
        gridIndex: 1, type: 'value',
        name: '%',
        max: 100,
        nameTextStyle: { fontSize: 10, color: '#718096' },
        splitLine: { lineStyle: { color: '#e5e9f2' } },
        axisLabel: { fontSize: 10, color: '#718096' },
      },
    ],
    series: builtSeries,
  }, { notMerge: false })
}

watch(() => route.params, fetchCurves)

function handleResize() {
  chart?.resize()
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  await fetchRoastContext().then(ctx => { roastContext.value = ctx })
  await fetchCurves()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.curve-page { max-width: 100%; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-4);
  gap: var(--sp-3);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.page-heading { font-size: var(--fs-xl); font-weight: 600; }

.upload-error {
  margin-bottom: var(--sp-3);
  padding: var(--sp-3);
  border: 1px solid var(--danger);
  border-radius: var(--radius-md);
  background: var(--danger-subtle);
  color: var(--danger);
  font-size: var(--fs-sm);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

/* KPI bar */
.kpi-bar {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-3) var(--sp-6);
  display: flex;
  align-items: center;
  margin-bottom: var(--sp-4);
}

.kpi-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-label { font-size: var(--fs-xs); color: var(--text-tertiary); }
.kpi-val { font-size: var(--fs-lg); font-weight: 600; font-family: var(--font-mono); }

.kpi-divider {
  width: 1px;
  height: 36px;
  background: var(--border-default);
  margin: 0 var(--sp-6);
}

/* Curve workspace — single large area */
.curve-workspace {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: var(--sp-4);
}

.workspace-legend {
  display: flex;
  gap: var(--sp-6);
  padding: var(--sp-3) var(--sp-4);
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-subtle);
  flex-wrap: wrap;
}

.legend-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.legend-label {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-weight: 500;
  text-transform: uppercase;
  margin-right: var(--sp-1);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-sm);
  cursor: pointer;
  color: var(--text-primary);
  user-select: none;
  padding: 2px 4px;
  border-radius: var(--radius-sm);
}

.legend-item:hover { background: var(--surface-selected); }

.legend-item.dimmed { opacity: 0.3; }

.legend-line {
  width: 16px;
  height: 3px;
  border-radius: 1px;
}

.legend-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.chart-container {
  width: 100%;
  height: 480px;
}

/* Events bar */
.events-bar {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.event-tag {
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-xs);
  font-weight: 500;
  background: var(--app-bg);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

/* Buttons */
.btn {
  height: var(--btn-height);
  padding: 0 var(--sp-4);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  font-family: var(--font-sans);
}

.btn-xs { height: 24px; padding: 0 var(--sp-2); font-size: var(--fs-xs); }

.align-select {
  height: 24px;
  padding: 0 var(--sp-2);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-default);
  background: var(--surface);
  font-size: var(--fs-xs);
  color: var(--text-primary);
}

.compare-warnings {
  padding: var(--sp-2) var(--sp-4);
  border-top: 1px solid var(--border-default);
  background: var(--warning-subtle);
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-3);
}
.warn-item { font-size: var(--fs-xs); color: var(--warning); }

.btn-primary { background: var(--primary); color: #fff; border-color: var(--primary); }
.btn-primary:hover { background: var(--primary-hover); }
.btn-secondary { background: var(--surface); color: var(--text-primary); border-color: var(--border-default); }
.btn-secondary:hover { background: var(--app-bg); }
.btn-text { background: transparent; color: var(--text-secondary); border-color: transparent; }
.btn-text:hover { color: var(--text-primary); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
