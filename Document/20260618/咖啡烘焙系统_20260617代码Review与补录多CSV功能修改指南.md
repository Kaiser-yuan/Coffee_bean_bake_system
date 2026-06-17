# 咖啡烘焙系统：20260617 代码 Review 与补录、多 CSV 功能修改指南

> 日期：2026-06-17  
> Review 代码版本：GitHub `master`，commit `971c598`  
> 文档目标：先指出当前代码仍需修改的问题，再给出“建立烘焙批次中的多 CSV 生成”和“历史数据补录中心”的前后端实现指南与验收标准。

## 1. 本次 Review 结论

昨晚的代码已经修复了多个前一版 P0 问题：

- 后端 `Dockerfile` 已调整为先复制 `app/` 再 `pip install .`。
- `pyproject.toml` 已补 `packages = ["app"]`。
- 已新增 `backend/alembic.ini` 和首个迁移文件。
- 问卷创建入口已迁移到 `POST /api/v1/roasting-batches/{batch_id}/questionnaires`。
- 烘焙批次创建、完成、重开、作废后已重新加载详情，降低 `MissingGreenlet` 风险。
- 注册接口已限制为首次初始化用户，且首个用户自动成为管理员。
- 曲线 AUC 和 warnings 已进入曲线响应。
- 前端新增了 `api/`、`adapters/`、`auth store`、登录页和部分真实 API 接入。

当前仍有几个需要先修的问题。

## 2. 当前代码修改意见

### P0-1：首个 Alembic 迁移不能使用 `Base.metadata.create_all/drop_all`

当前文件：

```text
backend/alembic/versions/20260616_0001_initial_schema.py
```

当前实现：

```python
def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
```

问题：

- 这不是标准 Alembic 迁移，后续字段变更、索引变更、约束变更难以追踪。
- `drop_all()` 的 downgrade 风险过大，会直接删除所有表。
- 审查迁移时看不到具体建了哪些表、外键和索引。
- 服务器部署后，数据库结构演进会变得不可控。

修改建议：

- 使用 `alembic revision --autogenerate` 生成明确的 `op.create_table()`、`op.create_index()`、`op.create_foreign_key()`。
- 人工检查生成结果。
- 不要在迁移文件里调用 `Base.metadata.create_all()`。
- downgrade 可以保守处理，至少要按依赖顺序 `op.drop_table()`，不要直接 `drop_all()`。

验收标准：

- [ ] 迁移文件中不再出现 `Base.metadata.create_all`。
- [ ] 迁移文件中能看到核心表的 `op.create_table`。
- [ ] `alembic upgrade head` 可以建表。
- [ ] `alembic downgrade base` 不误删非本项目表。

### P0-2：内部数据接口仍有未加认证的入口

当前至少以下接口没有声明 `CurrentUserDep`：

```text
GET /api/v1/green-beans/matches
GET /api/v1/green-beans/tree
```

问题：

- 生豆档案、采购批次、库存和烘焙记录属于内部数据。
- 部署公网后不应匿名访问。
- 公开接口应该只限评价问卷读取和提交。

修改建议：

```python
async def get_green_bean_tree(
    ...,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
```

验收标准：

- [ ] 未登录访问 `/api/v1/green-beans/tree` 返回 401。
- [ ] 登录后可正常访问。
- [ ] 公开问卷接口仍可匿名访问。

### P1-1：前端仍处于半真实、半 Mock 状态

当前真实 API 已开始接入，但大量页面仍直接读取 `frontend/src/mock`：

```text
Dashboard.vue
RoastingBatchList.vue
CurveAnalysis.vue
EvaluationManagement.vue
EvaluationDetail.vue
BatchReview.vue
PublicQuestionnaire.vue
stores/roasting.ts
```

问题：

- 登录、生豆管理可能走真实 API。
- 烘焙分析、曲线、评价、复盘仍主要是 mock。
- 联调时容易误判，以为后端已跑通，实际页面没有访问后端。

修改建议：

- 保留 demo mode，但必须做成统一分支。
- 每个模块只有一个 service 层，例如：

