<template>
  <div class="dashboard">
    <!-- 页面标题 + 年份切换 -->
    <div class="page-header">
      <h2 class="page-heading">系统总览</h2>
      <div class="year-switcher">
        <button class="year-btn" @click="prevYear" title="上一年">‹</button>
        <span class="year-label num">{{ store.currentYear }}</span>
        <button class="year-btn" @click="nextYear" title="下一年">›</button>
      </div>
    </div>

    <LoadingState v-if="loading" text="加载年度数据…" />
    <ErrorState v-else-if="error" title="无法加载数据" :message="errorMsg" :retry="true" @retry="fetchData" />

    <template v-else-if="data">
      <!-- 核心指标 — 横向摘要条 -->
      <section class="kpi-bar">
        <div class="kpi-item">
          <span class="kpi-label">已完成锅数</span>
          <span class="kpi-value num">{{ data.totalRoasts }}</span>
        </div>
        <div class="kpi-divider"></div>
        <div class="kpi-item">
          <span class="kpi-label">已烘豆款数</span>
          <span class="kpi-value num">{{ data.totalRoastedBeanProfiles }}</span>
        </div>
        <div class="kpi-divider"></div>
        <div class="kpi-item">
          <span class="kpi-label">总投豆重量</span>
          <span class="kpi-value num">{{ formatWeight(data.totalInputWeight) }}</span>
        </div>
        <div class="kpi-divider"></div>
        <div class="kpi-item">
          <span class="kpi-label">平均失重率</span>
          <span class="kpi-value num">{{ data.avgWeightLossRate }}%</span>
        </div>
      </section>

      <!-- 图表区域 -->
      <section class="charts-row">
        <div class="chart-block chart-block--main">
          <h3 class="chart-title">月度烘焙频率</h3>
          <div ref="monthlyChartRef" class="chart-box"></div>
        </div>
        <div class="chart-block">
          <h3 class="chart-title">豆种分布</h3>
          <div ref="varietyChartRef" class="chart-box"></div>
        </div>
        <div class="chart-block">
          <h3 class="chart-title">产区分布</h3>
          <div ref="regionChartRef" class="chart-box"></div>
        </div>
      </section>

      <!-- 待烘豆列表 -->
      <section class="list-section">
        <h3 class="section-title">
          待烘豆列表
          <span class="badge">{{ totalPendingCount }}</span>
        </h3>

        <div class="pending-tree" v-if="pendingGrouped.length">
          <div
            v-for="group in pendingGrouped"
            :key="group.beanId"
            class="tree-group"
          >
            <!-- 一级：豆款 -->
            <div
              class="tree-row tree-row-l1"
              @click="toggleBean(group.beanId)"
            >
              <span class="tree-expand">{{ expandedBeans.has(group.beanId) ? '▾' : '▸' }}</span>
              <span class="tree-bean-name">{{ group.beanName }}</span>
              <span class="tree-bean-meta">{{ group.variety }} · {{ group.process }} · {{ group.region }}</span>
              <span class="tree-count">{{ group.batches.length }} 个计划</span>
            </div>

            <!-- 二级：该豆款下的待烘计划 -->
            <div v-if="expandedBeans.has(group.beanId)" class="tree-children">
              <div
                v-for="b in group.batches"
                :key="b.id"
                class="tree-row tree-row-l2"
              >
                <span class="tree-expand-spacer"></span>
                <span class="tree-target">{{ b.targetDescription || '未指定目标' }}</span>
                <span class="tree-date">{{ b.plannedDate }}</span>
                <span class="tree-weight num">{{ b.beanWeightIn }}g</span>
                <span class="tree-pb">{{ getPurchaseLabel(b.purchaseBatchId) }}</span>
                <label class="tree-check" @click.stop>
                  <input
                    type="checkbox"
                    @change="onConfirmComplete(b)"
                  />
                  标记完成
                </label>
              </div>
            </div>
          </div>
        </div>

        <EmptyState
          v-else
          icon="✅"
          title="暂无待烘计划"
          description="前往生豆管理页面，在采购批次下创建待烘计划"
        />
      </section>

      <!-- 最近烘豆 -->
      <section class="list-section">
        <h3 class="section-title">最近烘豆</h3>
        <table class="data-table" v-if="data.recentBatches.length">
          <thead>
            <tr>
              <th>烘焙时间</th>
              <th>生豆名称</th>
              <th>豆种</th>
              <th>投豆/出豆</th>
              <th>失重率</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="b in data.recentBatches"
              :key="b.id"
              class="clickable"
              @click="goToCurve(b.id)"
            >
              <td class="num">{{ b.actualDate || b.plannedDate }}</td>
              <td>{{ getBeanName(b.purchaseBatchId) }}</td>
              <td>{{ getBeanVariety(b.purchaseBatchId) }}</td>
              <td class="num">{{ b.beanWeightIn }}g / {{ b.beanWeightOut ?? '-' }}g</td>
              <td class="num">{{ b.weightLossRate ? b.weightLossRate.toFixed(1) + '%' : '-' }}</td>
              <td>
                <span class="status-dot" :class="b.status === 'completed' ? 'success' : 'warning'"></span>
                {{ BATCH_STATUS_LABELS[b.status] }}
              </td>
            </tr>
          </tbody>
        </table>
        <EmptyState v-else icon="🔥" title="暂无烘焙记录" />
      </section>

      <!-- 确认完成弹窗 -->
      <div v-if="confirmBatch" class="modal-overlay" @click.self="confirmBatch = null">
        <div class="modal">
          <div class="modal-header">
            <h3>确认烘焙完成</h3>
            <button class="modal-close" @click="confirmBatch = null">✕</button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <label class="form-label">实际投豆量 (g)</label>
              <input v-model.number="confirmForm.beanWeightIn" type="number" class="input" />
            </div>
            <div class="form-row">
              <label class="form-label">实际烘焙日期</label>
              <input v-model="confirmForm.actualDate" type="date" class="input" />
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="confirmBatch = null">取消</button>
            <button class="btn btn-primary" @click="doComplete">确认完成</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import { BATCH_STATUS_LABELS } from '../types'
