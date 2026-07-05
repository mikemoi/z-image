# 当前状态快照

> 更新于 2026-07-05，代码基线 `f85470d` 之后。这里描述“现在实际能做什么”，历史愿景看根目录蓝图文档。

## 当前版本

- 分支：`main`
- 阶段：v0.3，截图入口、文字入口与统一分类已经可用。
- 数据库：PostgreSQL，`core` 与 `image` 两个 schema；启动时由 `ensure_schema()` 幂等补迁移。
- 前端：React/Vite/PWA；后端：FastAPI；AI：OpenRouter。
- 生产环境最后部署的 commit 未在仓库内记录；部署前必须在服务器执行 `git rev-parse HEAD` 与本地目标 commit 对照。

## 已完成

- 截图上传、checksum 去重、原图落盘、后台 Vision/OCR。
- 截图浏览、搜索、详情、问问 AI、精选/落箱、永久删除。
- 想法、日志、计划三个文字入口。
- 统一五维分类：类型、领域、用途、标签、来源。
- 文字与截图后台自动分类；人工编辑优先；支持手动重新分类。
- OCR、问问 AI、自动分类三个模型可分别配置。
- 分类说明与分类字段前端展示/编辑。
- 想法、日志和长期计划使用统一编辑器；普通卡片分类只读，标签不能直接误删。
- 想法默认作为一等内容保留，前端已移除二次精选按钮。
- 想法卡显示原始创建日期和时间，用于回看思考随时间的变化。
- “我的 → 数据概览”统一展示内容、类型、领域、用途、来源和分类状态；不展示趋势或完成率。

## 当前兼容层

- 旧 `theme/use_tag/granularity` 仍服务截图 Browse、Vision 和精选流程。
- 新 `entry_type/domain/topics` 已加入 entries 与 items。
- `kind` 是入口类型（idea/log/plan），不等于内容类型 `entry_type`。
- 截图来源在业务上固定为“截图”，`image.items` 没有单独 `source` 列。

## 已知问题

- `theme` 与 `domain` 并存，语义有重叠，暂未迁移或删除旧字段。
- 自动分类失败状态 `failed` 不会自动重试；需从 UI 或 API 调用 reclassify。
- `image.items` 的人工更新模型尚未用 Literal 严格限制枚举，分类器输出会 normalize。
- README、旧架构蓝图和规划文档包含历史表述；当前实现以本文件、HANDOFF、API、DATABASE 和源码为准。
- 暂无隔离测试数据库；现有自动测试均不连接真实 DB、不调用真实 AI。
- 生产 Vision/分类 Worker 是否健康属于运行状态，不能仅凭仓库判断；需看 `/api/worker/status` 和服务日志。

## 下一步建议

1. 首页信息架构整理，移除已迁到数据概览的统计区域。
2. 新增“记录 → 近日”轻量备忘；长期计划保留在“我的”。
3. 想法簇/可逆合并。
4. 截图追问。
5. 重新遇见改成截图驱动。
6. 最后再做向量与语义聚合。

## 发布前最小检查

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q .

cd ..\frontend
npm run build
```

若改数据库或 API，再本地启动后检查 `/api/health`、`/docs`，并使用专用测试数据验证；不要在生产库跑破坏性测试。
