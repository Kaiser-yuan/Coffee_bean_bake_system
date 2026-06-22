<template>
  <div class="green-beans-page">
    <div class="page-header">
      <h2 class="page-heading">生豆管理</h2>
      <button class="btn btn-primary" @click="openDrawer()">+ 录入生豆</button>
    </div>

    <!-- 搜索与筛选 -->
    <div class="filter-bar">
      <div class="filter-row">
        <input
          v-model="searchText"
          type="text"
          class="input search-input"
          placeholder="搜索生豆名称、品牌、产区…"
          @input="onSearch"
        />
        <select v-model="filters.variety" class="select" @change="onFilterChange">
          <option value="">全部豆种</option>
          <option v-for="v in VARIETY_OPTIONS" :key="v" :value="v">{{ v }}</option>
        </select>
        <select v-model="filters.process" class="select" @change="onFilterChange">
          <option value="">全部处理法</option>
          <option v-for="p in BEAN_PROCESSES" :key="p" :value="p">{{ p }}</option>
        </select>
        <select v-model="filters.region" class="select" @change="onFilterChange">
          <option value="">全部产区</option>
          <option v-for="r in REGION_OPTIONS" :key="r" :value="r">{{ r }}</option>
        </select>
      </div>
    </div>

    <LoadingState v-if="loading" text="加载生豆数据…" />
    <ErrorState v-else-if="error" :retry="true" @retry="fetchData" />

    <!-- 三级树状表格 -->
    <template v-else>
      <table class="tree-table" v-if="filteredBeans.length">
        <thead>
          <tr>
            <th class="col-name">生豆名称</th>
            <th>豆种</th>
            <th>处理法</th>
            <th>产区</th>
            <th>海拔</th>
            <th class="num col-stock">剩余库存</th>
            <th class="col-action"></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="bean in filteredBeans" :key="bean.id">
            <!-- Level 1: 生豆档案 -->
            <tr class="row-l1" @click="toggleExpand(bean.id)">
              <td>
                <span class="expand-icon">{{ expanded.has(bean.id) ? '▾' : '▸' }}</span>
                <strong>{{ bean.name }}</strong>
              </td>
              <td>{{ bean.variety }}</td>
              <td>{{ bean.process }}</td>
              <td>{{ bean.region }}</td>
              <td>{{ bean.elevation || '-' }}</td>
              <td class="num font-mono">
                <span
                  class="stock-indicator"
                  :class="getStockLevel(bean.id)"
                ></span>
                {{ formatWeight(getTotalStock(bean.id)) }}
              </td>
              <td></td>
            </tr>

            <!-- Level 2 & 3: 采购批次 + 烘焙批次 -->
            <template v-if="expanded.has(bean.id)">
              <template v-for="pb in getPurchaseBatches(bean.id)" :key="pb.id">
                <tr class="row-l2" @click="toggleExpand(pb.id)">
                  <td>
                    <span class="expand-spacer"></span>
                    <span class="expand-icon">{{ expanded.has(pb.id) ? '▾' : '▸' }}</span>
                    采购批次 {{ pb.id.replace('pb_', 'PB-') }}
                  </td>
                  <td>采购日期: {{ pb.purchaseDate }}</td>
                  <td>总量: {{ formatWeight(pb.totalWeight) }}</td>
                  <td>含水率: {{ pb.moistureContent ?? '-' }}%</td>
                  <td>{{ pb.supplier || '-' }}</td>
                  <td class="num font-mono">
                    <div class="stock-bar">
                      <div class="stock-bar-fill" :style="{ width: getStockPercent(pb) + '%', background: getStockBarColor(pb) }"></div>
                    </div>
                    {{ formatWeight(pb.remainingStock) }}
                  </td>
                  <td>
                    <button
                      class="btn btn-xs btn-secondary"
                      @click.stop="openRoastPlan(pb)"
                      title="创建待烘计划"
                    >
                      + 待烘计划
                    </button>
                    <button
                      v-if="!isDemoMode"
                      class="btn btn-xs btn-secondary"
                      @click.stop="openBulkCsv(pb)"
                      title="批量 CSV 生成烘焙批次"
                    >
                      批量 CSV
                    </button>
                  </td>
                </tr>

                <!-- Level 3: 烘焙批次 -->
                <template v-if="expanded.has(pb.id)">
                  <tr
                    v-for="rb in getRoastingBatches(bean.id, pb.id)"
                    :key="rb.id"
                    class="row-l3 clickable"
                    @click="goToCurve(rb.id)"
                  >
                    <td>
                      <span class="expand-spacer-double"></span>
                      烘焙 {{ rb.id.replace('rb_', 'RB-') }}
                    </td>
                    <td class="num">{{ rb.actualDate || rb.plannedDate }}</td>
                    <td class="num">{{ rb.beanWeightIn }}g / {{ rb.beanWeightOut ?? '-' }}g</td>
                    <td class="num">{{ rb.weightLossRate ? rb.weightLossRate.toFixed(1) + '%' : '-' }}</td>
                    <td>
                      <span class="status-dot" :class="rb.status === 'completed' ? 'success' : 'warning'"></span>
                      {{ BATCH_STATUS_LABELS[rb.status] }}
                      <span v-if="rb.targetDescription" class="roast-target text-xs text-tertiary ml-sm">
                        {{ rb.targetDescription }}
                      </span>
                    </td>
                    <td></td>
                  </tr>
                  <tr v-if="getRoastingBatches(bean.id, pb.id).length === 0" class="row-l3">
                    <td colspan="7">
                      <span class="expand-spacer-double"></span>
                      <span class="text-xs text-tertiary">暂无烘焙批次</span>
                    </td>
                  </tr>
                </template>
              </template>
            </template>
          </template>
        </tbody>
      </table>
      <EmptyState v-else icon="🫘" title="未找到匹配的生豆" />
    </template>

    <!-- 抽屉：录入生豆 -->
    <div v-if="drawerOpen" class="drawer-overlay" @click.self="closeDrawer">
      <div class="drawer">
        <div class="drawer-header">
          <h3>{{ editMode ? '新增采购批次' : '录入生豆' }}</h3>
          <button class="drawer-close" @click="closeDrawer">✕</button>
        </div>
        <div class="drawer-body">
          <!-- 搜索已有生豆 -->
          <label class="form-label">生豆名称</label>
          <input
            v-model="form.name"
            type="text"
            class="input"
            placeholder="输入名称搜索已有档案…"
            @input="onBeanSearch"
          />
          <div v-if="beanSuggestions.length" class="suggestions">
            <div
              v-for="s in beanSuggestions"
              :key="s.id"
              class="suggestion-item"
              @click="selectExistingBean(s)"
            >
              <span class="sug-name">{{ s.name }}</span>
              <span class="sug-meta">{{ s.brand || '-' }} · {{ s.season || '-' }} · {{ s.process }} · {{ s.region }}</span>
            </div>
          </div>

          <!-- 新豆款字段 -->
          <template v-if="!editMode">
            <div class="form-row">
              <label class="form-label">豆种</label>
              <select v-model="form.variety" class="select">
                <option v-for="v in VARIETY_OPTIONS" :key="v" :value="v">{{ v }}</option>
              </select>
            </div>
            <div class="form-row">
              <label class="form-label">处理法</label>
              <select v-model="form.process" class="select">
                <option v-for="p in BEAN_PROCESSES" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div class="form-row">
              <label class="form-label">产区</label>
              <select v-model="form.region" class="select">
                <option v-for="r in REGION_OPTIONS" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>
            <div class="form-row">
              <label class="form-label">品牌</label>
              <input v-model="form.brand" type="text" class="input" placeholder="例如：A品牌" />
            </div>
            <div class="form-row">
              <label class="form-label">产季</label>
              <input v-model="form.season" type="text" class="input" placeholder="例如：2025 产季" />
            </div>
            <div class="form-row">
              <label class="form-label">农场</label>
              <input v-model="form.farm" type="text" class="input" />
            </div>
            <div class="form-row">
              <label class="form-label">海拔</label>
              <input v-model="form.elevation" type="text" class="input" placeholder="例如 1800m" />
            </div>
            <div class="form-row">
              <label class="form-label">豆商风味描述</label>
              <input v-model="form.vendorFlavorDescription" type="text" class="input" placeholder="例如：花香、柑橘调性" />
            </div>
          </template>

          <!-- 采购批次字段（始终显示） -->
          <div class="form-divider">采购信息</div>
          <div class="form-row">
            <label class="form-label">采购日期</label>
            <input v-model="form.purchaseDate" type="date" class="input" />
          </div>
          <div class="form-row">
            <label class="form-label">采购总量 (g)</label>
            <input v-model.number="form.totalWeight" type="number" class="input" />
          </div>
          <div class="form-row">
            <label class="form-label">采购单价 (元/kg)</label>
            <input v-model.number="form.pricePerKg" type="number" class="input" step="0.01" placeholder="填写单价后自动计算总价" />
          </div>
          <div class="form-row">
            <label class="form-label">含水率 (%)</label>
            <input v-model.number="form.moistureContent" type="number" class="input" step="0.1" />
          </div>
          <div class="form-row">
            <label class="form-label">供应商</label>
            <input v-model="form.supplier" type="text" class="input" />
          </div>
          <div class="form-row">
            <label class="form-label">批次号</label>
            <input v-model="form.lotNumber" type="text" class="input" />
          </div>
        </div>
        <div class="drawer-footer">
          <button class="btn btn-secondary" @click="closeDrawer">取消</button>
          <button class="btn btn-primary" @click="onSubmit">保存</button>
        </div>
      </div>
    </div>

    <!-- 创建待烘计划弹窗 -->
    <div v-if="roastPlanOpen" class="modal-overlay" @click.self="roastPlanOpen = false">
      <div class="modal">
        <div class="modal-header">
          <h3>创建待烘计划</h3>
          <button class="modal-close" @click="roastPlanOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="plan-context">
            <div class="context-item">
              <span class="context-label">生豆</span>
              <span class="context-value">{{ selectedBeanForPlan?.name }}</span>
            </div>
            <div class="context-item">
              <span class="context-label">采购批次</span>
              <span class="context-value">PB-{{ selectedPbForPlan?.id?.replace('pb_', '') }}</span>
            </div>
            <div class="context-item">
              <span class="context-label">剩余库存</span>
              <span class="context-value font-mono">{{ selectedPbForPlan ? formatWeight(selectedPbForPlan.remainingStock) : '-' }}</span>
            </div>
          </div>

          <div class="form-divider"></div>

          <div class="form-row">
            <label class="form-label">计划烘焙日期</label>
            <input v-model="roastForm.plannedDate" type="date" class="input" />
          </div>
          <div class="form-row">
            <label class="form-label">投豆量 (g)</label>
            <input v-model.number="roastForm.beanWeightIn" type="number" class="input" />
          </div>
          <div class="form-row">
            <label class="form-label">烘焙目标</label>
            <input
              v-model="roastForm.targetDescription"
              type="text"
              class="input"
              placeholder="例如：突出花香、降低苦度、均衡发展…"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="roastPlanOpen = false">取消</button>
          <button class="btn btn-primary" @click="onCreateRoastPlan">创建</button>
        </div>
      </div>
    </div>

    <!-- 批量 CSV 生成烘焙批次 -->
    <BulkCsvImportDialog
      v-if="!isDemoMode"
      :open="bulkCsvOpen"
      :purchase-batch-id="bulkCsvPurchaseBatchId"
      @committed="onBulkCsvCommitted"
      @close="closeBulkCsv"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { isDemoMode, ApiError } from '../api/http'