import type { DashboardYearData, RoastingBatch } from '../types'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import EmptyState from '../components/common/EmptyState.vue'
import * as echarts from 'echarts'
import { fetchDashboard } from '../services/dashboardService'
import { completeRoastingBatch } from '../services/roastingBatchService'
import {
  fetchRoastContext,
  invalidateRoastContext,
  getGreenBeanByBatch,
  type RoastContext,
} from '../services/greenBeanContextService'

const store = useAppStore()
const router = useRouter()
const data = ref<DashboardYearData | null>(null)
const loading = ref(false)
const error = ref(false)
const errorMsg = ref('')

// Green-bean context for resolving bean names (demo-aware)
const roastContext = ref<RoastContext>({ greenBeans: [], purchaseBatches: [], roastingBatches: [] })

const expandedBeans = ref<Set<string>>(new Set())

const monthlyChartRef = ref<HTMLDivElement>()
const varietyChartRef = ref<HTMLDivElement>()
const regionChartRef = ref<HTMLDivElement>()
let monthlyChart: echarts.ECharts | null = null
let varietyChart: echarts.ECharts | null = null
let regionChart: echarts.ECharts | null = null

// 确认完成弹窗
const confirmBatch = ref<RoastingBatch | null>(null)
const confirmForm = ref({ beanWeightIn: 500, actualDate: new Date().toISOString().split('T')[0] })

// 按生豆档案（豆款）分组待烘列表
interface PendingGroup {
  beanId: string
  beanName: string
  variety: string
  process: string
  region: string
  batches: RoastingBatch[]
}

const pendingGrouped = computed<PendingGroup[]>(() => {
  if (!data.value) return []
  const map = new Map<string, PendingGroup>()
  for (const b of data.value.pendingBatches) {
    const gb = getGreenBeanByBatch(roastContext.value, b)
    if (!gb) continue
    if (!map.has(gb.id)) {
      map.set(gb.id, {
        beanId: gb.id,
        beanName: gb.name,
        variety: gb.variety,
        process: gb.process,
        region: gb.region,
        batches: [],
      })
    }
    map.get(gb.id)!.batches.push(b)
  }
  return [...map.values()]
})

const totalPendingCount = computed(() => data.value?.pendingBatches.length || 0)

function formatWeight(g: number) {
  if (g >= 1000) return (g / 1000).toFixed(1) + 'kg'
  return g + 'g'
}

function getBeanName(purchaseBatchId: string) {
  const pb = roastContext.value.purchaseBatches.find(p => p.id === purchaseBatchId)
  if (!pb) return '-'
  return roastContext.value.greenBeans.find(g => g.id === pb.greenBeanId)?.name || pb.greenBeanId
}

function getBeanVariety(purchaseBatchId: string) {
  const pb = roastContext.value.purchaseBatches.find(p => p.id === purchaseBatchId)
  if (!pb) return '-'
  return roastContext.value.greenBeans.find(g => g.id === pb.greenBeanId)?.variety || '-'
}

