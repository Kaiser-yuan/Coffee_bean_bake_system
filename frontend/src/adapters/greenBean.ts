import type { GreenBeanDto, GreenBeanMatchDto, GreenBeanTreeDto } from '../api/types'
import type { GreenBean } from '../types'

/** GreenBeanDto -> GreenBean */
export function toGreenBean(dto: GreenBeanDto): GreenBean {
  return {
    id: dto.id,
    name: dto.name,
    variety: dto.variety || '',
    process: (dto.process || '其他') as GreenBean['process'],
    region: dto.region || '',
    country: dto.country || '',
    farm: dto.farm || undefined,
    elevation: dto.elevation || undefined,
    brand: dto.brand || undefined,
    season: dto.harvest_season || undefined,
    vendorFlavorDescription: dto.vendor_flavor_description || undefined,
    firstCreated: dto.first_created_at || '',
  }
}

/** GreenBeanMatchDto -> GreenBean (abbreviated for suggestions) */
export function toGreenBeanSuggestion(dto: GreenBeanMatchDto): GreenBean {
  return {
    id: dto.id,
    name: dto.name,
    variety: '',
    process: (dto.processing_method || '其他') as GreenBean['process'],
    region: dto.region || '',
    country: '',
    brand: dto.brand || undefined,
    season: dto.harvest_season || undefined,
    firstCreated: '',
  }
}

/** GreenBeanWithFirstPurchase form -> Backend request DTO */
export function toGreenBeanWithFirstPurchaseDto(form: {
  name: string
  variety: string
  process: string
  region: string
  brand?: string
  season?: string
  farm?: string
  elevation?: string
  vendorFlavorDescription?: string
  purchaseDate: string
  totalWeight: number
  pricePerKg?: number
  moistureContent?: number
  supplier?: string
  lotNumber?: string
}): {
  name: string
  variety?: string | null
  process?: string | null
  region?: string | null
  country?: string | null
  brand?: string | null
  harvest_season?: string | null
  farm?: string | null
  elevation?: string | null
  vendor_flavor_description?: string | null
  purchase_date: string
  total_weight_grams: number
  unit_price_fen_per_kg?: number | null
  moisture_content_percent?: number | null
  supplier?: string | null
  lot_number?: string | null
} {
  return {
    name: form.name,
    variety: form.variety || undefined,
    process: form.process || undefined,
    region: form.region || undefined,
    country: undefined,
    brand: form.brand || undefined,
    harvest_season: form.season || undefined,
    farm: form.farm || undefined,
    elevation: form.elevation || undefined,
    vendor_flavor_description: form.vendorFlavorDescription || undefined,
    purchase_date: form.purchaseDate,
    total_weight_grams: form.totalWeight,
    unit_price_fen_per_kg: form.pricePerKg !== undefined ? Math.round(form.pricePerKg * 100) : undefined,
    moisture_content_percent: form.moistureContent ?? undefined,
    supplier: form.supplier || undefined,
    lot_number: form.lotNumber || undefined,
  }
}

/** Tree API -> frontend domain models, flattened */
export function toGreenBeanTree(tree: GreenBeanTreeDto[]): {
  greenBeans: GreenBean[]
  purchaseBatches: import('../types').PurchaseBatch[]
  roastingBatches: import('../types').RoastingBatch[]
} {
  const greenBeans: GreenBean[] = []
  const purchaseBatches: import('../types').PurchaseBatch[] = []
  const roastingBatches: import('../types').RoastingBatch[] = []

  for (const beanDto of tree) {
    greenBeans.push(toGreenBean(beanDto))

    for (const pbDto of beanDto.purchase_batches) {
      purchaseBatches.push({
        id: pbDto.id,
        greenBeanId: pbDto.green_bean_id,
        purchaseDate: pbDto.purchase_date || '',
        totalWeight: pbDto.total_weight_grams,
        moistureContent: pbDto.moisture_content_percent ?? undefined,
        pricePerKg: pbDto.unit_price_fen_per_kg !== null && pbDto.unit_price_fen_per_kg !== undefined
          ? pbDto.unit_price_fen_per_kg / 100
          : undefined,
        totalPrice: pbDto.total_price_fen !== null && pbDto.total_price_fen !== undefined
          ? pbDto.total_price_fen / 100
          : undefined,
        supplier: pbDto.supplier || undefined,
        lotNumber: pbDto.lot_number || undefined,
        notes: pbDto.notes || undefined,
        remainingStock: pbDto.remaining_weight_grams ?? 0,
        adjustments: [],
      })

      for (const rbDto of pbDto.roasting_batches) {
        roastingBatches.push({
          id: rbDto.id,
          purchaseBatchId: rbDto.purchase_batch_id,
          plannedDate: rbDto.planned_at || undefined,
          actualDate: rbDto.roasted_at || undefined,
          beanWeightIn: rbDto.planned_input_weight_grams,
          beanWeightOut: rbDto.output_weight_grams ?? undefined,
          weightLossRate: rbDto.weight_loss_percent ?? undefined,
          totalTime: rbDto.total_time_seconds ?? undefined,
          developmentTime: rbDto.development_time_seconds ?? undefined,
          developmentRatio: rbDto.development_ratio_percent ?? undefined,
          targetDescription: rbDto.target_description || undefined,
          status: rbDto.status as import('../types').BatchStatus,
          curveStatus: 'none' as import('../types').CurveStatus,
          evaluationStatus: 'none' as import('../types').EvaluationStatus,
          reviewStatus: 'none' as import('../types').ReviewStatus,
          colorTag: rbDto.color_tag || undefined,
        })
      }
    }
  }

  return { greenBeans, purchaseBatches, roastingBatches }
}