import * as greenBeanApi from '../api/greenBeans'
import {
  addPurchaseBatch,
  createGreenBeanWithFirstPurchase,
} from '../services/greenBeanService'
import { createRoastingBatch } from '../services/roastingBatchService'
import { fetchRoastContext, invalidateRoastContext } from '../services/greenBeanContextService'
import { toGreenBeanTree, toGreenBeanSuggestion } from '../adapters/greenBean'
import {
  BEAN_PROCESSES, VARIETY_OPTIONS, REGION_OPTIONS,
  BATCH_STATUS_LABELS,
} from '../types'
import type { GreenBean, PurchaseBatch, BeanProcess } from '../types'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import EmptyState from '../components/common/EmptyState.vue'
import BulkCsvImportDialog from '../components/roasting/BulkCsvImportDialog.vue'

const router = useRouter()
const loading = ref(false)
const error = ref(false)
const searchText = ref('')
const filters = ref({ variety: '', process: '', region: '' })
const expanded = ref(new Set<string>())
const drawerOpen = ref(false)
const editMode = ref(false)
const selectedBeanId = ref('')

// 批量 CSV 生成烘焙批次弹窗
const bulkCsvOpen = ref(false)
const bulkCsvPurchaseBatchId = ref('')

function openBulkCsv(pb: PurchaseBatch) {
  bulkCsvPurchaseBatchId.value = pb.id
  bulkCsvOpen.value = true
}
function closeBulkCsv() {
  bulkCsvOpen.value = false
}
async function onBulkCsvCommitted() {
  invalidateRoastContext()
  await fetchData()
}

