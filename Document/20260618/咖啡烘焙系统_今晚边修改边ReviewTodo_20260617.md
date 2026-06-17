# 咖啡烘焙系统：今晚边修改边 Review TODO

> 日期：2026-06-17  
> 用途：今晚执行时逐项勾选。每完成一小轮修改，就更新状态和验收记录。

## 0. 执行约定

状态标记：

```text
[ ] 未开始
[~] 进行中
[x] 已完成
[!] 阻塞或需要用户决策
```

每个任务完成后至少记录：

```text
改动文件：
检查命令：
检查结果：
遗留风险：
```

## 1. P0：Alembic 初始迁移

- [ ] 定位当前迁移文件 `backend/alembic/versions/20260616_0001_initial_schema.py`
- [ ] 确认当前 SQLAlchemy models 覆盖哪些核心表
- [ ] 重写 initial migration，移除 `Base.metadata.create_all`
- [ ] 重写 downgrade，移除 `Base.metadata.drop_all`
- [ ] 确保迁移中显式包含核心 `op.create_table`
- [ ] 检查表依赖顺序、外键、索引和唯一约束
- [ ] 运行 Python 语法检查
- [ ] 如果数据库环境可用，运行 `alembic upgrade head`
- [ ] 如果数据库环境可用，运行 `alembic downgrade base`

记录区：

```text
改动文件：
检查命令：
检查结果：
遗留风险：
```

## 2. P0：内部接口认证

- [ ] 搜索所有 `@router.get` / `@router.post` 等 API 路由
- [ ] 标记应该匿名访问的公开接口
- [ ] 标记必须登录访问的内部接口
- [ ] 给 `GET /api/v1/green-beans/tree` 补认证
- [ ] 给 `GET /api/v1/green-beans/matches` 补认证
- [ ] 检查采购批次、烘焙批次、曲线、评价管理、复盘接口认证状态
- [ ] 确认公开问卷读取接口仍可匿名访问
- [ ] 确认公开问卷提交接口仍可匿名访问
- [ ] 如果后端测试环境可用，验证未登录访问内部接口返回 401

记录区：

```text
改动文件：
检查命令：
检查结果：
遗留风险：
```

## 3. P1：登录与真实 API 模式

- [ ] 定位 `frontend/src/views/Login.vue`
- [ ] 移除默认密码 `admin123`
- [ ] 检查是否还有其它默认账号或密码预填
- [ ] 检查 `frontend/src/config` 或等价位置的 `VITE_DEMO_MODE` 逻辑
- [ ] 更新 `.env.example`，明确 demo 模式配置
- [ ] 更新 `.env.example`，明确真实 API 模式配置
- [ ] 确认真实 API 模式下未登录会跳转 `/login`
- [ ] 确认页面或布局中能看出当前是 demo 还是真实 API

记录区：

```text
改动文件：
检查命令：
检查结果：
遗留风险：
```

## 4. P1：前端 mock / service 边界

- [ ] 搜索前端直接 import `mock` 的文件
- [ ] 按业务模块列出 mock 依赖清单
- [ ] 确认已有 `api/`、`adapters/`、`services/` 结构
- [ ] 先迁移最影响联调判断的页面到 service 层
- [ ] service 内根据 demo mode 选择 mock 或真实 API
- [ ] 页面组件不直接判断 demo mode，尽量只调用 service
- [ ] 更新未迁移页面清单，避免误以为已经真实联调

已知待检查页面：

- [ ] `Dashboard.vue`
- [ ] `RoastingBatchList.vue`
- [ ] `CurveAnalysis.vue`
- [ ] `EvaluationManagement.vue`
- [ ] `EvaluationDetail.vue`
- [ ] `BatchReview.vue`
- [ ] `PublicQuestionnaire.vue`
- [ ] `stores/roasting.ts`

记录区：

```text
改动文件：
检查命令：
检查结果：
遗留风险：
```

## 5. P2：补录与多 CSV 数据模型

- [ ] 给 `roasting_batches` 模型增加 `entry_mode`
- [ ] 给 `roasting_batches` 模型增加 `inventory_effective`
- [ ] 给 `roasting_batches` 模型增加 `roasted_at_source`
- [ ] 给 `roasting_batches` 模型增加 `bulk_import_group_id`
- [ ] 给 `roasting_batches` 模型增加 `source_note`
- [ ] 新增 `bulk_import_jobs` 模型
- [ ] 新增 `bulk_import_items` 模型
- [ ] 补 schema / DTO
- [ ] 补 repository 或 service 所需类型
- [ ] 生成或手写 Alembic 迁移
- [ ] 检查默认值：多 CSV 默认扣库存，历史补录默认不扣库存

记录区：

```text
改动文件：
检查命令：
检查结果：
遗留风险：
```

## 6. P2：库存规则闭环

- [ ] 定位库存计算函数
- [ ] 修改库存计算，只统计 `status='completed'` 且 `inventory_effective=true`
- [ ] 检查重开批次逻辑
- [ ] 检查作废批次逻辑
- [ ] 确认 `inventory_effective=false` 不写扣减流水
- [ ] 确认 `inventory_effective=false` 不写返还流水
- [ ] 补充或更新测试用例

记录区：

```text
改动文件：
检查命令：
检查结果：
遗留风险：
```

## 7. P3：bulk preview 后端

- [ ] 新增或确认 `backend/app/services/bulk_import.py`
- [ ] 新增或确认 `backend/app/repositories/bulk_imports.py`
- [ ] 新增采购批次下 bulk preview 路由
- [ ] 新增历史补录 preview 路由
- [ ] 支持多文件上传
- [ ] 复用 CSV 解析能力
- [ ] 实现 roasted_at 推断
- [ ] 返回 warnings 和 summary
- [ ] 检测重复文件 hash
- [ ] 返回预计库存扣减
- [ ] 确认 preview 不创建 roasting batch
- [ ] 确认 preview 不扣库存

记录区：

```text
改动文件：
检查命令：
检查结果：
遗留风险：
```

## 8. P3：bulk commit 后端

- [ ] 新增采购批次下 bulk commit 路由
- [ ] 新增历史补录 commit 路由
- [ ] commit 前锁定采购批次或确保并发安全
- [ ] commit 前检查库存
- [ ] 防止同一个 job 重复提交
- [ ] 为每个成功 item 创建 completed roasting batch
- [ ] 保存 curve file
- [ ] 生成 active roasting curve
- [ ] 按 `inventory_effective` 决定是否扣库存
- [ ] 更新 bulk import job 和 items 状态
- [ ] 返回成功、失败和跳过明细

记录区：

```text
改动文件：
检查命令：
检查结果：
遗留风险：
```

## 9. 收尾

- [ ] 跑后端语法检查
- [ ] 跑前端类型检查或 build
- [ ] 汇总今晚完成项
- [ ] 汇总未完成项
- [ ] 汇总需要用户决策的问题
- [ ] 更新 Acceptance 文件中的实际验收结果
- [ ] 如有必要，生成新的交接 Summary
