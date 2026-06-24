<template>
  <div class="backfill-page">
    <header class="page-header">
      <h1>历史数据补录</h1>
      <p class="subtitle">将旧的烘焙 CSV 归档入库。默认不影响当前库存；如需计入库存请单独勾选。</p>
    </header>

    <div v-if="isDemoMode" class="notice">
      历史补录需要连接真实后端。请在 <code>.env.local</code> 中设置 <code>VITE_DEMO_MODE=false</code> 后使用。
    </div>

    <template v-else>
      <!-- Step 0: 新建历史归档采购 -->
      <section class="card" :class="{ 'card-collapsed': !showNewArchive }">
        <h2 class="card-title" style="cursor: pointer" @click="showNewArchive = !showNewArchive">
          {{ showNewArchive ? '▾' : '▸' }} 新建历史归档采购
        </h2>
        <p class="card-hint">选择已有生豆并输入原采购重量、期初库存等信息，创建一个仅归档的采购批次。</p>
        <template v-if="showNewArchive">
          <div class="archive-form">
            <div class="form-row">
              <label class="field flex-1">
                <span>生豆</span>
                <select v-model="archiveForm.greenBeanId" class="input">
                  <option value="">— 请选择 —</option>
                  <option v-for="gb in greenBeanOptions" :key="gb.id" :value="gb.id">{{ gb.label }}</option>
                </select>
              </label>
              <label class="field" style="max-width: 180px">
                <span>采购日期</span>
                <input v-model="archiveForm.purchaseDate" type="date" class="input" />
              </label>
            </div>
            <div class="form-row">
              <label class="field" style="max-width: 180px">
                <span>原采购重量 (g)</span>
                <input v-model.number="archiveForm.totalWeight" type="number" min="1" class="input" />
              </label>
              <label class="field" style="max-width: 180px">
                <span>期初库存 (g) <em class="hint">默认 0</em></span>
                <input v-model.number="archiveForm.openingStock" type="number" min="0" class="input" placeholder="0" />
              </label>
              <label class="field" style="max-width: 200px">
                <span>供应商</span>
                <input v-model="archiveForm.supplier" type="text" class="input" placeholder="可选" />
              </label>
            </div>
            <div class="form-actions">
              <button
                class="btn btn-secondary"
                :disabled="!canCreateArchive || creatingArchive"
                @click="doCreateArchivePurchase"
              >
                {{ creatingArchive ? '创建中…' : '创建归档采购' }}
              </button>
              <p v-if="archiveError" class="error-text">{{ archiveError }}</p>
            </div>
          </div>
        </template>
      </section>

      <!-- Step 1: 选择采购批次 -->
      <section class="card">
        <h2 class="card-title">1. 选择采购批次</h2>
        <p class="card-hint">先在「生豆管理」中补建历史生豆与采购批次，或在上方直接创建历史归档采购。</p>
        <label class="field">
          <span>采购批次</span>
          <select v-model="purchaseBatchId" class="input" @change="onPickBatch">
            <option value="">— 请选择 —</option>
            <option v-for="pb in purchaseBatchOptions" :key="pb.id" :value="pb.id">
              {{ pb.label }} · 余 {{ pb.remaining }}g
            </option>
          </select>
        </label>
      </section>

      <!-- Step 2: 上传 + 默认参数 -->
      <section class="card" :class="{ disabled: !purchaseBatchId }">
        <h2 class="card-title">2. 上传 CSV 并设置默认参数</h2>
        <div
          class="dropzone"
          :class="{ dragging }"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <p>拖拽多个 Kaleido CSV 到此处，或</p>
          <label class="file-pick">
            选择文件
            <input type="file" accept=".csv" multiple @change="onFileInput" hidden />
          </label>
        </div>
        <ul v-if="files.length" class="file-chips">
          <li v-for="(f, i) in files" :key="i">{{ f.name }}<button class="chip-x" @click="files.splice(i, 1)">✕</button></li>
        </ul>

        <div class="defaults">
          <label class="field">
            <span>默认投豆量 (g)</span>
            <input v-model.number="defaultInputWeight" type="number" min="1" class="input" />
          </label>
          <label class="field">
            <span>默认烘焙日期</span>
            <input v-model="defaultRoastDate" type="date" class="input" />
          </label>
          <label class="field">
            <span>当天首锅时间</span>
            <input v-model="firstRoastTime" type="time" class="input" />
          </label>
          <label class="field">
            <span>时间推断策略</span>
            <select v-model="strategy" class="input">
              <option value="auto">自动</option>
              <option value="csv_content">CSV 内容</option>
              <option value="filename">文件名</option>
              <option value="file_last_modified">文件修改时间</option>
              <option value="manual">手动日期 + 首锅时间</option>
              <option value="upload_order">按上传顺序分配</option>
            </select>
          </label>
        </div>
        <p class="note">默认 <strong>不影响库存</strong>（entry_mode = historical_backfill，inventory_effective = false）。</p>

        <button class="btn btn-primary" :disabled="!purchaseBatchId || !files.length || loading" @click="doPreview">
          {{ loading ? '解析中…' : '解析预览' }}
        </button>
        <p v-if="errorText" class="error-text">{{ errorText }}</p>
      </section>

      <!-- Step 3: 预览 -->
      <section v-if="preview" class="card">
        <h2 class="card-title">3. 预览与确认</h2>
        <div class="preview-meta">
          <span>可用库存：{{ preview.available_stock_grams }}g</span>
          <span>预计投豆合计：{{ plannedTotal }}g</span>
        </div>
        <div class="table-wrap">
          <table class="preview-table">
            <thead>
              <tr>
                <th>文件名</th><th>烘焙时间</th><th>来源</th><th>投豆(g)</th><th>出豆(g)</th>
                <th>影响库存</th><th>总时长</th><th>发展率</th><th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in editableRows" :key="row.item_id" :class="{ dup: row.is_duplicate, failed: row.parse_status === 'failed' }">
                <td class="fname" :title="row.parse_error_message || row.filename">
                  {{ row.filename }}
                  <div v-if="row.parse_error_message" class="parse-error">{{ row.parse_error_message }}</div>
                </td>
                <td>
                  <input v-if="row.parse_status === 'parsed'" v-model="row.roasted_at" type="datetime-local" class="cell-input" />
                  <span v-else>—</span>
                </td>
                <td>{{ row.roasted_at_source || '-' }}</td>
                <td>
                  <input v-if="row.parse_status === 'parsed'" v-model.number="row.actual_input_weight_grams" type="number" min="1" class="cell-input sm" />
                </td>
                <td>
                  <input v-if="row.parse_status === 'parsed'" v-model.number="row.output_weight_grams" type="number" min="0" class="cell-input sm" />
                </td>
                <td>
                  <input v-if="row.parse_status === 'parsed'" v-model="row.inventory_effective" type="checkbox" />
                </td>
                <td>{{ fmt(row.summary?.total_time_seconds) }}</td>
                <td>{{ fmt(row.summary?.development_ratio_percent, '%') }}</td>
                <td>
                  <span v-if="row.parse_status === 'failed'" class="tag tag-fail">失败</span>
                  <span v-else-if="row.is_duplicate" class="tag tag-dup">重复</span>
                  <span v-else class="tag tag-ok">已解析</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <button class="btn btn-primary" :disabled="!canCommit || loading" @click="doCommit">
          {{ loading ? '提交中…' : `提交补录（${commitableCount} 个）` }}
        </button>
      </section>

      <!-- Step 4: 结果 -->
      <section v-if="commitResult" class="card">
        <h2 class="card-title">4. 补录结果</h2>
        <p>成功 {{ commitResult.success_count }} 个，失败 {{ commitResult.failed_count }} 个，扣减库存 {{ commitResult.total_consumed_grams }}g。</p>
        <ul class="result-list">
          <li v-for="(it, i) in commitResult.items" :key="i" :class="it.success ? 'ok' : 'fail'">
            <span>{{ it.filename }}</span>
            <span v-if="it.success">→ {{ it.roasting_batch_id?.slice(0, 8) }}</span>
            <span v-else>{{ it.error_message }}</span>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, reactive } from 'vue'
