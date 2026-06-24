/**
 * Roasting curve service.
 */
import { ApiError, isDemoMode } from '../api/http'
import * as curveApi from '../api/curves'
import type { RoastingCurve } from '../types'
import type { CurveEventDto, CurvePointDto } from '../api/types'

let _mockMod: typeof import('../mock') | null = null
async function getMock() {
  if (!_mockMod) _mockMod = await import('../mock')
  return _mockMod
}

function toPoint(point: CurvePointDto) {
  return {
    sampleIndex: point.sample_index,
    elapsedSeconds: point.elapsed_seconds,
    beanTempCelsius: point.bean_temp_celsius ?? undefined,
    environmentTempCelsius: point.environment_temp_celsius ?? undefined,
    rorCelsiusPerMinute: point.ror_celsius_per_minute ?? undefined,
    targetTempCelsius: point.target_temp_celsius ?? undefined,
    heatingPowerMode: point.heating_power_mode ?? undefined,
    heatingPowerPercent: point.heating_power_percent ?? undefined,
    smokeDamperPercent: point.smoke_damper_percent ?? undefined,
    rollerPercent: point.roller_percent ?? undefined,
    powerStatus: point.power_status ?? undefined,
  }
}

function toEvent(event: CurveEventDto) {
  return {
    time: event.time_seconds ?? 0,
    type: event.type as import('../types').CurveEvent['type'],
    label: event.label,
    beanTemp: event.bean_temp_celsius ?? undefined,
  }
}

export async function fetchCurve(batchId: string): Promise<RoastingCurve | null> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiGetCurve(batchId)
  }
  let dto
  try {
    dto = await curveApi.getCurve(batchId)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
  return {
    id: dto.curve_file?.id || `curve_${batchId}`,
    roastingBatchId: batchId,
    points: dto.points.map(toPoint),
    events: dto.events.map(toEvent),
    parsedAt: '',
    csvFileName: dto.curve_file?.original_filename || '',
  }
}

export async function uploadCurve(batchId: string, file: File): Promise<void> {
  if (isDemoMode) {
    throw new ApiError('演示模式不能上传曲线，请切换到真实 API 模式', 400)
  }
  const result = await curveApi.uploadCurveFile(batchId, file)
  if (result.parse_status !== 'parsed') {
    throw new ApiError(result.parse_error_message || '曲线解析失败', 422, 'CURVE_PARSE_FAILED')
  }
}

export async function fetchCurves(batchIds: string[]): Promise<RoastingCurve[]> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiGetCurves(batchIds)
  }
  if (batchIds.length === 1) {
    const curve = await fetchCurve(batchIds[0])
    return curve ? [curve] : []
  }
  const dto = await curveApi.compareCurves(batchIds)
  return dto.series.map((series) => ({
    id: `curve_${series.batch.id}`,
    roastingBatchId: series.batch.id,
    points: series.points.map(toPoint),
    events: series.events.map(toEvent),
    parsedAt: '',
    csvFileName: '',
  }))
}
