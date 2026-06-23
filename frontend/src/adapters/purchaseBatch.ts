import type { PurchaseBatchCreateRequestDto } from '../api/types'

/** Frontend form -> Backend CreatePurchase DTO */
export function toPurchaseBatchCreateDto(form: {
  purchaseDate: string
  totalWeight: number
  pricePerKg?: number
  moistureContent?: number
  supplier?: string
  lotNumber?: string
  inventoryTrackingMode?: string
  openingStockGrams?: number
}): PurchaseBatchCreateRequestDto {
  return {
    purchase_date: form.purchaseDate,
    total_weight_grams: form.totalWeight,
    unit_price_fen_per_kg: form.pricePerKg !== undefined ? Math.round(form.pricePerKg * 100) : undefined,
    moisture_content_percent: form.moistureContent ?? undefined,
    supplier: form.supplier || undefined,
    lot_number: form.lotNumber || undefined,
    inventory_tracking_mode: form.inventoryTrackingMode as 'normal' | 'historical_archive' | undefined,
    opening_stock_grams: form.openingStockGrams ?? undefined,
  }
}
