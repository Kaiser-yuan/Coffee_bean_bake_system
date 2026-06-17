<template>
  <div v-if="open" class="dialog-overlay" @click.self="close">
    <div class="dialog-panel">
      <header class="dialog-header">
        <h2>批量 CSV 生成烘焙批次</h2>
        <button class="icon-btn" @click="close">✕</button>
      </header>

      <div class="dialog-body">
        <!-- 上传 + 默认参数 -->
        <section v-if="step === 'config'" class="step-config">
          <div
            class="dropzone"
            :class="{ dragging }"
            @dragover.prevent="dragging = true"
            @dragleave.prevent="dragging = false"
            @drop.prevent="onDrop"
          >
            <p class="dz-title">拖拽多个 Kaleido CSV 到此处，或</p>
            <label class="file-pick">
              选择文件
              <input type="file" accept=".csv" multiple @change="onFileInput" hidden />
            </label>
            <p class="dz-hint">支持一次选择多个 CSV，按文件名 / 内容推断烘焙时间</p>
          </div>

          <ul v-if="selectedFiles.length" class="file-chips">
            <li v-for="(f, i) in selectedFiles" :key="i">
              <span>{{ f.name }}</span>
              <button class="chip-x" @click="removeFile(i)">✕</button>
            </li>
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
                <option value="auto">自动（内容 → 文件名 → 修改时间）</option>
                <option value="csv_content">CSV 内容</option>
                <option value="filename">文件名</option>
                <option value="file_last_modified">文件修改时间</option>
                <option value="manual">手动日期 + 首锅时间</option>
                <option value="upload_order">按上传顺序分配</option>
              </select>
            </label>
            <label class="field checkbox">
              <input v-model="inventoryEffectiveDefault" type="checkbox" />
              <span>影响当前库存（默认扣减）</span>
            </label>
          </div>

          <p v-if="configError" class="error-text">{{ configError }}</p>
        </section>

        <!-- 预览表 -->
        <section v-else-if="step === 'preview'" class="step-preview">
          <div class="preview-meta">
            <span>库存可用：{{ preview?.available_stock_grams ?? '-' }} g</span>
            <span>预计投豆合计：{{ plannedTotal }} g</span>
            <span :class="inventoryOk ? 'ok' : 'warn'">
              {{ inventoryOk ? '库存充足' : '库存不足，提交将被拒绝' }}
            </span>
          </div>

          <div class="table-wrap">
            <table class="preview-table">
              <thead>
                <tr>
                  <th>文件名</th>
                  <th>推断烘焙时间</th>
                  <th>来源</th>
                  <th>投豆量(g)</th>
                  <th>出豆量(g)</th>
                  <th>扣库存</th>
                  <th>总时长</th>
                  <th>一爆开始</th>
                  <th>发展率</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in editableRows" :key="row.item_id" :class="{ dup: row.is_duplicate, failed: row.parse_status === 'failed' }">
                  <td class="fname" :title="row.filename">{{ row.filename }}</td>
                  <td>
                    <input
                      v-if="row.parse_status === 'parsed'"
                      v-model="row.roasted_at"
                      type="datetime-local"
                      class="cell-input"
                    />
                    <span v-else>—</span>
                  </td>
                  <td>{{ row.roasted_at_source || '-' }}</td>
                  <td>
                    <input
                      v-if="row.parse_status === 'parsed'"
                      v-model.number="row.actual_input_weight_grams"
                      type="number"
                      min="1"
                      class="cell-input sm"
                    />
                    <span v-else>—</span>
                  </td>
                  <td>
                    <input
                      v-if="row.parse_status === 'parsed'"
                      v-model.number="row.output_weight_grams"
                      type="number"
                      min="0"
                      class="cell-input sm"
                    />
                    <span v-else>—</span>
                  </td>
                  <td>
                    <input
                      v-if="row.parse_status === 'parsed'"
                      v-model="row.inventory_effective"
                      type="checkbox"
                    />
                  </td>
                  <td>{{ fmt(row.summary?.total_time_seconds) }}</td>
                  <td>{{ fmt(row.summary?.first_crack_start_seconds) }}</td>
                  <td>{{ fmt(row.summary?.development_ratio_percent, '%') }}</td>
                  <td>
                    <span v-if="row.parse_status === 'failed'" class="tag tag-fail">解析失败</span>
                    <span v-else-if="row.is_duplicate" class="tag tag-dup">疑似重复</span>
                    <span v-else class="tag tag-ok">已解析</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="batch-tools">
            <span>批量设置投豆量：</span>
            <input v-model.number="batchInputWeight" type="number" min="1" class="cell-input sm" />
            <button class="btn btn-ghost" @click="applyBatchInput">应用到全部</button>
          </div>

          <ul v-if="preview?.blocking_errors?.length" class="error-list">
            <li v-for="(e, i) in preview.blocking_errors" :key="i">{{ e }}</li>
          </ul>
        </section>

        <!-- 提交结果 -->
        <section v-else class="step-result">
          <p class="result-line">
            共生成 <strong>{{ commitResult?.success_count ?? 0 }}</strong> 个烘焙批次，
            失败 {{ commitResult?.failed_count ?? 0 }} 个，
            扣减库存 {{ commitResult?.total_consumed_grams ?? 0 }} g。
          </p>
          <ul class="result-list">
            <li v-for="(it, i) in commitResult?.items ?? []" :key="i" :class="it.success ? 'ok' : 'fail'">
              <span>{{ it.filename }}</span>
              <span v-if="it.success">→ 批次 {{ shortId(it.roasting_batch_id) }}</span>
              <span v-else>失败：{{ it.error_message }}</span>
            </li>
          </ul>
        </section>
      </div>

      <footer class="dialog-footer">
        <button class="btn btn-ghost" @click="close">关闭</button>
        <button
          v-if="step === 'config'"
          class="btn btn-primary"
          :disabled="!selectedFiles.length || loading"
          @click="doPreview"
        >
          {{ loading ? '解析中…' : '解析预览' }}
        </button>
        <button v-if="step === 'preview'" class="btn btn-ghost" @click="step = 'config'">返回</button>
        <button
          v-if="step === 'preview'"
          class="btn btn-primary"
          :disabled="!canCommit || loading"
          @click="doCommit"
        >
          {{ loading ? '提交中…' : `提交生成（${commitableCount} 个）` }}
        </button>
        <button v-if="step === 'result'" class="btn btn-primary" @click="close">完成</button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ApiError } from '../../api/http'
