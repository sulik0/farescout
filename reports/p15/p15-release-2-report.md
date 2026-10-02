# 飞探 FareScout 研究报告

**状态：partial** · 会话 `p15-release-2` · 轮次 `6ab2d6d1e791611a`

需求：香港 11 月飞日本哪里便宜？

出发：HKG；地区：JP；日期：2026-11-01～2026-11-30；单程，1 成人，经济舱。

排除红眼：未要求。

研究开始：2026-10-02T02:01:33.914081+00:00；结束：2026-10-02T02:07:56.401385+00:00。

研究假设：

- 未指定行程：先比较 1 成人、经济舱、单程；不同口径不混比
- 日期窗口已收窄到 2026 年 11 月，精确报价仍按样本日期

调用统计（工具调用，不把范围请求展开成虚构的逐日调用）：

- 社区 4 次；日期探索 4 次；最终精确验价 1 次；模型操作 3 次。
- 本轮耗时 382.487 秒。

- socai实际命令 14 次（含状态检查、搜索、正文读取与重试）；模型实际请求 3 次（含Pydantic AI重试）。
- 本轮报价复用 1 次；这些不是新增API调用，保留原抓取时间。
- 正文 4 篇；按已识别的转载/活动分为 4 组，未证明作者相互独立。

各类请求耗时：

| 请求类别 | 累计秒数 |
|---|---|
| browser_connection | 0.0 |
| 社区搜索（含读取） | 225.485 |
| 日期请求 | 14.193 |
| 日期阶段实际用时 | 13.592 |
| 最终验价 | 1.276 |
| 模型 | 7.062 |
| 扩展查询（含读取） | 136.345 |
| 搜索卡片 | 164.393 |
| 单篇正文读取 | 49.156 |
| 社区完整扫描 | 133.039 |

社区搜索已包含卡片和正文时间，不能再相加；并发日期请求累计时间可能大于实际阶段用时。

约束解释：

