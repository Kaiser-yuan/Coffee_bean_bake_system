<template>
  <div class="public-page">
    <div class="public-card">
      <h1 class="public-title">☕ 咖啡风味评价</h1>
      <p class="public-subtitle">
        {{ getBeanName }} · 烘焙于 {{ getBatchDate }}
      </p>

      <LoadingState v-if="loading" text="加载问卷…" />
      <ErrorState v-else-if="error" title="问卷不存在或已过期" :retry="true" @retry="fetchQ" />

      <!-- 已提交 -->
      <div v-else-if="submitted" class="submitted-box">
        <span class="submitted-icon">✅</span>
        <h2>感谢您的评价！</h2>
        <p>您的反馈已记录。</p>
      </div>

      <!-- 评分表单 -->
      <form v-else @submit.prevent="onSubmit" class="eval-form">
        <!-- 评分维度 -->
        <div v-for="dim in dimensions" :key="dim.key" class="dim-row">
          <div class="dim-header">
            <span class="dim-label">
              {{ dim.label }}
              <span v-if="dim.isIntensity" class="dim-intensity">（强度）</span>
            </span>
            <span class="dim-desc text-xs text-tertiary">{{ dim.description }}</span>
          </div>
          <div class="star-row">
            <button
              v-for="n in 5"
              :key="n"
              type="button"
              class="star-btn"
              :class="{ active: (form as any)[dim.key] >= n }"
              @click="(form as any)[dim.key] = (form as any)[dim.key] === n ? 0 : n"
            >
              {{ (form as any)[dim.key] >= n ? '★' : '☆' }}
            </button>
            <button
              type="button"
              class="skip-btn"
              :class="{ active: (form as any)[dim.key] === 0 }"
              @click="(form as any)[dim.key] = 0"
            >
              不确定
            </button>
          </div>
        </div>

        <!-- 冲煮信息 -->
        <div class="form-divider"></div>
        <div class="form-group">
          <label class="dim-label">冲煮方式</label>
          <div class="chip-row">
            <button
              v-for="m in BREW_METHODS"
              :key="m"
              type="button"
              class="chip"
              :class="{ active: form.brewMethod === m }"
              @click="form.brewMethod = m"
            >{{ m }}</button>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group flex-1">
            <label class="dim-label">饮用温度</label>
            <div class="chip-row">
              <button
                v-for="t in DRINK_TEMPERATURES"
                :key="t"
                type="button"
                class="chip"
                :class="{ active: form.drinkTemperature === t }"
                @click="form.drinkTemperature = t"
              >{{ t }}</button>
            </div>
          </div>
          <div class="form-group flex-1">
            <label class="dim-label">饮用形式</label>
            <div class="chip-row">
              <button
                v-for="f in DRINK_FORMS"
                :key="f"
                type="button"
                class="chip"
                :class="{ active: form.drinkForm === f }"
                @click="form.drinkForm = f"
              >{{ f }}</button>
            </div>
          </div>
        </div>

        <!-- 风味描述 -->
        <div class="form-group">
          <label class="dim-label">风味描述 <span class="text-xs text-tertiary">（可多选）</span></label>
          <div class="checkbox-grid">
            <label
              v-for="f in FLAVOR_TAGS"
              :key="f"
              class="checkbox-item"
              :class="{ checked: form.flavorNotes.includes(f) }"
            >
              <input
                type="checkbox"
                :value="f"
                v-model="form.flavorNotes"
                class="hidden-checkbox"
              />
              {{ f }}
            </label>
          </div>
        </div>

        <!-- 自由备注 -->
        <div class="form-group">
          <label class="dim-label">自由备注</label>
          <textarea
            v-model="form.freeNotes"
            class="textarea"
            rows="3"
            placeholder="任何您想补充的…"
          ></textarea>
        </div>

        <!-- 评价者信息 -->
        <div class="form-row">
          <div class="form-group flex-1">
            <label class="dim-label">您的称呼</label>
            <input v-model="form.evaluatorName" type="text" class="input" placeholder="可选" />
          </div>
          <div class="form-group flex-1">
            <label class="dim-label">身份</label>
            <select v-model="form.evaluatorType" class="select">
              <option value="customer">顾客</option>
              <option value="colleague">同事</option>
              <option value="roaster">烘焙师</option>
            </select>
          </div>
        </div>

        <div class="submit-area">
          <button
            type="submit"
            class="submit-btn"
            :disabled="!isValid"
          >
            提交评价
          </button>
          <p v-if="!isValid" class="text-xs text-danger">
            请至少完成综合喜好评分
          </p>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import {
  mockRoastingBatches,
  getGreenBeanByBatch,
  apiGetQuestionnaireByCode,
  apiSubmitEvaluation,
} from '../mock'
import { FLAVOR_TAGS, BREW_METHODS, DRINK_TEMPERATURES, DRINK_FORMS } from '../types'
import type { Questionnaire } from '../types'
import LoadingState from '../components/common/LoadingState.vue'
import ErrorState from '../components/common/ErrorState.vue'