```text
frontend/src/services/greenBeanService.ts
frontend/src/services/roastingBatchService.ts
frontend/src/services/curveService.ts
frontend/src/services/questionnaireService.ts
frontend/src/services/reviewService.ts
```

- 页面不直接 import `mock`，只调用 service。
- service 内部根据 `isDemoMode` 选择 mock 或真实 API。

验收标准：

- [ ] 页面组件不直接 import `../mock`。
- [ ] `VITE_DEMO_MODE=false` 时，所有核心页面请求真实后端。
- [ ] AppLayout 显示“真实 API”时，页面数据全部来自后端。

### P1-2：`VITE_DEMO_MODE` 默认值容易造成联调误判

当前：

```ts
export const isDemoMode = import.meta.env.VITE_DEMO_MODE !== 'false'
```

没有配置时默认是 demo mode。

问题：

- 开发者忘记写 `.env.local` 时，登录守卫不会启用。
- 页面可能继续读 mock。
- 联调时难以判断是否真的调用后端。

修改建议：

保留默认 demo 可以，但必须在页面明显提示，并在联调文档中固定要求：

```env
VITE_DEMO_MODE=false
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

验收标准：

- [ ] `.env.example` 明确给出 demo 和 real 两套配置。
- [ ] 真实 API 模式下未登录会跳转 `/login`。
- [ ] 控制台或页面角标明确显示当前模式。

### P1-3：登录页默认密码不应写死为 `admin123`

当前 `Login.vue` 中有默认值：

```ts
const password = ref('admin123')
```

问题：

- 容易误提交到正式环境。
- 用户会误以为系统内置默认密码。

修改建议：

```ts
const password = ref('')
```

验收标准：

- [ ] 登录页不预填密码。
- [ ] README 或本地指南说明如何初始化第一个管理员。

### P1-4：批量 CSV 和历史补录所需数据字段尚未建模

当前 `roasting_batches` 没有以下字段：

```text
entry_mode
inventory_effective
roasted_at_source
bulk_import_group_id
source_note
```

也没有批量导入任务表：

```text
bulk_import_jobs
```

问题：

- 无法区分普通计划、单锅已完成录入、多 CSV 生成、历史补录。
- 无法区分是否影响库存。
- 无法追踪同一次批量上传的多个 CSV。
- 后续撤销、复盘、排查重复导入会困难。

修改建议见后续功能设计章节。

## 3. 功能定位：两个入口，同一套底层能力

需要保留两个入口：

```text
入口 A：建立烘焙批次
入口 B：历史数据补录
```

但它们底层共用同一套能力：

```text
CSV 解析
→ 时间推断
→ 预览确认
→ 创建 roasting_batch
→ 保存 curve_file
→ 生成 roasting_curve
→ 可选扣库存
→ 写入导入分组
```

区别在默认参数和业务语义。

| 场景 | 入口 | 默认状态 | 默认影响库存 | 是否必须选择采购批次 |
|---|---|---|---|---|
| 单锅计划 | 建立烘焙批次 | planned | 否 | 是 |
| 单锅已完成录入 | 建立烘焙批次 | completed | 是 | 是 |
| 多 CSV 生成烘焙批次 | 建立烘焙批次 | completed | 是 | 是 |
| 历史补录 | 历史数据补录 | completed / archived | 否 | 推荐，但可先补建 |

结论：

- “最近刚烘完的一批 CSV”迁移到建立烘焙批次流程。
- “很久以前的数据归档”保留为历史补录中心。

## 4. 数据模型修改建议

### 4.1 修改 `roasting_batches`

新增字段：

```text
entry_mode varchar(32) not null default 'manual_plan'
inventory_effective boolean not null default true
roasted_at_source varchar(32) null
bulk_import_group_id uuid null
source_note text null
```

字段含义：

```text
entry_mode:
  manual_plan          手动创建未来烘焙计划
  manual_completed     手动录入已完成烘焙
  csv_bulk_import      从当前采购批次批量 CSV 生成
  historical_backfill  历史数据补录

inventory_effective:
  true   影响当前库存
  false  仅归档，不影响当前库存

roasted_at_source:
  csv_content
  filename
  file_last_modified
  manual
  upload_order