import { isDemoMode, ApiError } from '../api/http'
import * as greenBeanApi from '../api/greenBeans'
import { toGreenBeanTree } from '../adapters/greenBean'
import {
  previewHistoricalRoastCsvBackfill,
  commitHistoricalRoastCsvBackfill,
} from '../api/backfills'
import { cancelBulkImportJob } from '../api/bulkImports'
import type {
  BulkImportPreviewResponseDto,
  BulkImportCommitResponseDto,
  TimeInferenceStrategy,
} from '../api/bulkImports'
import { invalidateRoastContext } from '../services/greenBeanContextService'
import { addPurchaseBatch as apiAddPurchaseBatch } from '../services/greenBeanService'

const loading = ref(false)
const errorText = ref('')
const dragging = ref(false)
const showNewArchive = ref(false)

// -- Archive purchase creation form --
const archiveForm = reactive({
  greenBeanId: '',
  purchaseDate: new Date().toISOString().split('T')[0],
  totalWeight: 5000,
  openingStock: 0 as number | undefined,
  supplier: '',
})
const creatingArchive = ref(false)
const archiveError = ref('')
const greenBeanOptions = ref<{ id: string; label: string }[]>([])

const canCreateArchive = computed(
  () => archiveForm.greenBeanId && archiveForm.totalWeight > 0 && !creatingArchive.value,
)