const route = useRoute()
const shareCode = route.params.shareCode as string

const loading = ref(false)
const error = ref(false)
const submitted = ref(false)
const questionnaire = ref<Questionnaire | null>(null)

const dimensions = [
  { key: 'dryFragrance', label: '干香', description: '干咖啡粉的香气', isIntensity: false },
  { key: 'wetAroma', label: '湿香', description: '注水后的湿香', isIntensity: false },
  { key: 'acidity', label: '酸感', description: '酸味的强度', isIntensity: true },
  { key: 'sweetness', label: '甜感', description: '甜味的感受', isIntensity: false },
  { key: 'bitterness', label: '苦感', description: '苦味的强度', isIntensity: true },
  { key: 'aftertaste', label: '回味', description: '吞咽后的余味', isIntensity: false },
  { key: 'overallPreference', label: '综合喜好', description: '整体的喜欢程度', isIntensity: false },
]

const form = reactive({
  dryFragrance: 0,
  wetAroma: 0,
  acidity: 0,
  sweetness: 0,
  bitterness: 0,
  aftertaste: 0,
  overallPreference: 0,
  brewMethod: '手冲' as string,
  drinkTemperature: '热饮' as string,
  drinkForm: '黑咖啡' as string,
  flavorNotes: [] as string[],
  freeNotes: '',
  evaluatorName: '',
  evaluatorType: 'customer' as 'roaster' | 'colleague' | 'customer',
})

// 只有综合喜好是必填，其他维度可以"不确定"
const isValid = computed(() => {
  return form.overallPreference > 0
})

const getBeanName = computed(() => {
  if (!questionnaire.value) return ''
  const b = mockRoastingBatches.find(b => b.id === questionnaire.value!.roastingBatchId)
  if (!b) return ''
  return getGreenBeanByBatch(b)?.name || ''
})

const getBatchDate = computed(() => {
  if (!questionnaire.value) return ''
  const b = mockRoastingBatches.find(b => b.id === questionnaire.value!.roastingBatchId)
  return b?.actualDate || b?.plannedDate || ''
})