bulk_import_group_id:
  同一次上传多个 CSV 的分组 ID
```

注意：

- `calculate_remaining_stock()` 必须只统计 `status='completed'` 且 `inventory_effective=true` 的烘焙批次。
- 重开或作废时，也只有 `inventory_effective=true` 才写返还库存流水。

### 4.2 新增 `bulk_import_jobs`

建议新增表：

```text
bulk_import_jobs
```

字段：

```text
id uuid primary key
purchase_batch_id uuid null
mode varchar(32) not null
status varchar(32) not null
file_count int not null
success_count int not null default 0
failed_count int not null default 0
default_input_weight_grams int null
inventory_effective_default boolean not null
created_by uuid null
created_at timestamptz not null
committed_at timestamptz null
notes text null
```

`mode`：

```text
csv_bulk_import
historical_backfill
```

`status`：

```text
previewed
committed
failed
cancelled
```

### 4.3 新增 `bulk_import_items`

建议新增表：

```text
bulk_import_items
```

字段：

```text
id uuid primary key
job_id uuid not null
original_filename varchar(255) not null
file_hash varchar(64) not null
file_size_bytes int not null
client_last_modified_at timestamptz null
inferred_roasted_at timestamptz null
roasted_at_source varchar(32) null
display_order int not null
parse_status varchar(32) not null
parse_error_message text null
warnings jsonb null
preview_summary jsonb null
roasting_batch_id uuid null
curve_file_id uuid null
created_at timestamptz not null
```

作用：

- 支持预览后再提交。
- 支持每个 CSV 独立失败，不影响其它文件。
- 支持去重。
- 支持以后回看某次批量导入。

## 5. 时间推断规则

不要只依赖文件创建时间。浏览器上传通常只能提供 `lastModified`，服务器拿到的是上传文件流，不会可靠保留本地创建时间。

推荐优先级：

```text
1. CSV 内容中的烘焙时间，如果 Kaleido 文件能解析出来
2. 文件名日期，例如 260530_9.csv
3. 浏览器上传时传入的 file.lastModified
4. 用户在预览页手动选择的日期
5. 用户指定日期 + 上传顺序自动分配时间
```

文件名 `260530_9.csv` 的解析建议：

```text
26 -> 2026
05 -> 05 月
30 -> 30 日
_9 -> 第 9 锅或顺序号，不直接等于 9 点
```

如果只有日期没有时间：

- 允许用户填写“当天第一锅时间”，例如 `09:30`。
- 后续按 CSV 排序和总时长自动推断下一锅时间。
- 或者全部先设为同一天，用户在预览表中手动调整。

必须保存：

```text
roasted_at
roasted_at_source
```

## 6. 后端接口设计

### 6.1 当前采购批次下：多 CSV 生成烘焙批次

入口语义：

```text
采购批次详情
→ 建立烘焙批次
→ 批量 CSV 生成
```

#### 预览接口

```text
POST /api/v1/purchase-batches/{purchase_batch_id}/roasting-batches/bulk-preview
Content-Type: multipart/form-data
```

请求字段：

```text
files: File[]
default_input_weight_grams: number
inventory_effective_default: boolean = true
default_roast_date: string optional
first_roast_time: string optional
time_inference_strategy: csv_content | filename | file_last_modified | manual | upload_order
```

返回：

```json
{
  "job_id": "uuid",
  "purchase_batch_id": "uuid",
  "mode": "csv_bulk_import",
  "inventory_effective_default": true,
  "available_stock_grams": 3000,
  "total_planned_input_grams": 1650,
  "items": [
    {
      "item_id": "uuid",
      "filename": "260530_9.csv",
      "file_hash": "sha256",
      "inferred_roasted_at": "2026-05-30T09:30:00+08:00",
      "roasted_at_source": "filename",
      "input_weight_grams": 550,
      "inventory_effective": true,
      "parse_status": "parsed",
      "summary": {
        "total_time_seconds": 610,
        "turning_point_seconds": 75,
        "yellowing_seconds": 290,
        "first_crack_start_seconds": 480,
        "development_ratio_percent": 18.7,
        "auc_bt_above_100": 12345.6
      },
      "warnings": []
    }
  ],
  "blocking_errors": []
}
```

预览阶段不创建 `roasting_batches`，只创建导入 job 和 item，或者只返回临时 token。第一阶段建议落库 job，便于失败排查。

#### 提交接口

```text
POST /api/v1/purchase-batches/{purchase_batch_id}/roasting-batches/bulk-commit
Content-Type: application/json
```

请求：

```json
{
  "job_id": "uuid",
  "items": [
    {
      "item_id": "uuid",
      "roasted_at": "2026-05-30T09:30:00+08:00",
      "actual_input_weight_grams": 550,
      "output_weight_grams": 465,
      "inventory_effective": true,
      "source_note": "读卡器批量导入"
    }
  ]
}
```

提交逻辑：

```text
开启事务
→ 锁定 purchase_batch
→ 检查库存是否足够
→ 对每个 item 创建 completed roasting_batch
→ 保存 curve_file
→ 调用 parse_and_activate_curve
→ 如果 inventory_effective=true，写 roast_consumption 流水
→ 更新 bulk_import_job 状态
→ 返回导入结果
```

验收标准：

- [ ] 一次上传 2 个 CSV，生成 2 个 completed 烘焙批次。
- [ ] 每个批次都有独立 curve_file 和 active curve。
- [ ] 默认扣减库存。
- [ ] 总扣减量等于每行实际投豆量之和。
- [ ] 文件重复上传时能识别并提示。
- [ ] 某个 CSV 解析失败时，不影响其它文件预览。
- [ ] commit 可以防重复提交，同一个 job 不能重复生成批次。

### 6.2 历史数据补录中心

入口语义：

```text
数据管理 / 系统工具
→ 历史数据补录
```

后端可以复用同一套 preview/commit 服务，但接口路径建议独立：

```text
POST /api/v1/backfills/roasting-csv/preview
POST /api/v1/backfills/roasting-csv/commit
```

历史补录允许：

- 先选择已有采购批次。
- 或先创建历史生豆和历史采购批次。
- 默认 `inventory_effective=false`。
- 允许信息不完整，但必须标记数据来源。

历史补录 commit 默认：

```text
entry_mode = historical_backfill
inventory_effective = false
status = completed
```

验收标准：

- [ ] 历史补录默认不扣当前库存。
- [ ] 用户手动打开“影响库存”后才扣库存。
- [ ] 补录数据能进入曲线对比。
- [ ] 补录数据能进入复盘。
- [ ] 可以从批次详情看出该记录是历史补录。

## 7. 后端服务层拆分建议

不要把多 CSV 逻辑直接写在 API 文件里。建议新增：

```text
backend/app/services/bulk_import.py
backend/app/repositories/bulk_imports.py
backend/app/api/v1/bulk_imports.py
backend/app/api/v1/backfills.py
```

核心服务函数：

```python
async def preview_roast_csv_import(...)
async def commit_roast_csv_import(...)
def infer_roasted_at(...)
def detect_duplicate_curve_file(...)
def build_roasting_batch_from_import_item(...)
```

库存必须复用现有：

```python
lock_purchase_batch()
calculate_remaining_stock()
append_inventory_ledger()
```

曲线必须复用现有：

```python
parse_kaleido_m1()
parse_and_activate_curve()
```

## 8. 前端修改指南

### 8.1 采购批次详情增加“建立烘焙批次”

当前生豆管理已经是树形结构：

```text
生豆
└── 采购批次
    └── 烘焙记录
