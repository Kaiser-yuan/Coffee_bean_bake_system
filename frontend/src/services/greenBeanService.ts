import { isDemoMode } from '../api/http'
import * as greenBeanApi from '../api/greenBeans'
import { toGreenBeanWithFirstPurchaseDto } from '../adapters/greenBean'
import { toPurchaseBatchCreateDto } from '../adapters/purchaseBatch'

export type GreenBeanPurchaseForm = {
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
  inventoryTrackingMode?: string
  openingStockGrams?: number
}

export async function createGreenBeanWithFirstPurchase(form: GreenBeanPurchaseForm) {
  if (isDemoMode) {
    const mock = await import('../mock')
    const bean = await mock.apiCreateGreenBean({
      name: form.name,
      variety: form.variety,
      process: form.process as import('../types').BeanProcess,
      region: form.region,
      brand: form.brand,
      season: form.season,
      farm: form.farm,
      elevation: form.elevation,
      vendorFlavorDescription: form.vendorFlavorDescription,
    })
    await mock.apiCreatePurchaseBatch({
      greenBeanId: bean.id,
      purchaseDate: form.purchaseDate,
      totalWeight: form.totalWeight,
      pricePerKg: form.pricePerKg,
      moistureContent: form.moistureContent,
      supplier: form.supplier,
      lotNumber: form.lotNumber,
    })
    return bean
  }
  const result = await greenBeanApi.createGreenBeanWithFirstPurchase(
    toGreenBeanWithFirstPurchaseDto(form),
  )
  return result.green_bean
}

export async function addPurchaseBatch(greenBeanId: string, form: GreenBeanPurchaseForm) {
  if (isDemoMode) {
    const mock = await import('../mock')
    return mock.apiCreatePurchaseBatch({
      greenBeanId,
      purchaseDate: form.purchaseDate,
      totalWeight: form.totalWeight,
      pricePerKg: form.pricePerKg,
      moistureContent: form.moistureContent,
      supplier: form.supplier,
      lotNumber: form.lotNumber,
    })
  }
  return greenBeanApi.addPurchaseBatch(greenBeanId, toPurchaseBatchCreateDto(form))
}