const purchaseBatchId = ref('')
const purchaseBatchOptions = ref<{ id: string; label: string; remaining: number }[]>([])

const files = ref<File[]>([])
const defaultInputWeight = ref<number | null>(550)
const defaultRoastDate = ref('')
const firstRoastTime = ref('09:30')
const strategy = ref<TimeInferenceStrategy>('auto')

const preview = ref<BulkImportPreviewResponseDto | null>(null)
const commitResult = ref<BulkImportCommitResponseDto | null>(null)

type EditableRow = {
  item_id: string
  filename: string
  roasted_at: string
  roasted_at_source: string | null
  actual_input_weight_grams: number | null
  output_weight_grams: number | null
  inventory_effective: boolean
  parse_status: 'parsed' | 'failed'
  parse_error_message: string | null
  is_duplicate: boolean
  summary: Record<string, number | null>
}
const editableRows = ref<EditableRow[]>([])

onMounted(loadPurchaseBatches)

onBeforeUnmount(() => {
  // Best-effort cancel the current previewed job when leaving the page.
  if (preview.value?.job_id) {
    cancelBulkImportJob(preview.value.job_id).catch(() => {})
  }
})

async function loadPurchaseBatches() {
  if (isDemoMode) return
  try {
    const tree = await greenBeanApi.getGreenBeanTree({})
    const { greenBeans, purchaseBatches } = toGreenBeanTree(tree)
    const beanNameById = new Map(greenBeans.map((g) => [g.id, g.name]))
    purchaseBatchOptions.value = purchaseBatches.map((p) => {
      const beanName = beanNameById.get(p.greenBeanId) ?? '生豆'
      const parts: string[] = []
      if (p.inventoryTrackingMode === 'historical_archive') parts.push('历史归档')
      parts.push(beanName)
      parts.push(`原采购 ${p.totalWeight}g`)
      if (p.openingStockGrams !== undefined) parts.push(`期初 ${p.openingStockGrams}g`)
      parts.push(`剩余 ${p.remainingStock}g`)
      return {
        id: p.id,
        label: parts.join(' · '),
        remaining: p.remainingStock ?? 0,
      }
    })
    greenBeanOptions.value = greenBeans.map((g) => ({
      id: g.id,
      label: `${g.name}${g.variety ? ' · ' + g.variety : ''}`,
    }))
  } catch (e) {
    errorText.value = e instanceof ApiError ? e.message : '加载采购批次失败'
  }
}