| 字段 | 生效值 | 来源 | 规则 |
|---|---|---|---|
| origins | \[&#x27;HKG&#x27;\] | 用户明确 |  |
| region | JP | 用户明确 |  |
| date_from | 2026-11-01 | 语义解释 | 月份未含年份时取下一次该月份；日期探索是采样，不保证全窗最低 |
| date_to | 2026-11-30 | 语义解释 | 月份未含年份时取下一次该月份；日期探索是采样，不保证全窗最低 |
| date_mode | flexible | 用户明确 |  |
| trip_type | one\_way | 系统默认 | 默认1成人经济舱单程；往返须确认完整去回程 |
| stay_days | 5 | 系统默认 |  |
| no_red_eye | False | 系统默认 | 开启时排除任一航段当地22:00–06:00或跨夜；跨夜长途可能被保守排除 |

本轮整理 1 个调查方向，其中 1 个取得可核对的当前报价。

| 值得继续看的方向 | 当次各渠道最低报价（相互不作含税比较） |
|---|---|
| HKG → KIX | FlyAI / 飞猪 CNY 876（税费未确认）；Google Flights / SerpAPI CNY 893（含税） |

**尚未满足 3～5 个有价格证据的机会要求。不会用社区晒价补齐当前价格。**

## 1. 香港 HKG → 大阪关西 KIX

**发现依据 / 社区出现价格（不是当前票价）**

从 1 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [快运｜香港大阪9折最低来回1.5K，跨国庆也有](https://www.xiaohongshu.com/explore/6ab4a8860000000015008f93) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-02T02:05:21.373227+00:00
  - 原文：红叶季：11月19日-11月24日 2126HKD-200HKD（离境税），约等于1.6K 闲日：10月底、11月初、12月初都有 1946HKD-200HKD（离境税），约等于1.5K
  - 社区晒价：2126HKD-200HKD（离境税）；航司：未确认。
  - 证据质量：价格可能依赖未分析图片。不同正文，作者/活动来源独立性未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-30。

实际精确请求日期（含失败）：2026-11-04, 2026-11-29, 2026-11-30；范围响应返回日期：2026-11-04。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-04 | SerpAPI / Google Travel Explore | range | ok | 952.0 / adult_fare_tax_unknown |
| 2026-11-30 | SerpAPI | coarse | ok | 893.0 / total_including_taxes |
| 2026-11-04 | SerpAPI | coarse | ok | 952.0 / total_including_taxes |
| 2026-11-29 | SerpAPI | fine | ok | 952.0 / total_including_taxes |
| 2026-11-30 | FlyAI | verification | ok | 876.0 / adult_fare_tax_unknown |
| 2026-11-30 | SerpAPI | verification | ok | 893.0 / total_including_taxes |

- **CNY 876**（票价，税费口径未确认）· [FlyAI / 飞猪](https://flyai.open.fliggy.com/) · 出发 2026-11-30 / 单程 · 查询 2026-10-02T02:07:56.396911+00:00
  - 乐桃航空 MM064：HKG 2026-11-30 12:45:00 → KIX 2026-11-30 17:10:00
  - 行李：未确认，不能假定包含托运行李。
  - FlyAI adultPrice/ticketPrice 报价；税费总额未确认，不能等同于含税总价
  - 未访问 jumpUrl 或任何预订页
  - FlyAI 体验模式：部分结果受限
- **CNY 893**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-30 / 单程 · 查询 2026-10-02T02:07:52.520278+00:00
  - Peach Aviation MM 64：HKG 2026-11-30 12:45 → KIX 2026-11-30 17:10
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 640～1050；本轮同条件可比。

**交叉验证与结论**

- 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。
- 社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。

值得继续关注的依据是存在社区线索，且本次查到可核对的航班报价。是否足够便宜还应结合你的预算和出行条件。

**主要限制**

- 仅核查列出的具体日期；不是整个日期窗口的最低价保证。
- 帖文、作者或活动来源的独立性未确认；不同正文不自动等于独立佐证。
- 社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。
- 典型价格仅来自Google本次同条件洞察；不代表自建历史库、历史最低或库存保证。
- 从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。
- 发布时间为页面原文；相对时间以抓取时间为参照

Deal基础判断：**处于 Google 典型区间**。同一搜索条件的 Google 价格洞察；不是 FareScout 自建历史库或可售承诺。

## 研究循环与来源状态

- 根据证据 `6170786cb1a31ca1` 中的“大湾区”扩展搜索：**大湾区 日本 促销 出行日期 2027年1月21日**。理由：促销帖的适用出行日期到 2027 年 1 月 21 日、销售期到 2026 年 10 月 11 日，需确认 11 月是否仍在可订范围以及是否新增其他日本航点。

| 阶段 | 来源 | 状态 | 说明 |
|---|---|---|---|
| discovery | FareScout | ok | 已直接开始探索，无需先填写目的地或完整日期 |
| model | model | ok | 模型操作：patch |
| goal | FareScout | ok | 保留上下文：\[&#x27;HKG&#x27;\]；地区 JP；2026-11-01～2026-11-30；排除红眼 False |
| model | model | ok | 模型操作：plan |
| community_search | 小红书 / socai | info | 只读搜索：香港 日本 机票 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 机票 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_preview | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| source_retry | 小红书 / socai | failed | 前次未取得可读正文；有界重试：香港 日本 机票 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 机票 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_scan | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| evidence | 小红书 / socai | ok | 大湾区日本航点77折！冲绳东京大阪等都有！ |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| evidence | 小红书 / socai | ok | 香港往返东京/大阪机票¥685 |
| quality | FareScout | info | 出现商业/导流关键词；不等于虚假 |
| community_search | 小红书 / socai | ok | 查询 香港 日本 机票；已阅读 2 篇正文/评论 |
| community_search | 小红书 / socai | info | 只读搜索：香港飞日本 十一月 机票 便宜 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 十一月 机票 便宜 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_preview | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| social_read | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| evidence | 小红书 / socai | ok | 💰1200香港大阪往返机票🥹机票天才在评论区 |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| social_read | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| social_read | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| evidence | 小红书 / socai | ok | 快运｜香港大阪9折最低来回1.5K，跨国庆也有 |
| quality | FareScout | info | 价格可能依赖未分析图片 |
| community_search | 小红书 / socai | ok | 查询 香港飞日本 十一月 机票 便宜；已阅读 3 篇正文/评论 |
| model | model | ok | 模型操作：discover |
| extract | FareScout | ok | 从 4 篇已读内容筛选 1 个有引用的候选 |
| expansion_plan | FareScout | info | 促销帖的适用出行日期到 2027 年 1 月 21 日、销售期到 2026 年 10 月 11 日，需确认 11 月是否仍在可订范围以及是否新增其他日本航点。 |
| query_expansion | 小红书 / socai | info | 只读搜索：大湾区 日本 促销 出行日期 2027年1月21日 |
| source_query | 小红书 / socai | info | 实际社区关键词：大湾区 日本 促销 出行日期 2027年1月21日 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_preview | 小红书 / socai | failed | 命令超时 |
| source_retry | 小红书 / socai | failed | 逐篇读取未成功；仅回退一次socai完整扫描；有界重试：大湾区 日本 促销 出行日期 2027年1月21日 |
| source_query | 小红书 / socai | info | 实际社区关键词：大湾区 日本 促销 出行日期 2027年1月21日 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_scan | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| query_expansion | 小红书 / socai | failed | NO\_READABLE\_POSTS: 逐篇读取和完整扫描均未取得正文 |
| query_expansion | Reddit public | info | 只读搜索：大湾区 日本 促销 出行日期 2027年1月21日 |
| query_expansion | Reddit public | failed | ConnectTimeout: 来源调用失败；未保存可能含凭证的原始异常 |
| query_expansion | FareScout | info | 所有本轮社区来源失败；保留并尝试使用已有社区证据 |
| candidate | FareScout | ok | 两篇不同正文都提到香港—大阪，其中一篇给出 11 月 19-24 日与 11 月初的具体日期区间和港币价格，另一篇为覆盖 11 月的促销窗口；口径为往返，需按单程重新采样。 |
| date_exploration | SerpAPI | info | 范围粗筛 HKG-KIX；不假定逐日覆盖 |
| date_exploration | SerpAPI | ok | 范围结果实际含 1 个日期 |
| date_plan | FareScout | info | HKG-KIX 代表日：2026-11-04, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-KIX 2026-11-04 |
| date_exploration | SerpAPI | info | coarse：HKG-KIX 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-30：3 条匹配报价 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-04：3 条匹配报价 |
| date_exploration | SerpAPI | info | fine：HKG-KIX 2026-11-29 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-29：3 条匹配报价 |
| date_selected | FareScout | ok | HKG-KIX 选 2026-11-30 精确复验；仅为已查样本中的选择 |
| fare | FlyAI | info | verification：HKG-KIX 2026-11-30 |
| fare | FlyAI | ok | HKG-KIX 2026-11-30：3 条匹配报价 |
| fare | SerpAPI | ok | 复用本轮刚取得的同条件报价；保留原抓取时间 |
| coverage | FareScout | info | HKG-KIX 日期探索结束；未覆盖部分保持未知 |
| date_phase | FareScout | info | 日期探索与验价阶段实际用时（包含并发请求） |
| conflict | FareScout | info | 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conclusion | FareScout | ok | 有当前报价的候选不足3条；查询扩展未成功取得正文；至少3条路线的多日期有效覆盖尚未满足 |

停止原因：有当前报价的候选不足3条；查询扩展未成功取得正文；至少3条路线的多日期有效覆盖尚未满足

研究仅进行读取与搜索，没有下单、锁座、乘机人填写或支付。
