import { isDemoMode } from '../api/http'
import { getDashboard } from '../api/dashboard'
import { listRoastingBatches } from '../api/roastingBatches'
import { toRoastingBatch } from '../adapters/roastingBatch'
import type { DashboardYearData } from '../types'

let _mockMod: typeof import('../mock') | null = null
async function getMock() {
  if (!_mockMod) _mockMod = await import('../mock')
  return _mockMod
}

export async function fetchDashboard(year: number): Promise<DashboardYearData> {
  if (isDemoMode) {
    return getMock().then((m) => m.getDashboardData(year))
  }
  const [dto, batchesDto] = await Promise.all([
    getDashboard(year),
    listRoastingBatches({ page: 1, page_size: 500 }),
  ])
  const batches = batchesDto.items.map(toRoastingBatch)
  const completedThisYear = batches.filter((batch) => {
    const date = batch.actualDate || batch.plannedDate
    return batch.status === 'completed' && !!date && new Date(date).getFullYear() === year
  })
  return {
    year: dto.year,
    totalRoasts: dto.total_completed_roasts,
    totalRoastedBeanProfiles: dto.total_roasted_bean_profiles,
    totalInputWeight: dto.total_input_weight_grams,
    avgWeightLossRate: dto.average_weight_loss_percent ?? 0,
    monthlyRoasts: dto.monthly_roasts,
    varietyDistribution: dto.variety_distribution,
    regionDistribution: dto.region_distribution,
    pendingBatches: batches.filter((batch) => batch.status === 'planned'),
    recentBatches: completedThisYear.slice(0, 8),
  }
}
