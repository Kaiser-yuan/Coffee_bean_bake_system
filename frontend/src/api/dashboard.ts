import { apiRequest } from './http'
import type { DashboardResponseDto } from './types'

export function getDashboard(year: number): Promise<DashboardResponseDto> {
  return apiRequest<DashboardResponseDto>(`/dashboard?year=${year}`, { auth: true })
}