function getPurchaseLabel(id: string) {
  return id.replace('pb_', 'PB-')
}

function goToCurve(batchId: string) {
  router.push(`/curve/${batchId}`)
}

function toggleBean(beanId: string) {
  const s = new Set(expandedBeans.value)
  if (s.has(beanId)) s.delete(beanId)
  else s.add(beanId)
  expandedBeans.value = s
}

function onConfirmComplete(batch: RoastingBatch) {
  confirmBatch.value = batch
  confirmForm.value = {
    beanWeightIn: batch.beanWeightIn,
    actualDate: new Date().toISOString().split('T')[0],
  }
}

async function doComplete() {
  if (!confirmBatch.value) return
  await completeRoastingBatch(
    confirmBatch.value.id,
    confirmForm.value.beanWeightIn,
    confirmForm.value.actualDate,
  )
  invalidateRoastContext()
  confirmBatch.value = null
  await fetchData()
}

async function fetchData() {
  loading.value = true
  error.value = false
  errorMsg.value = ''
  try {
    const [dash, ctx] = await Promise.all([
      fetchDashboard(store.currentYear),
      fetchRoastContext(),
    ])
    data.value = dash
    roastContext.value = ctx
    if (data.value && pendingGrouped.value.length > 0) {
      expandedBeans.value = new Set([pendingGrouped.value[0].beanId])
    }
    await nextTick()
    renderCharts()
  } catch (e) {
    error.value = true
    errorMsg.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  if (!data.value) return

  if (monthlyChartRef.value) {
    if (!monthlyChart) monthlyChart = echarts.init(monthlyChartRef.value)
    monthlyChart.setOption({
      grid: { top: 8, right: 8, bottom: 20, left: 40 },
      xAxis: {
        type: 'category',
        data: data.value.monthlyRoasts.map(m => m.month + '月'),
        axisLabel: { fontSize: 10, color: '#5d6880' },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: { fontSize: 10, color: '#5d6880' },
        splitLine: { lineStyle: { color: '#e5e9f2' } },
      },
      series: [{
        type: 'bar',
        data: data.value.monthlyRoasts.map(m => m.count),
        itemStyle: { color: '#2f6bff', borderRadius: [3, 3, 0, 0] },
        barWidth: 16,
      }],
    })
  }

  if (varietyChartRef.value) {
    if (!varietyChart) varietyChart = echarts.init(varietyChartRef.value)
    varietyChart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['50%', '80%'],
        center: ['50%', '50%'],
        label: { fontSize: 10, color: '#5d6880' },
        itemStyle: { borderRadius: 3, borderColor: '#fff', borderWidth: 2 },
        data: data.value.varietyDistribution.map(v => ({ name: v.name, value: v.count })),
      }],
    })
  }

  if (regionChartRef.value) {
    if (!regionChart) regionChart = echarts.init(regionChartRef.value)
    regionChart.setOption({
      grid: { top: 8, right: 8, bottom: 20, left: 50 },
      xAxis: {
        type: 'value',
        axisLabel: { fontSize: 10, color: '#5d6880' },
        splitLine: { lineStyle: { color: '#e5e9f2' } },
      },
      yAxis: {
        type: 'category',
        data: data.value.regionDistribution.map(r => r.name).reverse(),
        axisLabel: { fontSize: 10, color: '#5d6880' },
        axisTick: { show: false },
      },
      series: [{
        type: 'bar',
        data: data.value.regionDistribution.map(r => r.count).reverse(),
        itemStyle: { color: '#168477', borderRadius: [0, 3, 3, 0] },
        barWidth: 14,
      }],
    })
  }
}

function prevYear() { store.setYear(store.currentYear - 1) }
function nextYear() { store.setYear(store.currentYear + 1) }

watch(() => store.currentYear, () => { fetchData() })
onMounted(fetchData)
</script>

<style scoped>
.dashboard { max-width: 1320px; }

/* 页面标题 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-6);
}

.page-heading { font-size: var(--fs-xl); font-weight: 600; }

.year-switcher {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.year-btn {
  width: 28px; height: 28px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--surface);
  cursor: pointer;
  font-size: 16px; line-height: 1;
  color: var(--text-secondary);
}
.year-btn:hover { background: var(--app-bg); }

.year-label {
  font-size: var(--fs-md); font-weight: 600;
  font-family: var(--font-mono); min-width: 52px; text-align: center;
}

/* KPI — 横向摘要条 */
.kpi-bar {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-4) var(--sp-6);
  display: flex;
  align-items: center;
  margin-bottom: var(--sp-6);
}

.kpi-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-label {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}

