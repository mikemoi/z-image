# 代码审查报告 · 2026-07-06

> 基线：`main` @ `afa712a`。覆盖：后端全部源码（模块/路由/模型/测试/init.sql/Docker 配置），前端核心链路（api/App/classification/Detail/ReviewSession/Home/Me/Logs/Browse/Capture/EntryEditor/Img/TokenGate），其余小页面同模式略读。
> 总体评价：对单人自托管项目质量偏高——参数化 SQL、幂等迁移、软删纪律、人工优先锁、异常不阻塞主流程执行一致。以下问题按严重程度排列。
> 状态标记：☐ 待修 / ☑ 已修。修完请更新本文件。

---

## 一、高优先级：真实风险（建议尽快修）

### ☑ 1. 原图误删风险：checksum 没有唯一约束
`deploy/init.sql` 里 `idx_files_checksum` 是普通索引，非 UNIQUE。上传去重靠 `routers/items.py` 的先查后插（`SELECT ... LIMIT 1`），并发或竞态可产生**同 checksum 两行 files 指向同一磁盘文件**。`purge` 只按 file_id 查引用，另一行的 item 还在，但 `os.remove` 已把文件删了。原图是唯一副本，这是全项目唯一可能物理丢图的代码路径。
**修复**：加 `CREATE UNIQUE INDEX`（先清历史重复行）+ purge 前按 file_path/checksum 查引用而不只按 file_id。

### ☑ 2. 图片无缩略图、无缓存——存量导入的硬阻塞
`frontend/src/components/Img.jsx` 每次挂载 fetch **完整原图** blob，卸载即 revoke，无缓存；`routers/files.py` 无 Cache-Control。Browse `limit=200` 一次拉 200 张全尺寸截图（几百 MB）；翻页/返回全部重新下载。5-6000 张存量导入后浏览体系不可用。
**修复**：上传时生成缩略图（或按需缩放端点）+ `Cache-Control: immutable`（checksum 命名天然适合）+ 前端按 checksum 缓存。这是下一阶段第一件工程事。

### ☑ 3. 分类结果全空仍标 done，从此沉默失联
`worker.py` classify_entry/classify_item：模型跑偏时 normalize 可能全 None，仍写 `ai_classify_status='done'`——无任何分类却被标完成，worker 永不再碰，只能靠"重新整理 fill_missing"捞回。
**修复**：`entry_type/domain/main_topic` 全空时按 failed 处理。

### ☑ 4. 分类 failed 无自动重试（与 Vision 不对称）
Vision 有 `_attempts` 重试到上限机制，分类失败一次即永久 failed。把 attempts 模式复制到分类管线。

### ☑ 5. 时区不一致：「往年今天」错位
`routers/entries.py` `on_this_day` 用 `date.today()`（容器内 UTC），日志创建/timeline 用 `Europe/Madrid`。马德里 0:00–2:00 之间日期匹配错一天。
**修复**：统一 `datetime.now(MADRID).date()`。

## 二、中优先级：安全与部署加固

### ☑ 6. 弱默认凭据静默生效
`config.py` 硬编码兜底密码 `zbrain2024` 和 `dev-token-change-me`；生产 `.env` 漏配时照常启动。`auth.py` 用 `!=` 比较 token。
**修复**：检测到默认 token 且非开发模式时启动报错；`secrets.compare_digest`。

### ☑ 7. 上传无大小/类型校验
任意大小/扩展名都收，`await up.read()` 整个进内存。建议 20MB 上限 + 扩展名白名单。

### ☑ 8. file_path 存上传时环境的路径
本地存 `./data/...`、容器存 `/data/...`，同库换环境旧图全 410。文件名即 `checksum.ext`，建议读取时从 `FILES_ROOT + checksum` 推导路径，不信任 DB 旧路径。

### ☑ 9. SPA catch-all 吞掉未知 API 路径
`main.py` 把 `/api/不存在` 也回 index.html。加一行 `full_path.startswith("api/")` → 404。

