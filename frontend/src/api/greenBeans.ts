import { apiRequest } from './http'
import type {
  GreenBeanMatchDto,
  GreenBeanTreeDto,
  GreenBeanDto,
  GreenBeanUpdateRequestDto,
  GreenBeanWithFirstPurchaseRequestDto,
  PurchaseBatchCreateRequestDto,
} from './types'

export function getGreenBeanTree(params: {
  search?: string
  variety?: string
  process?: string
  region?: string
  archive_status?: 'active' | 'archived' | 'all'
} = {}) {
  const qs = new URLSearchParams()
  if (params.search) qs.set('search', params.search)
  if (params.variety) qs.set('variety', params.variety)
  if (params.process) qs.set('process', params.process)
  if (params.region) qs.set('region', params.region)
  if (params.archive_status) qs.set('archive_status', params.archive_status)

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

export function updateGreenBean(greenBeanId: string, body: GreenBeanUpdateRequestDto) {
  return apiRequest<GreenBeanDto>(`/green-beans/${greenBeanId}`, {
    method: 'PATCH',
    body,
    auth: true,
  })
}

export function deleteOrArchiveGreenBean(greenBeanId: string) {
  return apiRequest<{ status: 'deleted' | 'archived'; green_bean_id: string }>(
    `/green-beans/${greenBeanId}`,
    { method: 'DELETE', auth: true },
  )
}

export function restoreGreenBean(greenBeanId: string) {
  return apiRequest<{ status: 'restored'; green_bean_id: string }>(
    `/green-beans/${greenBeanId}/restore`,
    { method: 'POST', auth: true },
  )
}
