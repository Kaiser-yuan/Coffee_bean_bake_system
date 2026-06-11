import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { GreenBean, RoastingBatch } from '../types'
import * as api from '../mock'

export const useAppStore = defineStore('app', () => {
  const currentYear = ref(new Date().getFullYear())
  const sidebarCollapsed = ref(false)
  const globalLoading = ref(false)

  function setYear(year: number) {
    currentYear.value = year
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return {
    currentYear,
    sidebarCollapsed,
    globalLoading,
    setYear,
    toggleSidebar,
  }
})