import {
  previewPurchaseBatchCsvImport,
  commitPurchaseBatchCsvImport,
  type BulkImportPreviewResponseDto,
  type BulkImportCommitResponseDto,
  type TimeInferenceStrategy,
} from '../../api/bulkImports'

const props = defineProps<{
  open: boolean
  purchaseBatchId: string
}>()
const emit = defineEmits<{ (e: 'committed'): void; (e: 'close'): void }>()

type EditableRow = {
  item_id: string
  filename: string
  file_hash: string
  roasted_at: string
  roasted_at_source: string | null
  actual_input_weight_grams: number | null
  output_weight_grams: number | null
  inventory_effective: boolean
  parse_status: 'parsed' | 'failed'
  is_duplicate: boolean
  summary: Record<string, number | null>
}

const step = ref<'config' | 'preview' | 'result'>('config')
const loading = ref(false)
const configError = ref('')
const dragging = ref(false)

const selectedFiles = ref<File[]>([])
const defaultInputWeight = ref<number | null>(550)
const inventoryEffectiveDefault = ref(true)
const defaultRoastDate = ref('')
const firstRoastTime = ref('09:30')
const strategy = ref<TimeInferenceStrategy>('auto')
const batchInputWeight = ref<number | null>(550)

const preview = ref<BulkImportPreviewResponseDto | null>(null)
const editableRows = ref<EditableRow[]>([])
const commitResult = ref<BulkImportCommitResponseDto | null>(null)

watch(() => props.open, (o) => {
  if (o) reset()
})

function reset() {
  step.value = 'config'
  configError.value = ''
  selectedFiles.value = []
  preview.value = null
  editableRows.value = []
  commitResult.value = null
}

