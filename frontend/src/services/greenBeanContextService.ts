/**
 * Green-bean context service — shared lookup of green beans, purchase batches,
 * and roasting batches. In demo mode reads the in-memory mock arrays; in real
 * mode loads everything from the /green-beans/tree endpoint (flattened).
 *
 * Used by views that need to resolve bean names / populate create-form
 * dropdowns without importing mock directly.
 */
import { isDemoMode } from '../api/http'
import * as greenBeanApi from '../api/greenBeans'
import { listRoastingBatches } from '../api/roastingBatches'
import { toGreenBeanTree } from '../adapters/greenBean'
import { toRoastingBatch } from '../adapters/roastingBatch'
import type { GreenBean, PurchaseBatch, RoastingBatch } from '../types'

export interface RoastContext {
  greenBeans: GreenBean[]
  purchaseBatches: PurchaseBatch[]
  roastingBatches: RoastingBatch[]
}

let cache: RoastContext | null = null
let inflight: Promise<RoastContext> | null = null
let generation = 0

async function loadRoastContext(): Promise<RoastContext> {
  if (isDemoMode) {
    const mock = await import('../mock')
    return {
      greenBeans: [...mock.mockGreenBeans],
      purchaseBatches: [...mock.mockPurchaseBatches],
      roastingBatches: [...mock.mockRoastingBatches],
    }
  }
  const [tree, batches] = await Promise.all([
    greenBeanApi.getGreenBeanTree({ archive_status: 'all' }),
    listRoastingBatches({ page: 1, page_size: 500 }),
  ])
  const treeContext = toGreenBeanTree(tree)
  return {
    ...treeContext,
    roastingBatches: batches.items.map(toRoastingBatch),
  }
}

export async function fetchRoastContext(force = false): Promise<RoastContext> {
  if (force) cache = null
  if (cache && !force) return cache
  if (inflight) return inflight

  const requestGeneration = generation
  const request = loadRoastContext()
  inflight = request

  try {
    const ctx = await request
    // Only persist to cache if no invalidation occurred while the request was in flight.
    if (requestGeneration === generation) cache = ctx
    return ctx
  } finally {
    if (inflight === request) inflight = null
  }
}

/** Clear the in-memory cache and bump the generation so any in-flight
 *  request cannot overwrite a newer fetch. (e.g. after a create/commit
 *  that changes the tree.) */
export function invalidateRoastContext() {
  cache = null
  generation += 1
}

/** Lightweight green-bean only context — does NOT request roasting batches.
 *  P1-1: used by RoastingBatchList page which already has batches via the store. */
export async function fetchGreenBeanTreeContext(): Promise<{
  greenBeans: GreenBean[]
  purchaseBatches: PurchaseBatch[]
}> {
  if (isDemoMode) {
    const mock = await import('../mock')
    return {
      greenBeans: [...mock.mockGreenBeans],
      purchaseBatches: [...mock.mockPurchaseBatches],
    }
  }
  const tree = await greenBeanApi.getGreenBeanTree({ archive_status: 'all' })
  return toGreenBeanTree(tree)  // only greenBeans + purchaseBatches, no roasting batches
}

/** Resolve the green bean for a roasting batch (demo-aware, sync after fetch). */
export function getGreenBeanByBatch(ctx: RoastContext, batch: RoastingBatch): GreenBean | undefined {
  const pb = ctx.purchaseBatches.find((p) => p.id === batch.purchaseBatchId)
  if (!pb) return undefined
  return ctx.greenBeans.find((g) => g.id === pb.greenBeanId)
}
