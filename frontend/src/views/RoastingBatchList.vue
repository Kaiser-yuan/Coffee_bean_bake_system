<template>
  <div class="roasting-page">
    <div class="page-header">
      <h2 class="page-heading">烘焙分析</h2>
      <div class="header-actions">
        <button class="btn btn-primary" @click="openCreateDialog">+ 新建待烘计划</button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-row">
        <input v-model="filters.greenBeanName" type="text" class="input search-input" placeholder="搜索生豆名称…" />
        <select v-model="filters.variety" class="select">
          <option value="">全部豆种</option>
          <option v-for="v in VARIETY_OPTIONS" :key="v" :value="v">{{ v }}</option>
        </select>
        <select v-model="filters.process" class="select">
          <option value="">全部处理法</option>
          <option v-for="p in BEAN_PROCESSES" :key="p" :value="p">{{ p }}</option>
        </select>
        <select v-model="filters.status" class="select">
          <option value="">全部状态</option>
          <option value="planned">待烘</option>
          <option value="completed">已完成</option>
        </select>
        <button class="btn btn-secondary btn-sm" @click="toggleMoreFilters">
          更多筛选
        </button>
        <button class="btn btn-text btn-sm" @click="clearFilters">重置</button>
      </div>
      <div v-if="showMoreFilters" class="filter-row filter-row-extra">
        <select v-model="filters.region" class="select">
          <option value="">全部产区</option>
          <option v-for="r in REGION_OPTIONS" :key="r" :value="r">{{ r }}</option>
        </select>
        <select v-model="filters.hasCurve" class="select select-sm">
          <option value="">曲线不限</option>
          <option value="true">有曲线</option>
          <option value="false">无曲线</option>
        </select>
      </div>
    </div>

    <!-- 浮动批量操作栏 -->
    <div v-if="store.compareSelection.size >= 2" class="batch-action-bar">
      <span class="text-sm">
        已选 <strong>{{ store.compareSelection.size }}</strong> 个批次
      </span>
      <button
        v-if="store.canCompare"
        class="btn btn-accent btn-sm"
        @click="goToCompare"
      >
        对比曲线
      </button>
      <button class="btn btn-text btn-sm" @click="store.clearCompareSelection()">取消选择</button>
    </div>

    <LoadingState v-if="loading" text="加载批次数据…" />
    <ErrorState v-else-if="error" :retry="true" @retry="fetchBatches" />

    <!-- 批次表格 -->
    <template v-else>
      <table class="batch-table" v-if="filteredBatches.length">
        <thead>
          <tr>
            <th class="col-check"></th>
            <th>烘焙时间</th>
            <th>生豆名称</th>
            <th class="num">投豆量</th>
            <th class="num">失重率</th>
            <th class="num">总时长</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="b in filteredBatches"
            :key="b.id"
            class="batch-row"
            @click="goToCurve(b.id)"
          >
            <td class="col-check" @click.stop>
              <input
                type="checkbox"
                :disabled="b.curveStatus !== 'parsed'"
                :checked="store.compareSelection.has(b.id)"
                @change="store.toggleCompareSelection(b.id)"
                :title="b.curveStatus !== 'parsed' ? '无曲线不可对比' : '选择对比'"
              />
            </td>
            <td>
              <span class="color-dot" :style="{ background: b.colorTag }"></span>
              <span class="num">{{ b.actualDate || b.plannedDate }}</span>
            </td>
            <td>
              <div class="bean-cell">
                <span class="bean-name">{{ getBeanNameForBatch(b.id) }}</span>
                <span class="bean-meta">{{ getBeanMeta(b.id) }}</span>
              </div>
            </td>
            <td class="num">{{ b.beanWeightIn }}g</td>
            <td class="num">{{ b.weightLossRate ? b.weightLossRate.toFixed(1) + '%' : '-' }}</td>
            <td class="num">{{ b.totalTime ? formatTime(b.totalTime) : '-' }}</td>
            <td @click.stop>
              <div class="status-dots">
                <span class="status-dot" :class="b.curveStatus === 'parsed' ? 'success' : 'neutral'" title="曲线状态">C</span>
                <span class="status-dot" :class="b.evaluationStatus === 'open' ? 'info' : b.evaluationStatus === 'closed' ? 'neutral' : 'neutral'" title="评价状态">E</span>
                <span class="status-dot" :class="b.reviewStatus === 'done' ? 'success' : b.reviewStatus === 'draft' ? 'warning' : 'neutral'" title="复盘状态">R</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <EmptyState v-else icon="🔥" title="未找到匹配批次" />
      <div class="table-footer" v-if="filteredBatches.length">
        <span class="text-sm text-tertiary">共 {{ filteredBatches.length }} 条</span>
      </div>
    </template>

    <!-- 创建待烘计划弹窗 -->
    <div v-if="createOpen" class="modal-overlay" @click.self="createOpen = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新建待烘计划</h3>
          <button class="modal-close" @click="createOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <label class="form-label">生豆</label>
            <select v-model="createForm.greenBeanId" class="select">
              <option v-for="b in mockGreenBeans" :key="b.id" :value="b.id">{{ b.name }}</option>
            </select>
          </div>
          <div class="form-row">
            <label class="form-label">采购批次</label>
            <select v-model="createForm.purchaseBatchId" class="select">
              <option v-for="p in availablePurchaseBatches" :key="p.id" :value="p.id">
                PB-{{ p.id.replace('pb_', '') }} ({{ formatWeight(p.remainingStock) }})
              </option>
            </select>
          </div>
          <div class="form-row">
            <label class="form-label">计划日期</label>
            <input v-model="createForm.plannedDate" type="date" class="input" />
          </div>
          <div class="form-row">
            <label class="form-label">投豆量 (g)</label>
            <input v-model.number="createForm.beanWeightIn" type="number" class="input" />
          </div>
          <div class="form-row">
            <label class="form-label">烘焙目标</label>
            <input v-model="createForm.targetDescription" type="text" class="input" placeholder="例如：突出花香、均衡发展" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="createOpen = false">取消</button>
          <button class="btn btn-primary" @click="onCreate">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRoastingStore } from '../stores/roasting'