// Reactive data arrays (populated from API or mock)
const greenBeans = ref<GreenBean[]>([])
const purchaseBatches = ref<PurchaseBatch[]>([])
const roastingBatches = ref<import('../types').RoastingBatch[]>([])

// 录入表单
const form = ref({
  name: '',
  variety: '铁皮卡',
  process: '水洗' as BeanProcess,
  region: '埃塞俄比亚',
  brand: '',
  season: '',
  farm: '',
  elevation: '',
  vendorFlavorDescription: '',
  purchaseDate: new Date().toISOString().split('T')[0],
  totalWeight: 5000,
  pricePerKg: undefined as number | undefined,
  moistureContent: undefined as number | undefined,
  supplier: '',
  lotNumber: '',
})
const beanSuggestions = ref<GreenBean[]>([])

// 待烘计划弹窗
const roastPlanOpen = ref(false)
const selectedPbForPlan = ref<PurchaseBatch | null>(null)
const selectedBeanForPlan = ref<GreenBean | null>(null)
const roastForm = ref({
  plannedDate: new Date().toISOString().split('T')[0],
  beanWeightIn: 500,
  targetDescription: '',
})

const filteredBeans = computed(() => {
  let list = [...greenBeans.value]
  if (!isDemoMode) {
    // Real mode: filtering is done server-side via fetchData params
    return list
  }
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(b =>
      b.name.toLowerCase().includes(q) ||
      (b.brand && b.brand.toLowerCase().includes(q)) ||
      b.region.toLowerCase().includes(q) ||
      b.variety.toLowerCase().includes(q)
    )
  }
  if (filters.value.variety) list = list.filter(b => b.variety === filters.value.variety)
  if (filters.value.process) list = list.filter(b => b.process === filters.value.process)
  if (filters.value.region) list = list.filter(b => b.region === filters.value.region)
  return list
})

