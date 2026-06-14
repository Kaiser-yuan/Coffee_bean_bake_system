// ============================================================
// 咖啡烘焙数据分析系统 - TypeScript 类型定义
// This file serves as the shared contract between frontend mock
// and future backend APIs.
// ============================================================

// ---------- 枚举与常量 ----------

export type BeanProcess = '水洗' | '日晒' | '蜜处理' | '厌氧发酵' | '半水洗' | '其他'
export type RoastLevel = '浅烘' | '中浅烘' | '中烘' | '中深烘' | '深烘'
export type BatchStatus = 'planned' | 'completed' | 'voided'
export type CurveStatus = 'none' | 'parsed' | 'error'
export type EvaluationStatus = 'none' | 'open' | 'closed'
export type ReviewStatus = 'none' | 'draft' | 'done'
export type QuestionnaireStatus = 'open' | 'closed' | 'expired'

export type BrewMethod = '杯测' | '手冲' | '意式' | '奶咖' | '其他'
export type DrinkTemperature = '热饮' | '冷饮'
export type DrinkForm = '黑咖啡' | '加奶' | '其他'

/** 资料完整度：与实际烘焙是否发生分开 */
export type BatchDataCompleteness = {
  missingWeightOut: boolean
  missingCSV: boolean
  missingEvaluation: boolean
  missingReview: boolean
  isComplete: boolean
}

export const BEAN_PROCESSES: BeanProcess[] = ['水洗', '日晒', '蜜处理', '厌氧发酵', '半水洗', '其他']
export const ROAST_LEVELS: RoastLevel[] = ['浅烘', '中浅烘', '中烘', '中深烘', '深烘']
export const BATCH_STATUS_LABELS: Record<BatchStatus, string> = { planned: '待烘', completed: '已完成', voided: '已作废' }
export const CURVE_STATUS_LABELS: Record<CurveStatus, string> = { none: '无曲线', parsed: '已解析', error: '解析失败' }
export const EVAL_STATUS_LABELS: Record<EvaluationStatus, string> = { none: '未发起', open: '进行中', closed: '已关闭' }

export const BREW_METHODS: BrewMethod[] = ['杯测', '手冲', '意式', '奶咖', '其他']
export const DRINK_TEMPERATURES: DrinkTemperature[] = ['热饮', '冷饮']
export const DRINK_FORMS: DrinkForm[] = ['黑咖啡', '加奶', '其他']
export const EVALUATOR_TYPES = ['roaster', 'colleague', 'customer'] as const

export const REGION_OPTIONS = [
  '埃塞俄比亚', '肯尼亚', '哥伦比亚', '巴西', '危地马拉',
  '哥斯达黎加', '巴拿马', '印度尼西亚', '云南', '卢旺达',
  '布隆迪', '洪都拉斯', '萨尔瓦多', '秘鲁', '坦桑尼亚',
]

export const VARIETY_OPTIONS = [
  '铁皮卡', '波旁', '卡杜拉', '卡杜艾', '瑰夏', 'SL28', 'SL34',
  '帕卡马拉', '埃塞原生种', '卡蒂姆', '新世界', '黄波旁',
]

export const FLAVOR_TAGS = [
  '花香', '柑橘', '莓果', '核果', '巧克力', '坚果', '焦糖',
  '香料', '草本', '发酵', '酒香', '烟熏', '茶感', '热带水果',
]

// ---------- 数据对象 ----------

export interface GreenBean {
  id: string
  name: string
  variety: string
  process: BeanProcess
  region: string
  country: string
  farm?: string
  elevation?: string
  /** 品牌 */
  brand?: string
  /** 产季 */
  season?: string
  /** 豆商风味描述 */
  vendorFlavorDescription?: string
  firstCreated: string // ISO date
}

export interface PurchaseBatch {
  id: string
  greenBeanId: string
  purchaseDate: string
  totalWeight: number // g
  moistureContent?: number // percentage
  /** 采购单价 (元/kg) */
  pricePerKg?: number
  /** 采购总价 (元) */
  totalPrice?: number
  supplier?: string
  lotNumber?: string
  notes?: string
  /** 剩余库存 — 由后端聚合计算，前端只读展示 */
  remainingStock: number
  adjustments: InventoryAdjustment[]
}

export interface InventoryAdjustment {
  id: string
  purchaseBatchId: string
  date: string
  amount: number // g, positive for add, negative for deduct
  reason: string
  notes?: string
}

export interface RoastingBatch {
  id: string
  purchaseBatchId: string
  /** 通过 purchaseBatchId -> PurchaseBatch.greenBeanId 关联，不冗余存储 */
  plannedDate?: string
  actualDate?: string
  /** 实际投豆量，标记完成时确认 */
  beanWeightIn: number // g
  /** 出豆量仅在实际称重后补录 */
  beanWeightOut?: number // g
  totalTime?: number // seconds
  developmentTime?: number // seconds
  /** 失重率仅在投豆量和出豆量都存在时计算 */
  weightLossRate?: number // percentage, computed
  developmentRatio?: number // percentage, computed
  roastLevel?: RoastLevel
  targetDescription?: string
  status: BatchStatus
  curveStatus: CurveStatus
  evaluationStatus: EvaluationStatus
  reviewStatus: ReviewStatus
  csvFileName?: string
  csvUploadTime?: string
  colorTag?: string // hex color for consistent identification
}

