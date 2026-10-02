# P1.5 真实验证记录

输入为“香港 11 月飞日本哪里便宜？”。价格只代表对应文件记录的抓取时间，不是现在的推荐，也不是全月最低。

- `p15-final-check-*`：最终代码三次新进程、新Session验收，因新的CDP会话未建立而blocked；不得用此前正文或价格补齐。对应源码指纹在 `final-source-manifest.json`。
- `p15-scan-*`：完整扫描模式两轮对照，也出现partial；第二轮加了页面失败分类和航司名称格式修正。
- `p15-release-*`：连接修复、逐篇读取与活动去重修正后，同一中间版本连续进行的应用冷启动。每轮使用新Python进程、新Session；沿用已登录Chrome，不重启daemon。报告和审计都保留成功与失败。
- `p15-connected-intermediate-audit.json`：此前一轮完整研究成功，但还没有补齐大湾区促销去重规则，单列为中间版。
- `p15-baseline-*` / `p15-improved-*`：Chrome连接恢复前的原版与中间版失败记录，不能用于宣称连接恢复后的速度提升。
- `p15-date-old-audit.json` / `p15-date-new-audit.json`：使用历史已读路线、重新请求当前报价的单次日期阶段对照；不是完整社区冷启动。
- `p15-date-comparison*`：FlyAI range、Google Travel Explore、Flights Deals与精确查价的真实响应对照。
- `p15-historical-evidence-review.json`：历史正文中的促销关联分析。
- `socai-connection/`：连续调用、CLI取消和适配器调用时的daemon/Chrome/endpoint/CDP连接观测。只保存连接指纹，不保存访问token。

完整结论、各阶段耗时、日期覆盖和限制见[当前P1.5验收文档](../../docs/current/p15-acceptance.md)。本机完整Session和socai原始回执含访问参数，仅保存在忽略提交的私有目录；公开审计包含出处、时间、分组、调用量、失败和可核对航班事实。