async function fetchQ() {
  loading.value = true
  error.value = false
  try {
    const q = await apiGetQuestionnaireByCode(shareCode)
    if (q && q.status === 'open') {
      questionnaire.value = q
    } else {
      error.value = true
    }
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

async function onSubmit() {
  if (!isValid.value || !questionnaire.value) return
  try {
    // Calculate bean age days from roast date
    let beanAgeDays: number | undefined
    const batch = mockRoastingBatches.find(b => b.id === questionnaire.value!.roastingBatchId)
    if (batch?.actualDate) {
      const bakeDate = new Date(batch.actualDate)
      const today = new Date()
      beanAgeDays = Math.floor((today.getTime() - bakeDate.getTime()) / (1000 * 60 * 60 * 24))
    }

    await apiSubmitEvaluation({
      questionnaireId: questionnaire.value.id,
      roastingBatchId: questionnaire.value.roastingBatchId,
      dryFragrance: form.dryFragrance,
      wetAroma: form.wetAroma,
      acidity: form.acidity,
      sweetness: form.sweetness,
      bitterness: form.bitterness,
      aftertaste: form.aftertaste,
      overallPreference: form.overallPreference,
      brewMethod: form.brewMethod as any,
      drinkTemperature: form.drinkTemperature as any,
      drinkForm: form.drinkForm as any,
      flavorNotes: form.flavorNotes,
      freeNotes: form.freeNotes,
      evaluatorName: form.evaluatorName,
      evaluatorType: form.evaluatorType,
      beanAgeDays,
      submittedAt: new Date().toISOString().split('T')[0],
    })
    submitted.value = true
  } catch {
    alert('提交失败，请重试')
  }
}

onMounted(fetchQ)
</script>

<style scoped>
.public-page {
  min-height: 100vh;
  background: #f5f7fb;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: var(--sp-6);
}

.public-card {
  width: 100%;
  max-width: 640px;
  background: #fff;
  border: 1px solid #e5e9f2;
  border-radius: 8px;
  padding: var(--sp-8) var(--sp-6);
  margin-top: var(--sp-6);
}

.public-title {
  font-size: 22px;
  font-weight: 700;
  text-align: center;
  margin-bottom: var(--sp-1);
  color: #172033;
}

.public-subtitle {
  text-align: center;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  margin-bottom: var(--sp-8);
}

.submitted-box {
  text-align: center;
  padding: var(--sp-8) 0;
}

.submitted-icon { font-size: 48px; display: block; margin-bottom: var(--sp-3); }
.submitted-box h2 { font-size: var(--fs-xl); margin-bottom: var(--sp-2); font-weight: 600; }

.eval-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

.dim-row {
  border-bottom: 1px solid #e5e9f2;
  padding-bottom: var(--sp-2);
}

.dim-header {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  margin-bottom: var(--sp-2);
}

.dim-label {
  font-size: var(--fs-base);
  font-weight: 500;
  color: var(--text-primary);
}

.dim-intensity {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-weight: 400;
}

.star-row {
  display: flex;
  align-items: center;
  gap: 2px;
}

.star-btn {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: #d7ddea;
  transition: color 0.15s;
  padding: 0 2px;
  line-height: 1;
}

.star-btn.active { color: #e5a029; }

.skip-btn {
  margin-left: var(--sp-3);
  padding: 2px 10px;
  border: 1px solid #d7ddea;
  border-radius: var(--radius-sm);
  background: var(--surface);
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  cursor: pointer;
  font-family: var(--font-sans);
}

.skip-btn.active {
  border-color: var(--primary);
  background: var(--primary-subtle);
  color: var(--primary);
}

/* Chips */
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1);
}

.chip {
  padding: 4px 14px;
  border: 1px solid var(--border-default);
  border-radius: 16px;
  font-size: var(--fs-sm);
  background: var(--surface);
  color: var(--text-secondary);
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.15s;
}

.chip:hover { border-color: var(--border-strong); }
.chip.active {
  background: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--primary);
}

/* Form */
.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.form-row {
  display: flex;
  gap: var(--sp-4);
}

.form-divider {
  border-top: 1px solid var(--border-default);
}

.flex-1 { flex: 1; }

.checkbox-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1);
}

.checkbox-item {
  padding: 4px 12px;
  border: 1px solid var(--border-default);
  border-radius: 16px;
  font-size: var(--fs-sm);
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
  color: var(--text-secondary);
}

.checkbox-item.checked {
  background: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--primary);
}

.hidden-checkbox {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.textarea {
  width: 100%;
  padding: var(--sp-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-family: var(--font-sans);
  resize: vertical;
  outline: none;
  background: var(--app-bg);
}

.textarea:focus { border-color: var(--primary); background: var(--surface); }

.input, .select {
  height: var(--input-height);
  padding: 0 var(--sp-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  font-family: var(--font-sans);
  background: var(--surface);
  outline: none;
  width: 100%;
  color: var(--text-primary);
}

.input:focus, .select:focus { border-color: var(--primary); }

.submit-area {
  text-align: center;
  padding-top: var(--sp-2);
}

.submit-btn {
  width: 100%;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--primary);
  color: #fff;
  border: none;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  font-family: var(--font-sans);
}

.submit-btn:hover { background: var(--primary-hover); }
.submit-btn:disabled { background: #d7ddea; cursor: not-allowed; }
</style>