function close() {
  emit('close')
}

function onFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) selectedFiles.value.push(...Array.from(input.files))
}
function onDrop(e: DragEvent) {
  dragging.value = false
  if (e.dataTransfer?.files) {
    selectedFiles.value.push(...Array.from(e.dataTransfer.files).filter((f) => f.name.endsWith('.csv')))
  }
}
function removeFile(i: number) {
  selectedFiles.value.splice(i, 1)
}

function toLocalInput(dt: string | null): string {
  if (!dt) return ''
  const d = new Date(dt)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function doPreview() {
  configError.value = ''
  if (!selectedFiles.value.length) return
  loading.value = true
  try {
    const res = await previewPurchaseBatchCsvImport(props.purchaseBatchId, selectedFiles.value, {
      default_input_weight_grams: defaultInputWeight.value ?? undefined,
      inventory_effective_default: inventoryEffectiveDefault.value,
      default_roast_date: defaultRoastDate.value || undefined,
      first_roast_time: firstRoastTime.value || undefined,
      time_inference_strategy: strategy.value,
    })
    preview.value = res
    editableRows.value = res.items.map((it) => ({
      item_id: it.item_id,
      filename: it.filename,
      file_hash: it.file_hash,
      roasted_at: toLocalInput(it.inferred_roasted_at),
      roasted_at_source: it.roasted_at_source,
      actual_input_weight_grams: it.input_weight_grams ?? defaultInputWeight.value,
      output_weight_grams: it.output_weight_grams ?? null,
      inventory_effective: it.inventory_effective,
      parse_status: it.parse_status,
      is_duplicate: it.is_duplicate,
      summary: it.summary as Record<string, number | null>,
    }))
    step.value = 'preview'
  } catch (e) {
    configError.value = e instanceof ApiError ? e.message : '解析预览失败'
  } finally {
    loading.value = false
  }
}

function applyBatchInput() {
  if (batchInputWeight.value) {
    for (const r of editableRows.value) {
      if (r.parse_status === 'parsed') r.actual_input_weight_grams = batchInputWeight.value
    }
  }
}

const commitableRows = computed(() =>
  editableRows.value.filter((r) => r.parse_status === 'parsed' && !r.is_duplicate && r.actual_input_weight_grams && r.roasted_at),
)
const commitableCount = computed(() => commitableRows.value.length)
const plannedTotal = computed(() =>
  commitableRows.value.reduce((s, r) => s + (r.actual_input_weight_grams ?? 0), 0),
)
const inventoryOk = computed(() => {
  if (!preview.value) return true
  const effectiveTotal = commitableRows.value
    .filter((r) => r.inventory_effective)
    .reduce((s, r) => s + (r.actual_input_weight_grams ?? 0), 0)
  return effectiveTotal <= preview.value.available_stock_grams
})
const canCommit = computed(() => commitableCount.value > 0 && inventoryOk.value)

async function doCommit() {
  if (!canCommit.value || !preview.value) return
  loading.value = true
  try {
    const items = commitableRows.value.map((r) => ({
      item_id: r.item_id,
      roasted_at: r.roasted_at ? new Date(r.roasted_at).toISOString() : null,
      actual_input_weight_grams: r.actual_input_weight_grams,
      output_weight_grams: r.output_weight_grams,
      inventory_effective: r.inventory_effective,
    }))
    const res = await commitPurchaseBatchCsvImport(
      props.purchaseBatchId,
      { job_id: preview.value.job_id, items },
      selectedFiles.value,
    )
    commitResult.value = res
    step.value = 'result'
    if (res.success_count > 0) emit('committed')
  } catch (e) {
    configError.value = e instanceof ApiError ? e.message : '提交失败'
  } finally {
    loading.value = false
  }
}

function fmt(v: number | null | undefined, suffix = ''): string {
  return v == null ? '-' : `${Math.round(v * 100) / 100}${suffix}`
}
function shortId(id: string | null): string {
  return id ? id.slice(0, 8) : ''
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed; inset: 0; background: rgba(20, 28, 48, 0.45);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.dialog-panel {
  width: min(1100px, 95vw); max-height: 90vh; background: var(--surface);
  border-radius: 12px; display: flex; flex-direction: column; overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,0.25);
}
.dialog-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border-default); }
.dialog-header h2 { margin: 0; font-size: var(--fs-lg); }
.icon-btn { border: none; background: none; cursor: pointer; font-size: 16px; color: var(--text-secondary); }
.dialog-body { padding: 20px; overflow: auto; flex: 1; }
.dialog-footer { padding: 14px 20px; border-top: 1px solid var(--border-default); display: flex; gap: 10px; justify-content: flex-end; }