```

建议在采购批次层级增加按钮：

```text
建立烘焙批次
```

点击后弹出模式选择：

```text
单锅计划
单锅已完成录入
批量 CSV 生成
```

### 8.2 批量 CSV 生成页面/弹窗

建议组件：

```text
frontend/src/components/roasting/BulkCsvImportDialog.vue
```

区域：

```text
上传区
默认参数区
解析预览表
错误与 warnings 区
提交确认区
```

预览表字段：

```text
文件名
推断烘焙时间
时间来源
实际投豆量
出豆量
是否扣库存
总时长
一爆开始
发展率
AUC
解析状态
warnings
```

交互要求：

- 支持一次选择多个 CSV。
- 支持拖拽上传。
- 支持按文件名或推断时间排序。
- 支持批量设置投豆量。
- 支持单行修改投豆量和烘焙时间。
- 库存不足时禁用提交。
- 提交前显示本次预计扣减库存。

### 8.3 历史补录中心

建议新增页面：

```text
frontend/src/views/HistoricalBackfill.vue
```

路由：

```text
/#/backfill
```

入口：

```text
系统设置 / 数据管理
```

页面流程：

```text
选择补录类型
→ 选择或创建生豆
→ 选择或创建采购批次
→ 上传 CSV
→ 预览
→ 确认是否影响库存
→ 提交
```

历史补录页面默认：

```text
inventory_effective = false
entry_mode = historical_backfill
```

### 8.4 前端 API 文件

新增：

```text
frontend/src/api/bulkImports.ts
frontend/src/api/backfills.ts
frontend/src/adapters/bulkImport.ts
```

接口函数：

```ts
previewPurchaseBatchCsvImport(purchaseBatchId, formData)
commitPurchaseBatchCsvImport(purchaseBatchId, body)
previewHistoricalRoastCsvBackfill(formData)
commitHistoricalRoastCsvBackfill(body)
```

### 8.5 前端类型

新增类型：

```ts
type RoastEntryMode =
  | 'manual_plan'
  | 'manual_completed'
  | 'csv_bulk_import'
  | 'historical_backfill'

