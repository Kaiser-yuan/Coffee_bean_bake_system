/** Shared label helpers for entry mode, inventory status, and source notes.

    P1-4: Ensure green-bean tree, roasting list, and curve detail / review pages
    consistently display batch origin tags (批量导入 / 历史补录 / 仅归档).
*/
export const ENTRY_MODE_LABELS: Record<string, string> = {
  csv_bulk_import: '批量导入',
  historical_backfill: '历史补录',
  manual_plan: '手动计划',
  manual_completed: '手动完成',
}

/** Short, human-readable label for an entry mode value. */
export function entryModeLabel(mode: string | undefined | null): string {
  if (!mode) return ''
  return ENTRY_MODE_LABELS[mode] || mode
}

/** Tag list describing a batch's origin and inventory effect. */
export function batchSourceLabels(entryMode?: string, inventoryEffective?: boolean | null, sourceNote?: string): string[] {
  const tags: string[] = []
  const modeLabel = entryModeLabel(entryMode)
  if (modeLabel) tags.push(modeLabel)
  if (inventoryEffective === false) tags.push('仅归档')
  if (sourceNote) tags.push(sourceNote)
  return tags
}