.dropzone { border: 2px dashed var(--border-strong); border-radius: 10px; padding: 28px; text-align: center; background: var(--surface-subtle); }
.dropzone.dragging { border-color: var(--primary); background: var(--primary-subtle); }
.dz-title { margin: 0 0 8px; color: var(--text-secondary); }
.dz-hint { margin: 8px 0 0; font-size: var(--fs-xs); color: var(--text-tertiary); }
.file-pick { display: inline-block; padding: 6px 14px; background: var(--primary); color: #fff; border-radius: 6px; cursor: pointer; font-size: var(--fs-sm); }

.file-chips { list-style: none; padding: 0; margin: 12px 0 0; display: flex; flex-wrap: wrap; gap: 6px; }
.file-chips li { display: flex; align-items: center; gap: 6px; background: var(--surface-subtle); border: 1px solid var(--border-default); border-radius: 14px; padding: 3px 8px; font-size: var(--fs-xs); }
.chip-x { border: none; background: none; cursor: pointer; color: var(--text-tertiary); }

.defaults { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 16px; }
.field { display: flex; flex-direction: column; gap: 4px; font-size: var(--fs-sm); color: var(--text-secondary); }
.field.checkbox { flex-direction: row; align-items: center; gap: 8px; }
.input, .cell-input { padding: 6px 8px; border: 1px solid var(--border-default); border-radius: 6px; font-size: var(--fs-sm); background: var(--surface); }

.preview-meta { display: flex; gap: 18px; margin-bottom: 12px; font-size: var(--fs-sm); color: var(--text-secondary); }
.preview-meta .ok { color: var(--success); } .preview-meta .warn { color: var(--danger); }
.table-wrap { overflow: auto; border: 1px solid var(--border-default); border-radius: 8px; }
.preview-table { width: 100%; border-collapse: collapse; font-size: var(--fs-xs); }
.preview-table th { background: var(--surface-subtle); text-align: left; padding: 8px; border-bottom: 1px solid var(--border-default); color: var(--text-secondary); white-space: nowrap; }
.preview-table td { padding: 6px 8px; border-bottom: 1px solid var(--border-default); }
.preview-table tr.dup { background: var(--warning-subtle); }
.preview-table tr.failed { background: var(--danger-subtle); }
.fname { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-input.sm { width: 72px; }
.tag { padding: 2px 6px; border-radius: 4px; font-size: var(--fs-xs); }
.tag-ok { background: var(--success-subtle); color: var(--success); }
.tag-fail { background: var(--danger-subtle); color: var(--danger); }
.tag-dup { background: var(--warning-subtle); color: var(--warning); }

.batch-tools { display: flex; align-items: center; gap: 8px; margin-top: 12px; font-size: var(--fs-sm); color: var(--text-secondary); }
.error-text, .error-list { color: var(--danger); font-size: var(--fs-sm); margin: 10px 0 0; }
.error-list { padding-left: 18px; }

.result-line { font-size: var(--fs-base); }
.result-list { list-style: none; padding: 0; margin-top: 12px; }
.result-list li { padding: 6px 0; display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-default); }
.result-list li.ok { color: var(--success); } .result-list li.fail { color: var(--danger); }

.btn { padding: 7px 16px; border-radius: 6px; border: none; cursor: pointer; font-size: var(--fs-sm); }
.btn-primary { background: var(--primary); color: #fff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost { background: var(--surface-subtle); color: var(--text-secondary); border: 1px solid var(--border-default); }
</style>
