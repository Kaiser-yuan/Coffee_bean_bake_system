import { apiRequest } from './http'
import type { StandardTermDto, TermUpdateRequestDto } from './types'

export function listTerms(category?: string, active?: boolean) {
  const params = new URLSearchParams()
  if (category) params.set('category', category)
  if (active !== undefined) params.set('active', String(active))
  const query = params.toString()
  return apiRequest<StandardTermDto[]>(`/terms${query ? `?${query}` : ''}`)
}

export function listAdminTerms(category?: string) {
  const params = new URLSearchParams()
  if (category) params.set('category', category)
  const query = params.toString()
  return apiRequest<StandardTermDto[]>(`/admin/terms${query ? `?${query}` : ''}`, {
    auth: true,
  })
}

export function updateTerm(id: string, body: TermUpdateRequestDto) {
  return apiRequest<StandardTermDto>(`/admin/terms/${id}`, {
    method: 'PATCH',
    body,
    auth: true,
  })
}
