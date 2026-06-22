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

export async function fetchRoastContext(force = false): Promise<RoastContext> {
  if (cache && !force) return cache
  if (inflight) return inflight

  inflight = (async () => {
    let ctx: RoastContext
    if (isDemoMode) {
      const mock = await import('../mock')
      ctx = {
        greenBeans: [...mock.mockGreenBeans],
        purchaseBatches: [...mock.mockPurchaseBatches],
        roastingBatches: [...mock.mockRoastingBatches],
      }
    } else {
      const [tree, batches] = await Promise.all([
        greenBeanApi.getGreenBeanTree({}),
        listRoastingBatches({ page: 1, page_size: 500 }),
      ])
      const treeContext = toGreenBeanTree(tree)
      ctx = {
        ...treeContext,
        roastingBatches: batches.items.map(toRoastingBatch),
      }
    }
    cache = ctx
    inflight = null
    return ctx
  })()

  return inflight
}

/** Clear the in-memory cache (e.g. after a create/commit that changes the tree). */
export function invalidateRoastContext() {
  cache = null
}

/** Resolve the green bean for a roasting batch (demo-aware, sync after fetch). */
export function getGreenBeanByBatch(ctx: RoastContext, batch: RoastingBatch): GreenBean | undefined {
  const pb = ctx.purchaseBatches.find((p) => p.id === batch.purchaseBatchId)
  if (!pb) return undefined
  return ctx.greenBeans.find((g) => g.id === pb.greenBeanId)
}
