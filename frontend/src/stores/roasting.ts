import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RoastingBatch } from '../types'
import { fetchRoastingBatches, completeRoastingBatch } from '../services/roastingBatchService'

export const useRoastingStore = defineStore('roasting', () => {
  const batches = ref<RoastingBatch[]>([])
  const total = ref(0)
  const loading = ref(false)

  const compareSelection = ref<Set<string>>(new Set())

  const canCompare = computed(() => {
    return compareSelection.value.size >= 2 && compareSelection.value.size <= 4
  })

  function toggleCompareSelection(batchId: string) {
    const s = new Set(compareSelection.value)
    if (s.has(batchId)) {
      s.delete(batchId)
    } else {
      if (s.size >= 4) return
      s.add(batchId)
    }
    compareSelection.value = s
  }

  function clearCompareSelection() {
    compareSelection.value = new Set()
  }

  async function fetchBatches() {
    loading.value = true
    try {
      const res = await fetchRoastingBatches()
      batches.value = res.items
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  async function markComplete(batchId: string, actualInputWeightGrams: number, roastedAt?: string) {
    await completeRoastingBatch(batchId, actualInputWeightGrams, roastedAt)
    await fetchBatches()
  }

  return {
    batches,
    total,
    loading,
    compareSelection,
    canCompare,
    toggleCompareSelection,
    clearCompareSelection,
    fetchBatches,
    markComplete,
  }
})