export type CurveAlignBy =
  | 'charge'
  | 'yellowing'
  | 'first_crack_start'
  | 'drop'

export interface CurvePoint {
  /** 采样序号 */
  sampleIndex: number
  /** 经过时间（秒），从入豆开始 */
  elapsedSeconds: number
  /** 豆温 BT (°C) */
  beanTempCelsius?: number
  /** 环境温度 ET (°C) */
  environmentTempCelsius?: number
  /** 升温率 RoR (°C/分钟) */
  rorCelsiusPerMinute?: number
  /** 目标温度 SV (°C) */
  targetTempCelsius?: number
  /** 火力模式 */
  heatingPowerMode?: string
  /** 火力百分比 */
  heatingPowerPercent?: number
  /** 风门百分比 */
  smokeDamperPercent?: number
  /** 滚筒转速百分比 */
  rollerPercent?: number
  /** 电源状态 */
  powerStatus?: string
}

// Backward compatibility aliases
export interface CurvePointCompat {
  time: number
  beanTemp?: number
  envTemp?: number
  ror?: number
  gas?: number
  airflow?: number
  drumSpeed?: number
}

export interface CurveEvent {
  time: number
  type: 'charge' | 'turning_point' | 'yellowing' | 'first_crack_start' | 'first_crack_end' | 'second_crack_start' | 'second_crack_end' | 'drop'
  label: string
  /** 事件发生时的豆温 */
  beanTemp?: number
}

export interface CurveComparisonPoint extends CurvePoint {
  /** 对齐后时间（秒），由后端或图表适配层计算 */
  alignedSeconds: number
}

export interface CurveMetricDifference {
  metric: string
  baseValue?: number
  comparisonValue?: number
  difference?: number
  unit?: string
  calculationRule?: string
  label?: string
}

export interface CurveComparisonWarning {
  code: string
  severity: 'info' | 'warning'
  batchId: string
  message: string
}

export interface RoastingCurve {
  id: string
  roastingBatchId: string
  points: CurvePoint[]
  events: CurveEvent[]
  parsedAt: string
  csvFileName: string
}

export interface Questionnaire {
  id: string
  roastingBatchId: string
  shareCode: string // unique code for public URL
  status: QuestionnaireStatus
  createdAt: string
  expiresAt?: string
  closedAt?: string
  submissionCount: number
}

export interface CuppingEvaluation {
  id: string
  questionnaireId: string
  roastingBatchId: string
  evaluatorName: string
  evaluatorType: 'roaster' | 'colleague' | 'customer'
  /** 冲煮方式 */
  brewMethod: BrewMethod
  /** 饮用温度 */
  drinkTemperature: DrinkTemperature
  /** 饮用形式 */
  drinkForm: DrinkForm
  /** 以下维度 1-5 分，0 表示"未评价/不确定" */
  dryFragrance: number
  wetAroma: number
  acidity: number // 强度
  sweetness: number
  bitterness: number // 强度
  aftertaste: number
  /** 综合喜好必须评分 */
  overallPreference: number // 1-5, always required
  flavorNotes: string[]
  freeNotes?: string
  /** 养豆天数，由系统根据评价时间和烘焙时间自动计算 */
  beanAgeDays?: number
  submittedAt: string
}

export interface BatchReview {
  id: string
  roastingBatchId: string
  personalReview: string
  personalReviewAt?: string
  evaluationSummary?: string
  comprehensiveReview?: string
  comprehensiveReviewAt?: string
  nextBatchSuggestions: string
  reminders: Reminder[]
}

export interface Reminder {
  id: string
  batchReviewId: string
  priority: 1 | 2 | 3
  content: string
  carriedToBatchId?: string
  /** 提醒来源追溯 */
  sourceReviewId?: string
  sourceRoastingBatchId?: string
  targetRoastingBatchId?: string
}

export interface StandardTerm {
  id: string
  category: 'flavor' | 'defect' | 'roast_level' | 'process' | 'variety' | 'region' | 'brew_method' | 'drink_temperature' | 'drink_form' | 'evaluator_type' | 'supplier'
  value: string
  active: boolean
  usageCount: number
}

// ---------- API 请求/响应 ----------

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export interface BatchFilter {
  dateRange?: [string, string]
  greenBeanName?: string
  variety?: string
  process?: BeanProcess
  region?: string
  purchaseBatchId?: string
  status?: BatchStatus
  hasCurve?: boolean
  hasEvaluation?: boolean
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  page?: number
  pageSize?: number
}

export interface GreenBeanFilter {
  search?: string
  variety?: string
  process?: BeanProcess
  region?: string
  stockStatus?: 'in_stock' | 'low' | 'depleted'
}

export interface DashboardYearData {
  year: number
  totalRoasts: number
  /** 已烘焙豆款数（生豆档案 ID 去重） */
  totalRoastedBeanProfiles: number
  totalInputWeight: number
  avgWeightLossRate: number
  monthlyRoasts: { month: number; count: number }[]
  varietyDistribution: { name: string; count: number }[]
  regionDistribution: { name: string; count: number }[]
  pendingBatches: RoastingBatch[]
  recentBatches: RoastingBatch[]
}
