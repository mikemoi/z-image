# 测试与验收

## 无外部副作用的回归测试

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q .

cd ..\frontend
npm run build
```

`backend/tests/test_classification.py` 不连接数据库、不调用 OpenRouter，覆盖：

- 固定类型、领域、主题、子题枚举与领域/主题/子题归属规则。
- 关联 related_topics 最多 2 个，tags 最多 5 个。
- Entry 请求模型枚举校验。
- Entry 来源统一为“我”；`source_item_id` 只保留图片关联，不改变来源。
- 人工修改分类后锁定 AI 状态。
- 重新分类清空字段并回到 pending。

## 本地集成验收

集成验收会写数据库，应只在本地或专用测试库执行：

1. 启动 PostgreSQL、后端和前端。
2. `/api/health` 应返回 `db=connected`。
3. 创建普通想法，确认 `source=我`、`entry_type=想法`。
4. 从截图详情创建想法，确认 `source=我` 且保留 `source_item_id`。
5. 人工改分类，确认状态为 done 且 Worker 不覆盖。
6. 调 reclassify，确认字段清空、状态 pending。
7. 上传测试图，确认分类 Worker 补 `entry_type/domain/main_topic/sub_topic/related_topics/tags`。
8. 删除全部测试数据和测试文件。

## 真实 AI 验收

真实 AI 会产生费用，只在明确需要时进行。需要有效 `OPENROUTER_API_KEY`，并检查三个模型设置。不要把 key、token、数据库密码写进测试、日志或提交。
