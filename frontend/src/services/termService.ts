/**
 * Standard terms service. In demo mode delegates to the in-memory mock;
 * in real mode calls the backend terms API.
 */
import { isDemoMode } from '../api/http'
import * as termApi from '../api/terms'
import { toStandardTerm } from '../adapters/term'
import type { StandardTerm } from '../types'

let _mockMod: typeof import('../mock') | null = null
async function getMock() {
  if (!_mockMod) _mockMod = await import('../mock')
  return _mockMod
}

export async function fetchTerms(): Promise<StandardTerm[]> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiGetTerms()
  }
  return (await termApi.listAdminTerms()).map(toStandardTerm)
}

export async function updateTerm(
  id: string,
  data: Partial<StandardTerm>,
): Promise<StandardTerm> {
  if (isDemoMode) {
    const m = await getMock()
    return m.apiUpdateTerm(id, data)
  }
  return toStandardTerm(await termApi.updateTerm(id, {
    value: data.value,
    is_active: data.active,
  }))
}
