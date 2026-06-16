import type { StandardTerm } from '../types'
import type { StandardTermDto } from '../api/types'

export function toStandardTerm(dto: StandardTermDto): StandardTerm {
  return {
    id: dto.id,
    category: dto.category as StandardTerm['category'],
    value: dto.value,
    active: dto.is_active,
    usageCount: dto.usage_count,
  }
}