async function onPickBatch() {
  if (preview.value?.job_id) {
    await cancelBulkImportJob(preview.value.job_id).catch(() => {})
  }
  preview.value = null
  commitResult.value = null
}

async function doCreateArchivePurchase() {
  if (!canCreateArchive.value) return
  creatingArchive.value = true
  archiveError.value = ''
  try {
    await apiAddPurchaseBatch(archiveForm.greenBeanId, {
      name: '',
      variety: '',
      process: '',
      region: '',
      purchaseDate: archiveForm.purchaseDate,
      totalWeight: archiveForm.totalWeight,
      supplier: archiveForm.supplier || undefined,
      inventoryTrackingMode: 'historical_archive',
      openingStockGrams: archiveForm.openingStock ?? 0,
    })
    // Refresh the purchase batch list so the new archive batch appears
    await loadPurchaseBatches()
    archiveError.value = ''
  } catch (e) {
    archiveError.value = e instanceof ApiError ? e.message : '创建归档采购失败'
  } finally {
    creatingArchive.value = false
  }
}

function onFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) files.value.push(...Array.from(input.files))
}
function onDrop(e: DragEvent) {
  dragging.value = false
  if (e.dataTransfer?.files)
    files.value.push(...Array.from(e.dataTransfer.files).filter((f) => f.name.endsWith('.csv')))
}