### ☑ 10. CORS 全开 `*`
生产同域单端口，其实可收紧。记录在案，低优先。

## 三、中优先级：正确性小刺

### ☑ 11. 文档与代码矛盾——insight 不消耗预算
DECISIONS.md 称"三个模型共用每日预算"，但 insight 端点不走 `_take_budget`（v0.3-plan 原意即不限）。**修文档**。

### ☑ 12. 搜索两处小毛病
`routers/search.py`：① `q` 中 `%`/`_` 未转义；② 图片/文字命中各取 limit 拼接再截断，图片永远排前，图片多时文字结果被完全挤掉。建议按 created_at 合并排序再截断。

### ☑ 13. Vision 落库失败会重复烧钱
`worker.py` DB 写失败丢弃已付费的 Vision 结果，重试重新调用。可把结果暂存进失败记录复用。低频。

### ☑ 14. 候选累计读-改-写竞态
`worker.py` `_upsert_candidate` 先读再写，并发可丢计数或撞唯一约束导致整次分类事务回滚（分类成功却标 failed）。改单条 `INSERT ... ON CONFLICT DO UPDATE`。

### ☑ 15. `_reading_queue` 的 total 是页大小非总数
`routers/items.py`。前端未用，防将来误用。

### ☑ 16. `vision.py` `_QUALITY` 后定义先引用
175 行定义、84 行 normalize 引用。运行没问题，可读性陷阱，挪文件顶部。

## 四、产品层缺口

### ☑ 17. 材料 ↔ 想法只有"写"没有"看"
Detail/ReviewSession 能就地写想法（闭环动线好），但详情页看不到该图已绑定的想法——加工层资产不可见。应加"我的想法（N 条）"区块，纯查询零 AI 成本，直接服务新定位核心。

### ☑ 18. Home 每 4 秒轮询 workerStatus 永不停
PWA 后台也在打。加 `document.visibilityState` 判断。

### ☑ 19. 分类表三份维护
`classification_schema.py` + `classification.js` + prompt 内嵌（prompt 已从 schema 生成，正确）。前端那份将来由 API 下发。

## 五、测试与工程债

### ☑ 20. 测试只覆盖分类契约
worker（候选累计/COALESCE 填充）、admin 确定性迁移 SQL、items 全部路由零测试；现有测试 mock conn，SQL 未被验证。admin.py 手写 JSONB 迁移最值得补集成测试（docker 临时 PG）。
**修复**：补上传校验/路径推导/candidate upsert/schema 下发/items queue total/admin 子题迁移回归测试；完整临时 PG 集成测试仍可后续增强。

### ☐ 21. schema 三处定义
init.sql / ensure_schema / DATABASE.md，每加一列同步三处。建议 ensure_schema 为唯一真源、init.sql 只留基线，或引入迁移编号。

## 六、未来架构建议（对接"外部大脑 + 生活记录 + 反馈"定位）

1. **缩略图管线**是存量导入、时间线卡片、运动/西语数据卡的共同地基（见 #2）。
2. **`/entries/timeline` 即未来"全系统总视图"落点**：现只查 `kind='log'`，将来运动/西语结构化记录按时间戳在此合流，前端 Timeline 已有骨架，设计对齐无需推翻。
3. **PWA 数据接入**：新开 `/api/ingest/...` 前缀 + 对方记录 ID 作幂等键，不复用 entries 创建端点（同步与手写语义不同）。
4. **搜索升级路径**：几千条 ILIKE 无压力；过万加 `pg_trgm` GIN 索引即可，无需改查询、无需 pgvector。
5. **健康自检**：给 health/概览加"磁盘文件数 vs files 行数"对账——唯一副本值得自动核对。

## 建议的修复顺序

- **第一批（半天，全是小改）**：#1 #3 #4 #5 #6 #11 #16
- **第二批（一次工程投入）**：#2 缩略图 + 缓存管线
- **第三批（随功能顺手）**：#12 #17 #14 #20
