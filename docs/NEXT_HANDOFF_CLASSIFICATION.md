# 最终内容坐标交接归档

> 写于 2026-07-06，原本用于记录“最终内容坐标 + 子题 + 候选机制 + 重新整理 + 时间线 + 搜索范围”的未开工需求。
>
> 截至提交 `43a6445`，这批需求已经进入源码主线。本文件只作为历史需求归档保留，不再代表待办。

## 已落地

- 内容坐标：类型 / 领域 / 主题 / 子题 / 相关 / 标签 / 来源
- 类型压缩：想法 / 知识 / 资料 / 记录 / 规则
- 来源统一：我 / 图片 / 文件
- `core.entries` 和 `image.items` 均支持 `sub_topic`
- 前后端固定子题表
- 图片详情页写想法：`source=我`，保留 `source_item_id`
- 搜索范围：全部 / 我的 / 外部
- 我的页面：时间线 / 重新整理 / 待审批
- 候选标签与候选子题池：`core.classification_candidates`
- 候选来源分布：`source_counts`
- 重新整理排队接口：`POST /api/admin/reclassify`
- 候选审批接口：`GET/POST /api/candidates`

## 当前权威文档

继续开发时以这些文件为准：

- [HANDOFF.md](HANDOFF.md)
- [STATUS.md](STATUS.md)
- [DATABASE.md](DATABASE.md)
- [API.md](API.md)
- [TESTING.md](TESTING.md)
- 源码：
  - `backend/classification_schema.py`
  - `frontend/src/classification.js`
  - `backend/classify.py`
  - `backend/worker.py`

## 注意

候选子题机制是“受控生长机制”，不是固定子题名称。AI 可以提名，但不能直接扩建正式子题表。正式扩充固定子题仍需同步修改：

```text
backend/classification_schema.py
frontend/src/classification.js
backend/tests/test_classification.py
```