import { mockGreenBeans, mockPurchaseBatches, apiCreateRoastingBatch, getGreenBeanByBatch } from '../mock'
import {
  BEAN_PROCESSES, VARIETY_OPTIONS, REGION_OPTIONS,
  BATCH_STATUS_LABELS,
} from '../types'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import EmptyState from '../components/common/EmptyState.vue'

const router = useRouter()
const store = useRoastingStore()
const loading = ref(false)
const error = ref(false)
const createOpen = ref(false)
const showMoreFilters = ref(false)

const filters = ref({
  greenBeanName: '',
  variety: '',
  process: '',
  region: '',
  status: '' as string,
  hasCurve: '' as string,
})

const createForm = ref({
  greenBeanId: mockGreenBeans[0]?.id || '',
  purchaseBatchId: '',
  plannedDate: new Date().toISOString().split('T')[0],
  beanWeightIn: 500,
  targetDescription: '',
})

const availablePurchaseBatches = computed(() => {
  return mockPurchaseBatches.filter(p => p.greenBeanId === createForm.value.greenBeanId)
})

function getBeanNameForBatch(batchId: string) {
  const b = store.batches.find(b => b.id === batchId)
  if (!b) return '-'
  return getGreenBeanByBatch(b)?.name || '-'
}

function getBeanMeta(batchId: string) {
  const b = store.batches.find(b => b.id === batchId)
  if (!b) return ''
  const gb = b ? getGreenBeanByBatch(b) : undefined
  return gb ? `${gb.variety} · ${gb.process} · ${gb.region}` : ''
}

const filteredBatches = computed(() => {
  let list = [...store.batches]
  const f = filters.value
  if (f.greenBeanName) {
    const q = f.greenBeanName.toLowerCase()
    list = list.filter(b => {
      const gb = getGreenBeanByBatch(b)
      return gb?.name.toLowerCase().includes(q)
    })
  }
  if (f.variety) list = list.filter(b => {
    const gb = getGreenBeanByBatch(b)
    return gb?.variety === f.variety
  })
  if (f.process) list = list.filter(b => {
    const gb = getGreenBeanByBatch(b)
    return gb?.process === f.process
  })
  if (f.region) list = list.filter(b => {
    const gb = getGreenBeanByBatch(b)
    return gb?.region === f.region
  })
  if (f.status) list = list.filter(b => b.status === f.status)
  if (f.hasCurve === 'true') list = list.filter(b => b.curveStatus === 'parsed')
  if (f.hasCurve === 'false') list = list.filter(b => b.curveStatus === 'none')
  return list
})

function toggleMoreFilters() { showMoreFilters.value = !showMoreFilters.value }

