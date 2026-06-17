# 咖啡烘焙系统：今晚边修改边 Review Acceptance

> 日期：2026-06-17  
> 用途：每轮修改后的验收标准与记录。这里判断“能不能进入下一轮”，不是写长期产品需求。

## 1. 总体验收原则

今晚每个任务必须满足：

- 修改范围足够小，能说清楚为什么改这些文件。
- 关键业务规则没有被绕开。
- 能运行的检查必须运行。
- 不能运行的检查必须说明原因。
- 未完成事项必须回写到 TODO。

## 2. 必跑检查清单

后端基础检查：

```powershell
cd backend
python -m py_compile app/main.py
```

后端扩展检查，按改动范围选择：

```powershell
cd backend
python -m py_compile app/api/v1/*.py app/services/*.py app/repositories/*.py app/parsers/*.py
```

数据库环境可用时：

```powershell
cd backend
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

前端基础检查：

```powershell
cd frontend
npm run build
```

如果项目提供更轻量的检查命令，优先使用项目内已有脚本，例如：

```powershell
npm run type-check
npm run lint
pytest
```

## 3. P0 验收：Alembic 初始迁移

必须通过：

- [ ] 迁移文件中不出现 `Base.metadata.create_all`
- [ ] 迁移文件中不出现 `Base.metadata.drop_all`
- [ ] `upgrade()` 中显式使用 `op.create_table`
- [ ] `downgrade()` 中显式按依赖顺序 `op.drop_table`
- [ ] 核心表包含主键、外键、索引和必要唯一约束
- [ ] 迁移文件本身语法检查通过

数据库可用时追加：

- [ ] `alembic upgrade head` 成功
- [ ] `alembic downgrade base` 成功
- [ ] 再次 `alembic upgrade head` 成功

验收记录：

```text
执行时间：
检查命令：
结果：
未通过项：
处理决定：
```

## 4. P0 验收：内部接口认证

必须通过：

- [ ] 未登录访问 `/api/v1/green-beans/tree` 返回 401
- [ ] 未登录访问 `/api/v1/green-beans/matches` 返回 401
- [ ] 登录后可以访问生豆树
- [ ] 登录后可以访问生豆匹配接口
- [ ] 采购批次、烘焙批次、曲线、评价管理、复盘接口需要登录
- [ ] 公开问卷读取接口可以匿名访问
- [ ] 公开问卷提交接口可以匿名访问

允许暂缓：

- 如果本地后端无法启动，可以先完成代码级 review，并把接口实测标记为待补验收。

验收记录：

```text
执行时间：
检查方式：
结果：
未通过项：
处理决定：
```

## 5. P1 验收：登录页与真实 API 模式

必须通过：

- [ ] 登录页不预填密码
- [ ] 登录页不展示任何误导性的默认生产密码
- [ ] `.env.example` 包含 demo 模式示例
- [ ] `.env.example` 包含真实 API 模式示例
- [ ] `VITE_DEMO_MODE=false` 时启用真实 API 逻辑
- [ ] 真实 API 模式下未登录访问内部页面会跳转登录页
- [ ] 页面或布局能显示当前处于 demo 或真实 API 模式

验收记录：

```text
执行时间：
检查命令：
结果：
未通过项：
处理决定：
```

## 6. P1 验收：mock / service 边界

必须通过：

- [ ] 已生成直接 import mock 的文件清单
- [ ] 已区分“今晚已迁移”和“后续待迁移”
- [ ] 已迁移页面不再直接 import `mock`
- [ ] 已迁移页面只通过 service 获取数据
- [ ] service 内部根据 demo mode 选择 mock 或真实 API
- [ ] 真实 API 模式下不会静默回退到 mock

阶段性允许：

- 不要求今晚一次迁移所有页面。
- 但每个未迁移页面必须留在 TODO 清单中。

验收记录：

```text
执行时间：
检查命令：
已迁移页面：
未迁移页面：
结果：
```

## 7. P2 验收：补录与多 CSV 数据模型

必须通过：

- [ ] `roasting_batches.entry_mode` 存在并有合理默认值
- [ ] `roasting_batches.inventory_effective` 存在并有合理默认值
- [ ] `roasting_batches.roasted_at_source` 存在
- [ ] `roasting_batches.bulk_import_group_id` 存在
- [ ] `roasting_batches.source_note` 存在
- [ ] `bulk_import_jobs` 表存在
- [ ] `bulk_import_items` 表存在
- [ ] schema / DTO 能表达 preview 和 commit 所需字段
- [ ] Alembic 迁移覆盖上述变化

默认规则必须成立：

- [ ] 当前采购批次下多 CSV 导入：`entry_mode=csv_bulk_import`
- [ ] 当前采购批次下多 CSV 导入：`inventory_effective=true`
- [ ] 历史补录：`entry_mode=historical_backfill`
- [ ] 历史补录：`inventory_effective=false`

验收记录：

```text
执行时间：
检查命令：
结果：
未通过项：
处理决定：
```

## 8. P2 验收：库存闭环

必须通过：

- [ ] 库存计算只扣 `status='completed'` 且 `inventory_effective=true` 的烘焙批次
- [ ] `inventory_effective=false` 的历史补录不影响当前库存
- [ ] 多 CSV 导入默认扣库存
- [ ] 重开 `inventory_effective=true` 的批次会返还库存
- [ ] 作废 `inventory_effective=true` 的批次会返还库存
- [ ] 重开或作废 `inventory_effective=false` 的批次不写返还流水

建议测试场景：

```text
采购批次 3000g
手动完成烘焙 500g，影响库存
历史补录 500g，不影响库存
剩余库存应为 2500g
```

验收记录：

```text
执行时间：
检查方式：
结果：
未通过项：
处理决定：
```

## 9. P3 验收：bulk preview

必须通过：

- [ ] 支持一次上传多个 CSV
- [ ] 返回每个文件的解析状态
- [ ] 返回每个文件的 warnings
- [ ] 返回推断烘焙时间
- [ ] 返回 `roasted_at_source`
- [ ] 返回预计投豆量和预计库存扣减
- [ ] 能识别重复文件 hash
- [ ] 单个 CSV 解析失败不影响其它文件预览
- [ ] preview 不创建 roasting batch
- [ ] preview 不扣库存

验收记录：

```text
执行时间：
检查方式：
测试文件：
结果：
未通过项：
处理决定：
```

## 10. P3 验收：bulk commit

必须通过：

- [ ] 同一个 job 不能重复 commit
- [ ] 库存不足时拒绝提交
- [ ] commit 成功后每个 item 生成一个 completed roasting batch
- [ ] 每个 roasting batch 有对应 curve file
- [ ] 每个 roasting batch 有 active roasting curve
- [ ] `inventory_effective=true` 时扣库存
- [ ] `inventory_effective=false` 时不扣库存
- [ ] 返回成功、失败、跳过明细

建议测试场景：

```text
采购批次 3000g
上传 2 个 CSV
每个设置投豆量 550g
commit 后应生成 2 条 completed roasting batch
剩余库存应减少 1100g
```

验收记录：

```text
执行时间：
检查方式：
测试文件：
结果：
未通过项：
处理决定：
```

## 11. 每轮最终记录模板

每完成一轮，把下面内容追加到本节。

```text
轮次：
时间：
本轮目标：
完成项：
改动文件：
运行检查：
通过验收：
未通过验收：
下一步：
```

## 12. 今晚结束标准

至少满足以下任一条件，就可以收尾并生成下一轮交接：

- P0 全部完成并验收。
- P0 完成，P1 完成一部分，剩余项清楚记录。
- 遇到环境阻塞，但代码级 review、TODO 和验收缺口已经记录清楚。

不建议在 P0 未完成前开始前端多 CSV 页面。