function toggleExpand(id: string) {
  const s = new Set(expanded.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  expanded.value = s
}

function getPurchaseBatches(beanId: string) {
  return purchaseBatches.value.filter(p => p.greenBeanId === beanId)
}

function getRoastingBatches(beanId: string, pbId: string) {
  return roastingBatches.value.filter(b => {
    const pb = purchaseBatches.value.find(p => p.id === b.purchaseBatchId)
    return pb?.greenBeanId === beanId && b.purchaseBatchId === pbId
  })
}

function getTotalStock(beanId: string) {
  return getPurchaseBatches(beanId).reduce((s, p) => s + p.remainingStock, 0)
}

/** 库存状态按比例判断 */
function getStockLevel(beanId: string) {
  const batches = getPurchaseBatches(beanId)
  if (batches.length === 0) return 'depleted'
  const totalRemaining = batches.reduce((s, p) => s + p.remainingStock, 0)
  const totalPurchased = batches.reduce((s, p) => s + p.totalWeight, 0)
  if (totalPurchased === 0) return 'depleted'
  const ratio = totalRemaining / totalPurchased
  if (ratio <= 0.05) return 'depleted'
  if (ratio < 0.2) return 'low'
  return 'normal'
}

function getStockPercent(pb: PurchaseBatch) {
  if (pb.totalWeight === 0) return 0
  return Math.min(100, Math.max(0, (pb.remainingStock / pb.totalWeight) * 100))
}

function getStockBarColor(pb: PurchaseBatch) {
  const pct = getStockPercent(pb)
  if (pct <= 5) return 'var(--danger)'
  if (pct < 20) return 'var(--warning)'
  return 'var(--success)'
}

function formatWeight(g: number) {
  if (g >= 1000) return (g / 1000).toFixed(1) + 'kg'
  return g + 'g'
}

function goToCurve(batchId: string) {
  router.push(`/curve/${batchId}`)
}

// ---------- 录入抽屉 ----------
function openDrawer() {
  editMode.value = false
  selectedBeanId.value = ''
  resetForm()
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
}

function resetForm() {
  form.value = {
    name: '',
    variety: '铁皮卡',
    process: '水洗' as BeanProcess,
    region: '埃塞俄比亚',
    brand: '',
    season: '',
    farm: '',
    elevation: '',
    vendorFlavorDescription: '',
    purchaseDate: new Date().toISOString().split('T')[0],
    totalWeight: 5000,
    pricePerKg: undefined,
    moistureContent: undefined,
    supplier: '',
    lotNumber: '',
  }
  beanSuggestions.value = []
}

async function onBeanSearch() {
  if (!form.value.name.trim()) {
    beanSuggestions.value = []
    return
  }

  if (isDemoMode) {
    const ctx = await fetchRoastContext(true)
    const q = form.value.name.toLowerCase()
    beanSuggestions.value = ctx.greenBeans.filter(b =>
      b.name.toLowerCase().includes(q)
    ).slice(0, 5)
    return
  }

  try {
    const matches = await greenBeanApi.matchGreenBeans(form.value.name)
    beanSuggestions.value = matches.map(toGreenBeanSuggestion)
  } catch {
    // Silently fail for suggestions
    beanSuggestions.value = []
  }
}

function selectExistingBean(bean: GreenBean) {
  editMode.value = true
  selectedBeanId.value = bean.id
  form.value.name = bean.name
  form.value.variety = bean.variety
  form.value.process = bean.process
  form.value.region = bean.region
  beanSuggestions.value = []
}

async function onSubmit() {
  // Step 1: Save
  try {
    if (editMode.value) {
      await addPurchaseBatch(selectedBeanId.value, form.value)
    } else {
      await createGreenBeanWithFirstPurchase(form.value)
    }
  } catch (err) {
    alert(err instanceof ApiError ? err.message : '保存失败')
    return
  }

  // Step 2: Close drawer (save succeeded)
  invalidateRoastContext()
  closeDrawer()

  // Step 3: Refresh list (may fail separately from save)
  try {
    await fetchData()
  } catch {
    alert('保存已成功，但刷新列表失败。请手动刷新页面或清空筛选后重试。')
  }
}

// ---------- 待烘计划弹窗 ----------
function openRoastPlan(pb: PurchaseBatch) {
  selectedPbForPlan.value = pb
  selectedBeanForPlan.value = greenBeans.value.find(g => g.id === pb.greenBeanId) || null
  roastForm.value = {
    plannedDate: new Date().toISOString().split('T')[0],
    beanWeightIn: 500,
    targetDescription: '',
  }
  roastPlanOpen.value = true
}

async function onCreateRoastPlan() {
  if (!selectedPbForPlan.value || !selectedBeanForPlan.value) return

  // Validation
  if (roastForm.value.beanWeightIn <= 0) {
    alert('投豆量必须大于零')
    return
  }
  if (!roastForm.value.plannedDate) {
    alert('计划日期不能为空')
    return
  }
  if (roastForm.value.beanWeightIn > selectedPbForPlan.value.remainingStock) {
    alert(`投豆量 (${roastForm.value.beanWeightIn}g) 超过采购批次可用库存 (${selectedPbForPlan.value.remainingStock}g)`)
    return
  }

  try {
    await createRoastingBatch({
      purchaseBatchId: selectedPbForPlan.value.id,
      plannedDate: roastForm.value.plannedDate,
      beanWeightIn: roastForm.value.beanWeightIn,
      targetDescription: roastForm.value.targetDescription,
    })
    invalidateRoastContext()
    await fetchData()
    roastPlanOpen.value = false
  } catch (err) {
    alert(err instanceof ApiError ? err.message : '创建失败')
  }
}

async function onSearch() {
  if (isDemoMode) return
  await fetchData()
}

async function onFilterChange() {
  if (isDemoMode) return
  await fetchData()
}

async function fetchData() {
  loading.value = true
  error.value = false
  try {
    if (isDemoMode) {
      const ctx = await fetchRoastContext(true)
      greenBeans.value = [...ctx.greenBeans]
      purchaseBatches.value = [...ctx.purchaseBatches]
      roastingBatches.value = [...ctx.roastingBatches]
      return
    }

    const tree = await greenBeanApi.getGreenBeanTree({
      search: searchText.value || undefined,
      variety: filters.value.variety || undefined,
      process: filters.value.process || undefined,
      region: filters.value.region || undefined,
    })

    const mapped = toGreenBeanTree(tree)
    greenBeans.value = mapped.greenBeans
    purchaseBatches.value = mapped.purchaseBatches
    roastingBatches.value = mapped.roastingBatches
  } catch (err) {
    console.error('Failed to fetch green bean tree:', err)
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.green-beans-page { max-width: 1500px; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-4);
}

.page-heading { font-size: var(--fs-xl); font-weight: 600; }

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
}

.search-input { flex: 1; min-width: 200px; }

/* Tree table */
.tree-table {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  border-collapse: collapse;
  font-size: var(--fs-sm);
}

.tree-table th {
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

.tree-table td {
  padding: var(--sp-2) var(--sp-3);
  border-bottom: 1px solid var(--border-default);
  height: var(--table-row-height);
}

.col-name { width: 300px; }
.col-stock { width: 170px; }
.col-action { width: 100px; }

.row-l1 { cursor: pointer; }
.row-l1:hover { background: var(--surface-selected); }
.row-l2 { cursor: pointer; background: var(--surface-subtle); }
.row-l2:hover { background: var(--surface-selected); }
.row-l3 { cursor: pointer; background: #fafbfd; }
.row-l3:hover { background: var(--surface-selected); }

.expand-icon {
  display: inline-block;
  width: 16px;
  font-size: 11px;
  color: var(--text-tertiary);
}

.expand-spacer { display: inline-block; width: 20px; }
.expand-spacer-double { display: inline-block; width: 36px; }

.roast-target { margin-left: var(--sp-2); opacity: 0.7; }
.ml-sm { margin-left: var(--sp-2); }

/* Stock indicator */
.stock-indicator {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.stock-indicator.normal { background: var(--success); }
.stock-indicator.low { background: var(--warning); }
.stock-indicator.depleted { background: var(--danger); }

.stock-bar {
  display: inline-block;
  width: 40px;
  height: 4px;
  background: var(--border-default);
  border-radius: 2px;
  margin-right: 8px;
  vertical-align: middle;
  overflow: hidden;
}

.stock-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

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

.btn-xs {
  padding: 0 var(--sp-2);
  height: 28px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-xs);
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  white-space: nowrap;
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
  min-width: 120px;
}

.input:focus, .select:focus { border-color: var(--primary); }

/* Drawer */
.drawer-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.2); z-index: 100;
  display: flex; justify-content: flex-end;
}

.drawer {
  width: 560px; max-width: 90vw;
  background: var(--surface);
  height: 100%;
  display: flex; flex-direction: column;
  box-shadow: var(--shadow-overlay);
}

.drawer-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--sp-4) var(--sp-6);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.drawer-header h3 { font-size: var(--fs-md); font-weight: 600; }