type RoastedAtSource =
  | 'csv_content'
  | 'filename'
  | 'file_last_modified'
  | 'manual'
  | 'upload_order'
```

核心 DTO：

```ts
type BulkImportPreviewItemDto = {
  item_id: string
  filename: string
  file_hash: string
  inferred_roasted_at: string | null
  roasted_at_source: RoastedAtSource | null
  input_weight_grams: number | null
  output_weight_grams?: number | null
  inventory_effective: boolean
  parse_status: 'parsed' | 'failed'
  summary: Record<string, unknown>
  warnings: string[]
}
```

## 9. 与库存闭环的关系

多 CSV 生成默认影响库存：

```text
entry_mode = csv_bulk_import
inventory_effective = true
```

历史补录默认不影响库存：

```text
entry_mode = historical_backfill
inventory_effective = false
```

库存计算必须改为：

```text
remaining =
  purchase_batch.total_weight_grams
  - sum(completed roasting_batches actual_input_weight_grams where inventory_effective=true)
  + sum(inventory_adjustments.amount_grams)
```

库存流水规则：

```text
purchase_in        采购入库
roast_consumption  烘焙扣减
roast_return       重开或作废返还
adjustment         手动调整
```

如果 `inventory_effective=false`：

- 不写 `roast_consumption`。
- 不写 `roast_return`。
- 但可以在批次详情标记“仅归档，不影响库存”。

## 10. 与曲线闭环的关系

每个 CSV 必须生成独立：

```text
curve_file
roasting_curve
```

每个由 CSV 生成的烘焙批次必须能：

- 在烘焙批次列表中显示。
- 在曲线分析中打开。
- 参与多曲线对比。
- 创建问卷。
- 创建复盘。

## 11. 防重复与事务要求

### 防重复

至少用以下维度判断重复：

```text
purchase_batch_id + file_hash
```

可选增强：

```text
roasted_at + actual_input_weight_grams + file_hash
```

重复处理：

- 预览阶段提示重复。
- 默认不允许重复 commit。
- 如需覆盖，后续单独设计“替换曲线”操作，不要在批量导入中隐式覆盖。

### 事务

commit 必须是事务性操作：

```text
同一个 job 提交
→ 要么全部成功
→ 要么失败项明确标记
```

第一阶段建议：

- 预览允许部分失败。
- commit 只提交 parse 成功且用户勾选的 items。
- 对每个 item 单独记录成功/失败。
- 库存不足时整个 commit 拒绝。

## 12. 开发顺序建议

### 第一步：先修当前代码 Review 问题

1. 重写 Alembic initial migration。
2. 给内部接口补认证。
3. 清理登录页默认密码。
4. 明确真实 API 模式配置。
5. 把页面直接 import mock 的模式迁移到 service 层。

### 第二步：补数据模型

1. 给 `roasting_batches` 增加补录相关字段。
2. 新增 `bulk_import_jobs`。
3. 新增 `bulk_import_items`。
4. 生成 Alembic 迁移。

### 第三步：做后端 preview

1. 支持多文件上传。
2. 解析 CSV。
3. 推断时间。
4. 返回预览表。
5. 检查重复。
6. 检查预计库存。

### 第四步：做后端 commit

1. 锁定采购批次。
2. 检查库存。
3. 批量创建 completed 烘焙批次。
4. 保存 curve_file。
5. 创建 active curve。
6. 可选扣库存。
7. 更新 job 状态。

### 第五步：做前端批量 CSV 生成

1. 在采购批次下增加入口。
2. 做上传和预览表。
3. 支持修改每行投豆量、出豆量、时间、是否扣库存。
4. 支持提交并刷新采购批次树。

### 第六步：做历史补录中心

1. 新增独立页面。
2. 默认不影响库存。
3. 复用 preview/commit 能力。
4. 支持先创建历史采购批次。

## 13. 验收标准

### 13.1 当前代码修复验收

- [ ] `alembic` 初始迁移不再使用 `create_all/drop_all`。
- [ ] 未登录无法访问生豆树、采购批次、烘焙批次、曲线、评价管理、复盘接口。
- [ ] 登录页不预填密码。
- [ ] `VITE_DEMO_MODE=false` 时核心页面不再使用 mock。
- [ ] `python -m py_compile` 通过。
- [ ] 后端 OpenAPI 路径中问卷创建为 `/api/v1/roasting-batches/{batch_id}/questionnaires`。

### 13.2 多 CSV 生成烘焙批次验收

- [ ] 在采购批次详情中可以选择多个 CSV。
- [ ] 预览阶段不扣库存、不创建烘焙批次。
- [ ] 预览表能显示每个 CSV 的解析结果。
- [ ] 可以批量设置投豆量。
- [ ] 可以单独修改每行烘焙时间。
- [ ] 提交后自动生成多条 completed 烘焙批次。
- [ ] 每条批次都有曲线。
- [ ] 默认扣库存。
- [ ] 库存不足时拒绝提交。
- [ ] 重复文件能识别。

### 13.3 历史补录验收

- [ ] 历史补录有独立入口。
- [ ] 默认不影响库存。
- [ ] 可以选择已有采购批次。
- [ ] 可以先补建历史采购批次。
- [ ] 提交后生成的批次 `entry_mode=historical_backfill`。
- [ ] 历史补录曲线可以参与曲线对比。
- [ ] 历史补录批次可以写复盘。

### 13.4 库存验收

- [ ] 当前采购批次多 CSV 导入后，库存减少等于导入行投豆量总和。
- [ ] 历史补录默认不改变库存。
- [ ] `inventory_effective=false` 的烘焙批次不参与库存扣减。
- [ ] 重开或作废 `inventory_effective=true` 的批次会返还库存。
- [ ] 重开或作废 `inventory_effective=false` 的批次不写库存返还流水。

## 14. 本地验证说明

当前本机 Docker 尚未完全准备好时，可以先做：

```powershell
cd backend
python -m py_compile app/main.py app/api/v1/*.py app/services/*.py app/parsers/*.py
```

Docker 和 PostgreSQL 可用后，再补：

```powershell
cd backend
docker compose up -d db
alembic upgrade head
python -m uvicorn app.main:app --reload
pytest
```

前端真实 API 模式：

```env
VITE_DEMO_MODE=false
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

启动：

```powershell
cd frontend
npm install
npm run dev
```

## 15. 结论

当前代码已经从“静态前端 + 后端雏形”进入“可联调前的基础建设阶段”。下一步不要直接开始做多 CSV 页面，先把迁移、认证和 mock/service 边界修清楚。之后再实现批量 CSV 生成烘焙批次，它会成为日常工作主入口；历史补录中心保留，但作为数据归档和旧数据沉淀入口。
