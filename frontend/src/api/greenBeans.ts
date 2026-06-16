import { apiRequest } from './http'
import type {
  GreenBeanMatchDto,
  GreenBeanTreeDto,
  GreenBeanWithFirstPurchaseRequestDto,
  PurchaseBatchCreateRequestDto,
} from './types'

export function getGreenBeanTree(params: {
  search?: string
  variety?: string
  process?: string
  region?: string
} = {}) {
  const qs = new URLSearchParams()
  if (params.search) qs.set('search', params.search)
  if (params.variety) qs.set('variety', params.variety)
  if (params.process) qs.set('process', params.process)
  if (params.region) qs.set('region', params.region)

  const query = qs.toString()
  return apiRequest<GreenBeanTreeDto[]>(`/green-beans/tree${query ? `?${query}` : ''}`, {
    auth: true,
  })
}

export function matchGreenBeans(name: string) {
  const qs = new URLSearchParams({ name })
  return apiRequest<GreenBeanMatchDto[]>(`/green-beans/matches?${qs}`, {
    auth: true,
  })
}

export function createGreenBeanWithFirstPurchase(body: GreenBeanWithFirstPurchaseRequestDto) {
  return apiRequest<{ green_bean: Record<string, unknown>; purchase_batch: Record<string, unknown> }>(
    '/green-beans/with-first-purchase',
    {
      method: 'POST',
      body,
      auth: true,
    },
  )
}

export function addPurchaseBatch(greenBeanId: string, body: PurchaseBatchCreateRequestDto) {
  return apiRequest(`/green-beans/${greenBeanId}/purchase-batches`, {
    method: 'POST',
    body,
    auth: true,
  })
}
