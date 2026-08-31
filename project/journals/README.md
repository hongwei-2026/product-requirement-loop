# 产品研发日志库

数据来自官方仓库：
https://github.com/quanttide/quanttide-journal-of-product-development

按 **产品流 × 日期** 归档（与产品云一致）。

## 同步全量（交付前必跑）

在仓库根目录：

```bat
python scripts\sync_journals.py
```

会拉取各产品流日日志到本目录，并重建 `catalog.json`。

## 怎么选才对、才快

| 场景 | 怎么选 |
|------|--------|
| 拍视频 / 快速试跑 | 选「聚焦摘录」或字数少的日日志 |
| 正式定稿 | 选对应 **产品流 + 日期** 的全文 |
| 刚开完会 | 前端粘贴 / 上传 → 进 `custom/` |

## 前端入口

侧栏 **「日志库」** 页可浏览全部日志；工作台可「快速更换」。