function formatWeight(g: number) {
  return g >= 1000 ? (g / 1000).toFixed(1) + 'kg' : g + 'g'
}

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${sec.toString().padStart(2, '0')}`
}

function goToCurve(batchId: string) { router.push(`/curve/${batchId}`) }

function goToCompare() {
  const ids = [...store.compareSelection].join(',')
  router.push(`/curve/compare/${ids}`)
}

function clearFilters() {
  filters.value = { greenBeanName: '', variety: '', process: '', region: '', status: '', hasCurve: '' }
  showMoreFilters.value = false
}

function openCreateDialog() {
  createForm.value.purchaseBatchId = availablePurchaseBatches.value[0]?.id || ''
  createOpen.value = true
}

async function onCreate() {
  await apiCreateRoastingBatch({
    purchaseBatchId: createForm.value.purchaseBatchId,
    plannedDate: createForm.value.plannedDate,
    beanWeightIn: createForm.value.beanWeightIn,
    targetDescription: createForm.value.targetDescription,
  })
  createOpen.value = false
  await fetchBatches()
}

async function fetchBatches() {
  loading.value = true
  error.value = false
  try {
    await store.fetchBatches()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(fetchBatches)
</script>

<style scoped>
.roasting-page { max-width: 1500px; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-4);
}

.page-heading { font-size: var(--fs-xl); font-weight: 600; }

.header-actions {
  display: flex;
  gap: var(--sp-2);
}

/* Filter bar */
.filter-bar {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-3);
  margin-bottom: var(--sp-4);
}

.filter-row {
  display: flex;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.filter-row-extra {
  margin-top: var(--sp-2);
  padding-top: var(--sp-2);
  border-top: 1px solid var(--border-default);
}

.search-input { flex: 1; min-width: 180px; }

/* Floating batch action bar */
.batch-action-bar {
  background: var(--primary-subtle);
  border: 1px solid var(--primary);
  border-radius: var(--radius-md);
  padding: var(--sp-2) var(--sp-4);
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin-bottom: var(--sp-3);
}

/* Batch table */
.batch-table {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  border-collapse: collapse;
  font-size: var(--fs-sm);
}

.batch-table th {
  background: var(--surface-subtle);
  padding: var(--sp-2) var(--sp-3);
  text-align: left;
  font-weight: 500;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-default);
  white-space: nowrap;
}

.batch-table td {
  padding: var(--sp-2) var(--sp-3);
  border-bottom: 1px solid var(--border-default);
  height: var(--table-row-height);
}

.col-check { width: 36px; text-align: center; }

.batch-row { cursor: pointer; }
.batch-row:hover { background: var(--surface-selected); }

.color-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.bean-cell {
  display: flex;
  flex-direction: column;
}

.bean-name { font-weight: 500; }
.bean-meta { font-size: var(--fs-xs); color: var(--text-tertiary); }

/* Status dots group */
.status-dots {
  display: flex;
  gap: 4px;
}

.status-dots .status-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  color: #fff;
}

.status-dots .status-dot.success { background: var(--success); }
.status-dots .status-dot.warning { background: var(--warning); }
.status-dots .status-dot.neutral { background: var(--text-tertiary); }
.status-dots .status-dot.info { background: var(--primary); }

.table-footer {
  padding: var(--sp-2) var(--sp-3);
  color: var(--text-tertiary);
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

.btn-sm { height: 28px; padding: 0 var(--sp-3); font-size: var(--fs-sm); }

.btn-primary { background: var(--primary); color: #fff; border-color: var(--primary); }
.btn-primary:hover { background: var(--primary-hover); }
.btn-secondary { background: var(--surface); color: var(--text-primary); border-color: var(--border-default); }
.btn-secondary:hover { background: var(--app-bg); }
.btn-accent { background: var(--business-accent); color: #fff; border-color: var(--business-accent); }
.btn-accent:hover { opacity: 0.9; }
.btn-text { background: transparent; color: var(--text-secondary); border-color: transparent; }
.btn-text:hover { color: var(--text-primary); background: var(--app-bg); }

/* Form controls */
.input, .select {
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

.input:focus, .select:focus { border-color: var(--primary); }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.15); z-index: 100;
  display: flex; align-items: center; justify-content: center;
}

.modal {
  width: 500px; max-width: 90vw;
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

.modal-close { background: none; border: none; font-size: 18px; cursor: pointer; color: var(--text-tertiary); }

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
</style>