.kpi-value {
  font-size: var(--fs-2xl);
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--text-primary);
}

.kpi-divider {
  width: 1px;
  height: 40px;
  background: var(--border-default);
  margin: 0 var(--sp-6);
}

/* Charts */
.charts-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: var(--sp-4);
  margin-bottom: var(--sp-6);
}

.chart-block {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-4);
}

.chart-title { font-size: var(--fs-sm); font-weight: 500; color: var(--text-secondary); margin-bottom: var(--sp-2); }
.chart-box { width: 100%; height: 200px; }

/* Sections */
.list-section { margin-bottom: var(--sp-6); }

.section-title {
  font-size: var(--fs-md); font-weight: 600;
  display: flex; align-items: center; gap: var(--sp-2);
  margin-bottom: var(--sp-3);
}

.badge {
  background: var(--primary-subtle); color: var(--primary);
  font-size: var(--fs-xs); padding: 0 6px;
  border-radius: 10px; font-weight: 500;
}

/* ---------- 待烘豆树 ---------- */
.pending-tree {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.tree-group {
  border-bottom: 1px solid var(--border-default);
}
.tree-group:last-child { border-bottom: none; }

.tree-row {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-2) var(--sp-4);
  font-size: var(--fs-sm);
  min-height: var(--table-row-height);
}

.tree-row-l1 {
  cursor: pointer;
}

.tree-row-l1:hover {
  background: var(--surface-selected);
}

.tree-row-l2 {
  background: var(--surface-subtle);
  border-top: 1px solid var(--border-default);
}

.tree-row-l2:hover {
  background: var(--surface-selected);
}

.tree-expand {
  width: 16px;
  font-size: 11px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.tree-expand-spacer {
  width: 28px;
  flex-shrink: 0;
}

.tree-bean-name {
  font-weight: 600;
  color: var(--text-primary);
  min-width: 140px;
}

.tree-bean-meta {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  flex: 1;
}

.tree-count {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  background: var(--app-bg);
  padding: 2px 8px;
  border-radius: 10px;
  flex-shrink: 0;
}

.tree-target {
  font-weight: 500;
  color: var(--primary);
  min-width: 150px;
}

.tree-date {
  color: var(--text-secondary);
  min-width: 100px;
}

.tree-weight {
  font-family: var(--font-mono);
  min-width: 70px;
}

.tree-pb {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  flex: 1;
}

.tree-check {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  cursor: pointer;
  flex-shrink: 0;
}

/* Table */
.data-table {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  border-collapse: collapse;
  font-size: var(--fs-sm);
}

.data-table th {
  background: var(--surface-subtle);
  padding: var(--sp-2) var(--sp-3);
  text-align: left;
  font-weight: 500;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-default);
}

.data-table td {
  padding: var(--sp-2) var(--sp-3);
  border-bottom: 1px solid var(--border-default);
  height: var(--table-row-height);
}

.data-table tr:last-child td { border-bottom: none; }
.clickable { cursor: pointer; }
.clickable:hover { background: var(--surface-selected); }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.15); z-index: 100;
  display: flex; align-items: center; justify-content: center;
}

.modal {
  width: 440px; max-width: 90vw;
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-overlay);
  overflow: hidden;
}

.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--sp-4) var(--sp-6);
  border-bottom: 1px solid var(--border-default);
}

.modal-header h3 { font-size: var(--fs-md); font-weight: 600; }

.modal-close {
  background: none; border: none;
  font-size: 18px; cursor: pointer;
  color: var(--text-tertiary);
}

.modal-body {
  padding: var(--sp-6);
  display: flex; flex-direction: column; gap: var(--sp-4);
}

.modal-footer {
  padding: var(--sp-4) var(--sp-6);
  border-top: 1px solid var(--border-default);
  display: flex; justify-content: flex-end; gap: var(--sp-2);
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.form-label {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  font-weight: 500;
}

.input {
  height: var(--input-height);
  padding: 0 var(--sp-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-family: var(--font-sans);
  background: var(--surface);
  color: var(--text-primary);
  outline: none;
}
.input:focus { border-color: var(--primary); }

/* Buttons */
.btn {
  padding: 0 var(--sp-4);
  height: var(--btn-height);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  font-family: var(--font-sans);
}

.btn-primary {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.btn-primary:hover { background: var(--primary-hover); }

.btn-secondary {
  background: var(--surface);
  color: var(--text-primary);
  border-color: var(--border-default);
}
.btn-secondary:hover { background: var(--app-bg); }

/* Status dot + text */
.status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.status-dot.success { background: var(--success); }
.status-dot.warning { background: var(--warning); }
</style>