function toLocalInput(dt: string | null): string {
  if (!dt) return ''
  const d = new Date(dt)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function doPreview() {
  errorText.value = ''
  if (!purchaseBatchId.value || !files.value.length) return
  loading.value = true
  try {
    // Cancel previous previewed job before creating a new one.
    if (preview.value?.job_id) {
      await cancelBulkImportJob(preview.value.job_id).catch(() => {})
      preview.value = null
    }
    const res = await previewHistoricalRoastCsvBackfill(
      {
        purchase_batch_id: purchaseBatchId.value,
        default_input_weight_grams: defaultInputWeight.value ?? undefined,
        inventory_effective_default: false,
        default_roast_date: defaultRoastDate.value || undefined,
        first_roast_time: firstRoastTime.value || undefined,
        time_inference_strategy: strategy.value,
      },
      files.value,
    )
    preview.value = res
    editableRows.value = res.items.map((it) => ({
      item_id: it.item_id,
      filename: it.filename,
      roasted_at: toLocalInput(it.inferred_roasted_at),
      roasted_at_source: it.roasted_at_source,
      actual_input_weight_grams: it.input_weight_grams ?? defaultInputWeight.value,
      output_weight_grams: it.output_weight_grams ?? null,
      inventory_effective: it.inventory_effective,
      parse_status: it.parse_status,
      parse_error_message: it.parse_error_message,
      is_duplicate: it.is_duplicate,
      summary: it.summary as Record<string, number | null>,
    }))
    commitResult.value = null
  } catch (e) {
    errorText.value = e instanceof ApiError ? e.message : '解析预览失败'
  } finally {
    loading.value = false
  }
}

const commitableRows = computed(() =>
  editableRows.value.filter((r) => r.parse_status === 'parsed' && !r.is_duplicate && r.actual_input_weight_grams && r.roasted_at),
)
const commitableCount = computed(() => commitableRows.value.length)
const plannedTotal = computed(() => commitableRows.value.reduce((s, r) => s + (r.actual_input_weight_grams ?? 0), 0))
const canCommit = computed(() => commitableCount.value > 0)

async function doCommit() {
  if (!canCommit.value || !preview.value) return
  loading.value = true
  errorText.value = ''
  try {
    const items = commitableRows.value.map((r) => ({
      item_id: r.item_id,
      roasted_at: r.roasted_at ? new Date(r.roasted_at).toISOString() : null,
      actual_input_weight_grams: r.actual_input_weight_grams,
      output_weight_grams: r.output_weight_grams,
      inventory_effective: r.inventory_effective,
    }))
    const res = await commitHistoricalRoastCsvBackfill(
      { job_id: preview.value.job_id, items },
      files.value,
    )
    commitResult.value = res
    invalidateRoastContext()
  } catch (e) {
    errorText.value = e instanceof ApiError ? e.message : '提交失败'
  } finally {
    loading.value = false
  }
}

function fmt(v: number | null | undefined, suffix = ''): string {
  return v == null ? '-' : `${Math.round(v * 100) / 100}${suffix}`
}
</script>

<style scoped>
.backfill-page { padding: 20px; max-width: 1100px; margin: 0 auto; }
.page-header h1 { margin: 0 0 4px; font-size: var(--fs-2xl); }
.subtitle { margin: 0 0 20px; color: var(--text-secondary); font-size: var(--fs-sm); }
.notice { background: var(--warning-subtle); color: var(--warning); padding: 12px 16px; border-radius: 8px; }
.notice code { background: rgba(0,0,0,0.06); padding: 1px 4px; border-radius: 4px; }

.card { background: var(--surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 18px; margin-bottom: 16px; }
.card.disabled { opacity: 0.5; pointer-events: none; }
.card-title { margin: 0 0 4px; font-size: var(--fs-md); }
.card-hint { margin: 0 0 12px; color: var(--text-tertiary); font-size: var(--fs-xs); }

.field { display: flex; flex-direction: column; gap: 4px; font-size: var(--fs-sm); color: var(--text-secondary); max-width: 320px; margin-bottom: 10px; }
.input, .cell-input { padding: 6px 8px; border: 1px solid var(--border-default); border-radius: 6px; font-size: var(--fs-sm); background: var(--surface); }
.cell-input.sm { width: 72px; }

.dropzone { border: 2px dashed var(--border-strong); border-radius: 10px; padding: 24px; text-align: center; background: var(--surface-subtle); }
.dropzone.dragging { border-color: var(--primary); }
.file-pick { display: inline-block; padding: 6px 14px; background: var(--primary); color: #fff; border-radius: 6px; cursor: pointer; font-size: var(--fs-sm); }
.file-chips { list-style: none; padding: 0; margin: 10px 0 0; display: flex; flex-wrap: wrap; gap: 6px; }
.file-chips li { display: flex; align-items: center; gap: 6px; background: var(--surface-subtle); border: 1px solid var(--border-default); border-radius: 14px; padding: 3px 8px; font-size: var(--fs-xs); }
.chip-x { border: none; background: none; cursor: pointer; color: var(--text-tertiary); }

.defaults { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 12px 0; }
.note { font-size: var(--fs-xs); color: var(--text-tertiary); }

.preview-meta { display: flex; gap: 18px; margin-bottom: 10px; font-size: var(--fs-sm); color: var(--text-secondary); }
.table-wrap { overflow: auto; border: 1px solid var(--border-default); border-radius: 8px; margin-bottom: 12px; }
.preview-table { width: 100%; border-collapse: collapse; font-size: var(--fs-xs); }
.preview-table th { background: var(--surface-subtle); text-align: left; padding: 8px; border-bottom: 1px solid var(--border-default); }
.preview-table td { padding: 6px 8px; border-bottom: 1px solid var(--border-default); }
.preview-table tr.dup { background: var(--warning-subtle); }
.preview-table tr.failed { background: var(--danger-subtle); }
.fname { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tag { padding: 2px 6px; border-radius: 4px; }
.tag-ok { background: var(--success-subtle); color: var(--success); }
.tag-fail { background: var(--danger-subtle); color: var(--danger); }
.tag-dup { background: var(--warning-subtle); color: var(--warning); }
.parse-error { margin-top: 3px; color: var(--danger); white-space: normal; max-width: 260px; }

.result-list { list-style: none; padding: 0; }
.result-list li { padding: 6px 0; display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-default); }
.result-list li.ok { color: var(--success); } .result-list li.fail { color: var(--danger); }

.btn { padding: 7px 16px; border-radius: 6px; border: none; cursor: pointer; font-size: var(--fs-sm); }
.btn-primary { background: var(--primary); color: #fff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.error-text { color: var(--danger); font-size: var(--fs-sm); margin-top: 10px; }
</style>
