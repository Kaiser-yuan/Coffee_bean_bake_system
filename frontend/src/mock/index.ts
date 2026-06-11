// ============================================================
// 咖啡烘焙数据分析系统 - Mock 数据层
// 模拟异步请求，支持成功、空数据、失败三种状态
// ============================================================

import type {
  GreenBean, PurchaseBatch, RoastingBatch, RoastingCurve,
  Questionnaire, CuppingEvaluation, BatchReview,
  DashboardYearData, StandardTerm, CurveEvent, BrewMethod, DrinkTemperature, DrinkForm,
} from '../types'

// ---------- 工具函数 ----------

function uid(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

function randInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function randFloat(min: number, max: number, decimals = 1): number {
  return parseFloat((Math.random() * (max - min) + min).toFixed(decimals))
}

const now = new Date()
function isoDate(offsetDays: number): string {
  const d = new Date(now)
  d.setDate(d.getDate() + offsetDays)
  return d.toISOString().split('T')[0]
}

// ---------- 辅助数据 ----------

const beanNames = [
  '耶加雪菲 G1', '西达摩 G2', '肯尼亚 AA 奇安布', '曼特宁 林东', '巴西 喜拉朵',
  '哥伦比亚 娜玲珑', '危地马拉 安提瓜', '巴拿马 翡翠庄园 瑰夏', '云南 保山 铁皮卡',
  '卢旺达 恩戈马', '埃塞 古吉 罕贝拉', '哥斯达黎加 塔拉珠',
]

const varieties = ['铁皮卡', '波旁', '卡杜拉', '瑰夏', 'SL28', 'SL34', '埃塞原生种', '卡蒂姆']
const processes: Array<'水洗' | '日晒' | '蜜处理' | '厌氧发酵' | '半水洗' | '其他'> = ['水洗', '日晒', '蜜处理', '厌氧发酵', '半水洗', '其他']
const regions = ['埃塞俄比亚', '肯尼亚', '哥伦比亚', '巴西', '危地马拉', '巴拿马', '印度尼西亚', '云南', '卢旺达', '哥斯达黎加']
const roastLevels: Array<'浅烘' | '中浅烘' | '中烘' | '中深烘' | '深烘'> = ['浅烘', '中浅烘', '中烘', '中深烘', '深烘']
const brands = ['A 品牌', 'B 品牌', 'C 品牌', '无名氏']
const seasons = ['2025 产季', '2024 产季', '2023 产季', '2026 新产季']

const brewMethods: BrewMethod[] = ['杯测', '手冲', '意式', '奶咖', '其他']
const drinkTemps: DrinkTemperature[] = ['热饮', '冷饮']
const drinkForms: DrinkForm[] = ['黑咖啡', '加奶', '其他']

// ---------- 生豆档案 ----------

export const mockGreenBeans: GreenBean[] = beanNames.map((name, i) => ({
  id: `gb_${i + 1}`,
  name,
  variety: pick(varieties),
  process: pick(processes),
  region: pick(regions),
  country: pick(regions),
  farm: Math.random() > 0.4 ? `${pick(['A', 'B', 'C'])}农场` : undefined,
  elevation: Math.random() > 0.3 ? `${randInt(1200, 2200)}m` : undefined,
  brand: pick(brands),
  season: pick(seasons),
  vendorFlavorDescription: Math.random() > 0.4 ? pick(['花香、柑橘调性', '坚果巧克力调性', '热带水果、发酵感', '焦糖甜感、平衡']) : undefined,
  firstCreated: isoDate(-randInt(30, 400)),
}))

// ---------- 采购批次 ----------

export const mockPurchaseBatches: PurchaseBatch[] = []

for (let i = 0; i < 25; i++) {
  const gb = pick(mockGreenBeans)
  const totalWeight = randInt(5000, 60000)
  const pricePerKg = randFloat(30, 300, 0)
  mockPurchaseBatches.push({
    id: `pb_${i + 1}`,
    greenBeanId: gb.id,
    purchaseDate: isoDate(-randInt(10, 365)),
    totalWeight,
    moistureContent: randFloat(10, 13),
    pricePerKg,
    totalPrice: parseFloat((totalWeight / 1000 * pricePerKg).toFixed(2)),
    supplier: pick(['豆商A', '豆商B', '豆商C', '生豆集市']),
    lotNumber: `LOT-${randInt(1000, 9999)}`,
    remainingStock: randInt(0, Math.floor(totalWeight * 0.6)),
    adjustments: [],
  })
}

// ---------- 烘焙批次 ----------

const BATCH_COLORS = ['#df5b45', '#3478d4', '#1f9d68', '#8b5cc7', '#e5a029', '#d94b4b']

export const mockRoastingBatches: RoastingBatch[] = []

for (let i = 0; i < 40; i++) {
  const pb = pick(mockPurchaseBatches)
  const status: 'planned' | 'completed' = Math.random() > 0.25 ? 'completed' : 'planned'
  const hasCurve = status === 'completed' && Math.random() > 0.15
  const hasEval = hasCurve && Math.random() > 0.4
  const hasReview = hasCurve && Math.random() > 0.5
  const weightIn = randInt(200, 1000)

  mockRoastingBatches.push({
    id: `rb_${i + 1}`,
    purchaseBatchId: pb.id,
    plannedDate: isoDate(-randInt(0, 14)),
    actualDate: status === 'completed' ? isoDate(-randInt(1, 14)) : undefined,
    beanWeightIn: weightIn,
    beanWeightOut: status === 'completed' && Math.random() > 0.3
      ? Math.round(weightIn * randFloat(0.82, 0.88))
      : undefined,
    totalTime: status === 'completed' ? randInt(540, 900) : undefined,
    weightLossRate: undefined, // computed dynamically below
    developmentRatio: status === 'completed' ? randFloat(18, 24) : undefined,
    roastLevel: pick(roastLevels),
    targetDescription: Math.random() > 0.5 ? pick(['突出花香', '均衡发展', '追求甜感', '降低苦度']) : undefined,
    status,
    curveStatus: hasCurve ? 'parsed' : 'none',
    evaluationStatus: hasEval ? (Math.random() > 0.5 ? 'open' : 'closed') : 'none',
    reviewStatus: hasReview ? (Math.random() > 0.5 ? 'done' : 'draft') : 'none',
    csvFileName: hasCurve ? `batch_${i + 1}.csv` : undefined,
    csvUploadTime: hasCurve ? isoDate(-randInt(0, 14)) : undefined,
    colorTag: BATCH_COLORS[i % BATCH_COLORS.length],
  })
}

// Compute weight loss rate after creation (only when both values exist)
mockRoastingBatches.forEach(b => {
  if (b.beanWeightIn && b.beanWeightOut) {
    b.weightLossRate = parseFloat(((1 - b.beanWeightOut / b.beanWeightIn) * 100).toFixed(1))
  }
})

// ---------- 烘焙曲线 ----------

function generateCurvePoints(duration: number): import('../types').CurvePoint[] {
  const points: import('../types').CurvePoint[] = []
  const step = 1 // 1 second interval
  const chargeTemp = 200
  const tpTime = randInt(60, 100)
  const tpTemp = randInt(60, 90)
  const fcStart = randInt(420, 480)
  const dropTime = duration

  let bt = chargeTemp
  for (let t = 0; t <= duration; t += step) {
    const p: import('../types').CurvePoint = { time: t }

    if (t < tpTime) {
      bt = chargeTemp - (chargeTemp - tpTemp) * (t / tpTime)
    } else {
      const progress = (t - tpTime) / (dropTime - tpTime)
      const targetTemp = randInt(205, 218)
      bt = tpTemp + (targetTemp - tpTemp) * (1 - Math.exp(-3 * progress))
    }
    p.beanTemp = parseFloat(bt.toFixed(1))

    p.envTemp = parseFloat((p.beanTemp + randInt(20, 50) + (t < 300 ? 10 : 0)).toFixed(1))

    p.ror = t < dropTime - 10 ? parseFloat(randFloat(1.5, 8, 1).toString()) : 0

    if (t < tpTime) p.gas = 80
    else if (t < fcStart - 60) p.gas = 70
    else if (t < fcStart) p.gas = 60
    else p.gas = 50

    if (t < tpTime) p.airflow = 50
    else if (t < fcStart) p.airflow = 60
    else p.airflow = 70

    p.drumSpeed = 78

    points.push(p)
  }
  return points
}

export const mockCurves: RoastingCurve[] = []

mockRoastingBatches
  .filter(b => b.curveStatus === 'parsed')
  .forEach(b => {
    const duration = b.totalTime || randInt(540, 900)
    const events: CurveEvent[] = [
      { time: 0, type: 'charge', label: '入豆' },
      { time: randInt(60, 100), type: 'tp', label: '回温点' },
      { time: randInt(300, 360), type: 'turning', label: '转换点' },
      { time: randInt(420, 480), type: 'fc_start', label: '一爆开始' },
      { time: randInt(500, 560), type: 'fc_end', label: '一爆结束' },
      { time: duration, type: 'drop', label: '下豆' },
    ]

    mockCurves.push({
      id: `curve_${b.id}`,
      roastingBatchId: b.id,
      points: generateCurvePoints(duration),
      events,
      parsedAt: isoDate(-randInt(0, 14)),
      csvFileName: b.csvFileName || 'batch.csv',
    })
  })

// ---------- 问卷 ----------

export const mockQuestionnaires: Questionnaire[] = []

mockRoastingBatches
  .filter(b => b.evaluationStatus !== 'none')
  .forEach(b => {
    mockQuestionnaires.push({
      id: `q_${b.id}`,
      roastingBatchId: b.id,
      shareCode: Math.random().toString(36).slice(2, 10),
      status: b.evaluationStatus === 'open' ? 'open' : 'closed',
      createdAt: b.actualDate || isoDate(-7),
      expiresAt: isoDate(14),
      closedAt: b.evaluationStatus === 'closed' ? isoDate(-randInt(0, 3)) : undefined,
      submissionCount: randInt(b.evaluationStatus === 'closed' ? 3 : 0, 12),
    })
  })

// ---------- 杯测评价 ----------

const evaluatorNames = ['张师傅', '小李', '小王', '赵姐', '顾客A', '顾客B', '同事C', '烘焙师D']
const flavorTags = ['花香', '柑橘', '莓果', '巧克力', '坚果', '焦糖', '发酵', '酒香']

export const mockEvaluations: CuppingEvaluation[] = []

mockQuestionnaires.forEach(q => {
  const count = q.submissionCount
  for (let i = 0; i < count; i++) {
    // Some evaluations skip some dimensions (0 = not evaluated)
    const skipSome = Math.random() > 0.5
    mockEvaluations.push({
      id: `eval_${q.id}_${i}`,
      questionnaireId: q.id,
      roastingBatchId: q.roastingBatchId,
      evaluatorName: pick(evaluatorNames),
      evaluatorType: pick(['roaster', 'colleague', 'customer'] as const),
      brewMethod: pick(brewMethods),
      drinkTemperature: pick(drinkTemps),
      drinkForm: pick(drinkForms),
      dryFragrance: skipSome && Math.random() > 0.3 ? 0 : randInt(3, 5),
      wetAroma: randInt(3, 5),
      acidity: randInt(2, 5),
      sweetness: randInt(3, 5),
      bitterness: randInt(1, 4),
      aftertaste: randInt(3, 5),
      overallPreference: randInt(3, 5), // always rated
      flavorNotes: Array.from({ length: randInt(1, 4) }, () => pick(flavorTags)),
      freeNotes: Math.random() > 0.5 ? '整体口感不错，回甘明显。' : undefined,
      beanAgeDays: randInt(1, 14),
      submittedAt: isoDate(-randInt(0, 10)),
    })
  }
})

// ---------- 批次复盘 ----------

export const mockReviews: BatchReview[] = []

mockRoastingBatches
  .filter(b => b.reviewStatus !== 'none')
  .forEach(b => {
    mockReviews.push({
      id: `review_${b.id}`,
      roastingBatchId: b.id,
      personalReview: '脱水阶段延长了30秒，尝试在转换点后缓慢降火。一爆声响清晰，发展时间约1分40秒，下豆时机合适。整体酸度明亮，但甜感还可以再提升。',
      personalReviewAt: isoDate(-randInt(1, 7)),
      evaluationSummary: b.evaluationStatus === 'closed'
        ? '综合3位评价者反馈：干香花香明显，酸感适中偏强，甜感中等，回味持久。大部分评价者提到柑橘和莓果风味，与烘焙目标基本一致。部分评价者认为苦感略高，可能与一爆后火力调整有关。'
        : undefined,
      comprehensiveReview: b.reviewStatus === 'done'
        ? '结合曲线数据和评价反馈：脱水充分，发展率合理（约21%），但一爆后ROR下降偏快，可能导致部分甜感未充分发展。下一锅可尝试在转换点后更缓慢地降火，保持一爆后ROR在2-3℃/30s范围。'
        : undefined,
      comprehensiveReviewAt: b.reviewStatus === 'done' ? isoDate(-randInt(0, 3)) : undefined,
      nextBatchSuggestions: '建议下一锅在转换点至一爆之间降低降火速度，目标发展率达到22-23%。下豆温度可以尝试略高2-3℃以增强甜感。',
      reminders: [
        {
          id: `rem_${b.id}_1`,
          batchReviewId: `review_${b.id}`,
          priority: 1,
          content: '一爆后ROR控制：降火速度放慢，保持ROR在2-3℃/30s',
        },
        {
          id: `rem_${b.id}_2`,
          batchReviewId: `review_${b.id}`,
          priority: 2,
          content: '发展率目标22-23%，发展时间1分50秒左右',
        },
        {
          id: `rem_${b.id}_3`,
          batchReviewId: `review_${b.id}`,
          priority: 3,
          content: '下豆温度尝试提高2-3℃，注意观察豆色变化',
        },
      ],
    })
  })

// ---------- 辅助：通过 purchaseBatchId 获取 GreenBean ----------
export function getGreenBeanByBatch(batch: RoastingBatch): GreenBean | undefined {
  const pb = mockPurchaseBatches.find(p => p.id === batch.purchaseBatchId)
  if (!pb) return undefined
  return mockGreenBeans.find(g => g.id === pb.greenBeanId)
}

export function getGreenBeanById(greenBeanId: string): GreenBean | undefined {
  return mockGreenBeans.find(g => g.id === greenBeanId)
}

// ---------- 年度仪表盘数据 ----------

export function getDashboardData(year: number): DashboardYearData {
  const yearBatches = mockRoastingBatches.filter(b => {
    const d = new Date(b.actualDate || b.plannedDate!)
    return d.getFullYear() === year
  })
  const completedBatches = yearBatches.filter(b => b.status === 'completed')

  const monthlyRoasts = Array.from({ length: 12 }, (_, i) => ({
    month: i + 1,
    count: randInt(i > new Date().getMonth() ? 0 : 2, 15),
  }))

  // 豆款数：生豆档案 ID 去重
  const beanProfileIds = new Set<string>()
  completedBatches.forEach(b => {
    const pb = mockPurchaseBatches.find(p => p.id === b.purchaseBatchId)
    if (pb) beanProfileIds.add(pb.greenBeanId)
  })

  // 豆种分布
  const varietyMap = new Map<string, number>()
  completedBatches.forEach(b => {
    const gb = getGreenBeanByBatch(b)
    const v = gb?.variety || '其他'
    varietyMap.set(v, (varietyMap.get(v) || 0) + 1)
  })
  const varietyDist = [...varietyMap.entries()].map(([name, count]) => ({ name, count }))

  // 产区分布
  const regionMap = new Map<string, number>()
  completedBatches.forEach(b => {
    const gb = getGreenBeanByBatch(b)
    const r = gb?.region || '其他'
    regionMap.set(r, (regionMap.get(r) || 0) + 1)
  })
  const regionDist = [...regionMap.entries()].map(([name, count]) => ({ name, count }))

  return {
    year,
    totalRoasts: completedBatches.length,
    totalRoastedBeanProfiles: beanProfileIds.size,
    totalInputWeight: completedBatches.reduce((s, b) => s + b.beanWeightIn, 0),
    avgWeightLossRate: completedBatches.length > 0
      ? parseFloat((completedBatches
          .filter(b => b.weightLossRate !== undefined)
          .reduce((s, b) => s + (b.weightLossRate || 0), 0) /
          completedBatches.filter(b => b.weightLossRate !== undefined).length || 0
        ).toFixed(1))
      : 0,
    monthlyRoasts,
    varietyDistribution: varietyDist,
    regionDistribution: regionDist,
    pendingBatches: yearBatches.filter(b => b.status === 'planned').slice(0, 5),
    recentBatches: completedBatches.slice(-8).reverse(),
  }
}

// ---------- 标准词表 ----------

export const mockTerms: StandardTerm[] = [
  // 风味描述
  ...flavorTags.map(f => ({ id: `term_flavor_${f}`, category: 'flavor' as const, value: f, active: true, usageCount: randInt(1, 20) })),
  // 缺陷描述
  { id: 'term_rd', category: 'defect' as const, value: '烘焙不均', active: true, usageCount: 3 },
  { id: 'term_be', category: 'defect' as const, value: '烘焙不足', active: true, usageCount: 2 },
  { id: 'term_sc', category: 'defect' as const, value: '焦苦味', active: true, usageCount: 5 },
  { id: 'term_gr', category: 'defect' as const, value: '青草味', active: false, usageCount: 0 },
  // 烘焙度
  ...roastLevels.map(r => ({ id: `term_roast_${r}`, category: 'roast_level' as const, value: r, active: true, usageCount: randInt(2, 15) })),
  // 处理法
  ...['水洗', '日晒', '蜜处理', '厌氧发酵', '半水洗', '其他'].map(p => ({ id: `term_process_${p}`, category: 'process' as const, value: p, active: true, usageCount: randInt(2, 12) })),
  // 冲煮方式
  ...brewMethods.map(m => ({ id: `term_brew_${m}`, category: 'brew_method' as const, value: m, active: true, usageCount: randInt(1, 10) })),
  // 饮用温度
  ...drinkTemps.map(t => ({ id: `term_temp_${t}`, category: 'drink_temperature' as const, value: t, active: true, usageCount: randInt(1, 8) })),
  // 饮用形式
  ...drinkForms.map(f => ({ id: `term_form_${f}`, category: 'drink_form' as const, value: f, active: true, usageCount: randInt(1, 8) })),
  // 评价者类型
  ...['烘焙师', '同事', '顾客'].map(t => ({ id: `term_eval_${t}`, category: 'evaluator_type' as const, value: t, active: true, usageCount: randInt(2, 15) })),
]

// ---------- 模拟请求层 ----------

type MockConfig = {
  delay?: number
  failRate?: number
}

const config: MockConfig = {
  delay: 300,
  failRate: 0,
}

export function setMockConfig(cfg: Partial<MockConfig>): void {
  Object.assign(config, cfg)
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function mockRequest<T>(
  data: T,
  opts?: { empty?: boolean; fail?: boolean }
): Promise<T> {
  await delay(config.delay + Math.random() * 200)

  if (opts?.fail) {
    throw new Error('模拟请求失败')
  }

  if (opts?.empty) {
    if (Array.isArray(data)) return [] as unknown as T
    return null as unknown as T
  }

  return data
}

// ---------- API ----------

export async function apiGetDashboard(year: number): Promise<DashboardYearData> {
  return mockRequest(getDashboardData(year))
}

export async function apiGetGreenBeans(filter?: Record<string, unknown>): Promise<GreenBean[]> {
  return mockRequest([...mockGreenBeans])
}

export async function apiGetPurchaseBatches(greenBeanId?: string): Promise<PurchaseBatch[]> {
  const list = greenBeanId
    ? mockPurchaseBatches.filter(p => p.greenBeanId === greenBeanId)
    : [...mockPurchaseBatches]
  return mockRequest(list)
}

export async function apiGetRoastingBatches(filter?: Record<string, unknown>): Promise<{ items: RoastingBatch[]; total: number }> {
  const items = [...mockRoastingBatches]
  return mockRequest({ items, total: items.length })
}

export async function apiGetCurve(batchId: string): Promise<RoastingCurve | null> {
  const curve = mockCurves.find(c => c.roastingBatchId === batchId)
  return mockRequest(curve || null)
}

export async function apiGetCurves(batchIds: string[]): Promise<RoastingCurve[]> {
  const curves = mockCurves.filter(c => batchIds.includes(c.roastingBatchId))
  return mockRequest(curves)
}

export async function apiGetQuestionnaires(): Promise<Questionnaire[]> {
  return mockRequest([...mockQuestionnaires])
}

export async function apiGetQuestionnaire(id: string): Promise<Questionnaire | null> {
  return mockRequest(mockQuestionnaires.find(q => q.id === id) || null)
}

export async function apiGetQuestionnaireByCode(code: string): Promise<Questionnaire | null> {
  return mockRequest(mockQuestionnaires.find(q => q.shareCode === code) || null)
}

export async function apiGetEvaluations(questionnaireId: string): Promise<CuppingEvaluation[]> {
  return mockRequest(mockEvaluations.filter(e => e.questionnaireId === questionnaireId))
}

export async function apiGetReview(batchId: string): Promise<BatchReview | null> {
  return mockRequest(mockReviews.find(r => r.roastingBatchId === batchId) || null)
}

export async function apiGetReviews(): Promise<BatchReview[]> {
  return mockRequest([...mockReviews])
}

export async function apiGetTerms(): Promise<StandardTerm[]> {
  return mockRequest([...mockTerms])
}

export async function apiCreateGreenBean(data: Partial<GreenBean>): Promise<GreenBean> {
  const bean: GreenBean = {
    id: uid('gb'),
    name: data.name || '新豆款',
    variety: data.variety || '铁皮卡',
    process: data.process || '水洗',
    region: data.region || '',
    country: data.country || '',
    brand: data.brand,
    season: data.season,
    vendorFlavorDescription: data.vendorFlavorDescription,
    firstCreated: new Date().toISOString().split('T')[0],
    ...data,
  }
  mockGreenBeans.push(bean)
  return mockRequest(bean)
}

export async function apiCreatePurchaseBatch(data: Partial<PurchaseBatch>): Promise<PurchaseBatch> {
  const totalWeight = data.totalWeight || 5000
  const pricePerKg = data.pricePerKg
  const batch: PurchaseBatch = {
    id: uid('pb'),
    greenBeanId: data.greenBeanId || '',
    purchaseDate: data.purchaseDate || new Date().toISOString().split('T')[0],
    totalWeight,
    pricePerKg,
    totalPrice: pricePerKg ? parseFloat((totalWeight / 1000 * pricePerKg).toFixed(2)) : undefined,
    remainingStock: totalWeight,
    adjustments: [],
    ...data,
  }
  mockPurchaseBatches.push(batch)
  return mockRequest(batch)
}

export async function apiCreateRoastingBatch(data: Partial<RoastingBatch>): Promise<RoastingBatch> {
  const batch: RoastingBatch = {
    id: uid('rb'),
    purchaseBatchId: data.purchaseBatchId || '',
    beanWeightIn: data.beanWeightIn || 500,
    status: 'planned',
    curveStatus: 'none',
    evaluationStatus: 'none',
    reviewStatus: 'none',
    colorTag: BATCH_COLORS[Math.floor(Math.random() * BATCH_COLORS.length)],
    ...data,
  }
  mockRoastingBatches.unshift(batch)
  return mockRequest(batch)
}

/** 标记烘焙完成 - 不再自动计算出豆量，需要用户确认投豆量和实际时间 */
export async function apiCompleteBatch(
  batchId: string,
  confirmedWeightIn?: number,
  confirmedActualDate?: string,
): Promise<RoastingBatch> {
  const b = mockRoastingBatches.find(b => b.id === batchId)
  if (b) {
    b.status = 'completed'
    b.actualDate = confirmedActualDate || new Date().toISOString().split('T')[0]
    if (confirmedWeightIn) {
      b.beanWeightIn = confirmedWeightIn
    }
    // 出豆量不再自动计算 — 后续补录
  }
  return mockRequest(b!)
}

/** 补录出豆量 */
export async function apiUpdateWeightOut(batchId: string, weightOut: number): Promise<RoastingBatch> {
  const b = mockRoastingBatches.find(b => b.id === batchId)
  if (b) {
    b.beanWeightOut = weightOut
    if (b.beanWeightIn > 0) {
      b.weightLossRate = parseFloat(((1 - weightOut / b.beanWeightIn) * 100).toFixed(1))
    }
  }
  return mockRequest(b!)
}

export async function apiCreateQuestionnaire(batchId: string): Promise<Questionnaire> {
  const q: Questionnaire = {
    id: uid('q'),
    roastingBatchId: batchId,
    shareCode: Math.random().toString(36).slice(2, 10),
    status: 'open',
    createdAt: new Date().toISOString().split('T')[0],
    submissionCount: 0,
  }
  mockQuestionnaires.push(q)
  const batch = mockRoastingBatches.find(b => b.id === batchId)
  if (batch) batch.evaluationStatus = 'open'
  return mockRequest(q)
}

export async function apiCloseQuestionnaire(id: string): Promise<Questionnaire> {
  const q = mockQuestionnaires.find(q => q.id === id)
  if (q) {
    q.status = 'closed'
    q.closedAt = new Date().toISOString().split('T')[0]
  }
  return mockRequest(q!)
}

export async function apiSubmitEvaluation(data: Partial<CuppingEvaluation>): Promise<CuppingEvaluation> {
  const eval_: CuppingEvaluation = {
    id: uid('eval'),
    evaluatorName: data.evaluatorName || '匿名',
    evaluatorType: data.evaluatorType || 'customer',
    brewMethod: data.brewMethod || '手冲',
    drinkTemperature: data.drinkTemperature || '热饮',
    drinkForm: data.drinkForm || '黑咖啡',
    dryFragrance: data.dryFragrance ?? 0,
    wetAroma: data.wetAroma ?? 0,
    acidity: data.acidity ?? 0,
    sweetness: data.sweetness ?? 0,
    bitterness: data.bitterness ?? 0,
    aftertaste: data.aftertaste ?? 0,
    overallPreference: data.overallPreference || 3,
    flavorNotes: data.flavorNotes || [],
    submittedAt: new Date().toISOString().split('T')[0],
    ...data,
  }
  mockEvaluations.push(eval_)
  const q = mockQuestionnaires.find(q => q.id === data.questionnaireId)
  if (q) q.submissionCount++
  return mockRequest(eval_)
}

export async function apiSaveReview(data: Partial<BatchReview>): Promise<BatchReview> {
  const existing = mockReviews.find(r => r.roastingBatchId === data.roastingBatchId)
  if (existing) {
    Object.assign(existing, data, {
      id: existing.id,
      roastingBatchId: existing.roastingBatchId,
    })
    return mockRequest(existing)
  }
  const review: BatchReview = {
    id: uid('review'),
    personalReview: '',
    nextBatchSuggestions: '',
    reminders: [],
    ...data,
  } as BatchReview
  mockReviews.push(review)
  return mockRequest(review)
}

export async function apiUpdateTerm(id: string, data: Partial<StandardTerm>): Promise<StandardTerm> {
  const term = mockTerms.find(t => t.id === id)
  if (term) Object.assign(term, data)
  return mockRequest(term!)
}
