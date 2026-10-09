# FareScout 文档导航

文档分为三类：当前统一版、历史记录和实现参考。当前需求的唯一依据是《产品需求与验收标准》；开发和验收时，遇到其他文档与它不一致的地方，以需求原文为准。

## 当前统一版

| 文档 | 内容 |
|---|---|
| [产品需求与验收标准](current/product-requirements.md) | 产品范围、需求和完成标准；唯一需求基准 |
| [系统概览与产品价值](current/system-overview.md) | 研究流程、技术选择、Agent 行为及产品价值；文中 POC 部分标明为历史状态 |
| [P1 实现说明](current/implementation.md) | 当前 P1 如何实现、各组件怎样配合、已知风险和暂缓事项 |
| [前端研究工作台](current/frontend-workspace.md) | 三栏界面、航线结论追溯、会话交互修复与前端验证 |
| [P1 真实验收与限制](current/acceptance.md) | 真实运行记录、调用量、日期覆盖、失败来源和 P1 完成情况 |
| [P1.5 改进计划](current/p15-plan.md) | 社区读取、耗时、日期调用和促销去重怎样改进 |
| [P1.5 验证与 Chrome 连接诊断](current/p15-acceptance.md) | 改动说明、逐轮真实冷启动、阶段耗时、日期对照及尚未通过的稳定性验收 |
| [研究恢复与提前展示结果](current/research-recovery-acceptance.md) | 同一轮恢复、按缺口选择下一步、真实首条结果耗时和睡眠附近的 CDP 断线记录 |
| [CDP 稳定性与恢复验收](current/cdp-stability-acceptance.md) | 睡眠与不睡眠对照、首次 WebSocket 日志、确认后自动续跑、managed Chrome 的实际结果及尚未通过的检查 |
| [社区浏览器会话稳定性专项](current/browser-session-stability.md) | managed 默认配置、空闲读取、daemon 状态更新滞后修复、四次真实断线续跑，以及票价验收和长期空闲的限制 |
| [上午授权后，下午为什么又需要确认 Chrome](current/cdp-disconnect-investigation.md) | 排查三小时超时、进程清理和睡眠附近的CDP断线，并给出分阶段解决方案 |
| [socai 连接复用排查](current/socai-connection-diagnosis.md) | 连续搜索的 daemon、endpoint、TCP连接实测与首次授权等待修正 |

## 历史记录

| 文档 | 内容 |
|---|---|
| [P0 验收记录](history/p0-acceptance.md) | 原 POC 的真实运行及 MUST 验收记录 |
| [实施计划与落地过程](history/implementation-plan.md) | P0 起步计划和后续调整过程；历史环境状态不代表当前状态 |
| [技术验证记录](history/technical-spike.md) | 早期技术 Spike 与后续复测经过 |
| [P1 方向调研](history/p1-direction-research.md) | P1 开发前的调研快照，不代表当前实现状态 |

## 实现参考

- [已登录浏览器桥接说明](reference/browser-bridge.md)：早期宿主浏览器协作方式及文件回执协议。
- [逐轮研究报告与原始审计数据](../reports/)：真实研究报告、Session 和审计文件。
