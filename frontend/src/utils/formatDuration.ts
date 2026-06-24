/** P1-3: Shared duration formatter — seconds → mm:ss.

    Used by BulkCsvImportDialog and HistoricalBackfill preview tables.
    0 → "00:00", 75 → "01:15", 610 → "10:10", null → "-".
*/
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '-'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