.drawer-close { background: none; border: none; font-size: 18px; cursor: pointer; color: var(--text-tertiary); }

.drawer-body {
  flex: 1; overflow-y: auto;
  padding: var(--sp-6);
  display: flex; flex-direction: column; gap: var(--sp-3);
}

.drawer-footer {
  display: flex; justify-content: flex-end; gap: var(--sp-2);
  padding: var(--sp-4) var(--sp-6);
  border-top: 1px solid var(--border-default);
  flex-shrink: 0;
}

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

/* Plan context */
.plan-context {
  background: var(--app-bg);
  border-radius: var(--radius-md);
  padding: var(--sp-3);
  display: flex; flex-direction: column; gap: var(--sp-2);
}

.context-item {
  display: flex; gap: var(--sp-2);
  font-size: var(--fs-sm);
}

.context-label { color: var(--text-tertiary); min-width: 64px; }
.context-value { font-weight: 500; }

/* Form */
.form-label {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  font-weight: 500;
}

.form-divider {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-primary);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--border-default);
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

/* Suggestions */
.suggestions {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  max-height: 160px;
  overflow-y: auto;
}

.suggestion-item {
  padding: var(--sp-2) var(--sp-3);
  cursor: pointer;
  font-size: var(--fs-sm);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.suggestion-item:last-child { border-bottom: none; }
.suggestion-item:hover { background: var(--surface-selected); }

.sug-name { font-weight: 500; }
.sug-meta { font-size: var(--fs-xs); color: var(--text-tertiary); }
</style>
