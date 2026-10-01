# 飞探 FareScout 研究报告

**状态：partial** · 会话 `web-1790821711900` · 轮次 `c31de69beb24714f`

需求：香港 11 月飞日本哪里便宜？

出发：HKG；地区：JP；日期：2026-11-01～2026-11-30；单程，1 成人，经济舱。

排除红眼：未要求。

研究开始：2026-10-01T02:28:31.967137+00:00；结束：2026-10-01T02:34:16.260449+00:00。

研究假设：

- 未指定行程：先比较 1 成人、经济舱、单程；不同口径不混比
- 日期窗口已收窄到 2026 年 11 月，精确报价仍按样本日期

调用统计（工具调用，不把范围请求展开成虚构的逐日调用）：

- 社区 4 次；日期探索 9 次；最终精确验价 4 次；模型操作 3 次。
- 本轮耗时 344.293 秒。

- socai实际搜索命令 4 次（含重试）；模型实际请求 3 次（含Pydantic AI重试）。

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

本轮整理 2 个调查方向，其中 2 个取得可核对的当前报价。

| 值得继续看的方向 | 当次各渠道最低报价（相互不作含税比较） |
|---|---|
| HKG → KIX | FlyAI / 飞猪 CNY 876（税费未确认）；Google Flights / SerpAPI CNY 893（含税） |
| HKG → NRT | FlyAI / 飞猪 CNY 829（税费未确认）；Google Flights / SerpAPI CNY 846（含税） |

**尚未满足 3～5 个有价格证据的机会要求。不会用社区晒价补齐当前价格。**

## 1. 香港 HKG → 大阪关西 KIX

**发现依据 / 社区出现价格（不是当前票价）**

从 2 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [快运｜香港大阪9折最低来回1.5K，跨国庆也有](https://www.xiaohongshu.com/explore/6ab4a8860000000015008f93) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:33:30.888108+00:00
  - 原文：闲日：10月底、11月初、12月初都有 1946HKD-200HKD（离境税），约等于1.5K
  - 社区晒价：1946HKD；航司：未确认。
  - 证据质量：价格可能依赖未分析图片。不同正文，作者/活动来源独立性未确认。
- [快运｜香港大阪9折最低来回1.5K，跨国庆也有](https://www.xiaohongshu.com/explore/6ab4a8860000000015008f93) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:33:30.888108+00:00
  - 原文：红叶季：11月19日-11月24日 2126HKD-200HKD（离境税），约等于1.6K
  - 社区晒价：2126HKD；航司：未确认。
  - 证据质量：价格可能依赖未分析图片。不同正文，作者/活动来源独立性未确认。
- [💰1200香港大阪往返机票🥹机票天才在评论区](https://www.xiaohongshu.com/explore/6a865d6500000000140265f9) · 小红书 / socai · 发布/更新：09-08 · 读取：2026-10-01T02:33:30.888157+00:00
  - 原文：💰去程747返程636，共计1373，香港离境税退200hk，基本就是1200元
  - 社区晒价：1373；航司：未确认。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-30。

实际精确请求日期（含失败）：2026-11-01, 2026-11-15, 2026-11-29, 2026-11-30；范围响应返回日期：2026-11-01, 2026-11-02, 2026-11-03, 2026-11-04, 2026-11-30。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-30 | FlyAI | range | ok | 876.0 / adult_fare_tax_unknown |
| 2026-11-01 | FlyAI | range | ok | 910.0 / adult_fare_tax_unknown |
| 2026-11-02 | FlyAI | range | ok | 910.0 / adult_fare_tax_unknown |
| 2026-11-03 | FlyAI | range | ok | 910.0 / adult_fare_tax_unknown |
| 2026-11-04 | FlyAI | range | ok | 910.0 / adult_fare_tax_unknown |
| 2026-11-01 | SerpAPI | coarse | ok | 952.0 / total_including_taxes |
| 2026-11-15 | SerpAPI | coarse | ok | 952.0 / total_including_taxes |
| 2026-11-30 | SerpAPI | coarse | ok | 893.0 / total_including_taxes |
| 2026-11-29 | SerpAPI | fine | ok | 952.0 / total_including_taxes |
| 2026-11-30 | FlyAI | verification | ok | 876.0 / adult_fare_tax_unknown |
| 2026-11-30 | SerpAPI | verification | ok | 893.0 / total_including_taxes |

- **CNY 876**（票价，税费口径未确认）· [FlyAI / 飞猪](https://flyai.open.fliggy.com/) · 出发 2026-11-30 / 单程 · 查询 2026-10-01T02:34:09.155366+00:00
  - 乐桃航空 MM064：HKG 2026-11-30 12:45:00 → KIX 2026-11-30 17:10:00
  - 行李：未确认，不能假定包含托运行李。
  - FlyAI adultPrice/ticketPrice 报价；税费总额未确认，不能等同于含税总价
  - 未访问 jumpUrl 或任何预订页
  - FlyAI 体验模式：部分结果受限
- **CNY 893**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-30 / 单程 · 查询 2026-10-01T02:34:12.236159+00:00
  - Peach Aviation MM 64：HKG 2026-11-30 12:45 → KIX 2026-11-30 17:10
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 640～1000；本轮同条件可比。

**交叉验证与结论**

- 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。
- 社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。

值得继续关注的依据是存在社区线索，且本次查到可核对的航班报价。是否足够便宜还应结合你的预算和出行条件。

**主要限制**

- 仅核查列出的具体日期；不是整个日期窗口的最低价保证。
- 社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。
- 典型价格仅来自Google本次同条件洞察；不代表自建历史库、历史最低或库存保证。
- 从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。
- 发布时间为页面原文；相对时间以抓取时间为参照
- 页面显示最后编辑时间，原发帖时间未知

Deal基础判断：**处于 Google 典型区间**。同一搜索条件的 Google 价格洞察；不是 FareScout 自建历史库或可售承诺。

## 2. 香港 HKG → 东京成田 NRT

**发现依据 / 社区出现价格（不是当前票价）**

从 1 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [抢到了trip香港往返东京680的机票！](https://www.xiaohongshu.com/explore/6aa100820000000028003f9f) · 小红书 / socai · 发布/更新：09-09 · 读取：2026-10-01T02:32:39.298194+00:00
  - 原文：999hkd-200hkd离境税 到手680
  - 社区晒价：680；航司：日本航空。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-01。

实际精确请求日期（含失败）：2026-11-01, 2026-11-02, 2026-11-30；范围响应返回日期：2026-11-02, 2026-11-04, 2026-11-30。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-02 | FlyAI | range | ok | 829.0 / adult_fare_tax_unknown |
| 2026-11-30 | FlyAI | range | ok | 1052.0 / adult_fare_tax_unknown |
| 2026-11-04 | FlyAI | range | ok | 1085.0 / adult_fare_tax_unknown |
| 2026-11-01 | SerpAPI | coarse | ok | 846.0 / total_including_taxes |
| 2026-11-02 | SerpAPI | coarse | ok | 846.0 / total_including_taxes |
| 2026-11-30 | SerpAPI | coarse | ok | 995.0 / total_including_taxes |
| 2026-11-01 | FlyAI | verification | ok | 829.0 / adult_fare_tax_unknown |
| 2026-11-01 | SerpAPI | verification | ok | 846.0 / total_including_taxes |

- **CNY 829**（票价，税费口径未确认）· [FlyAI / 飞猪](https://flyai.open.fliggy.com/) · 出发 2026-11-01 / 单程 · 查询 2026-10-01T02:34:14.071054+00:00
  - 香港快运 UO650：HKG 2026-11-01 14:00:00 → NRT 2026-11-01 19:05:00
  - 行李：未确认，不能假定包含托运行李。
  - FlyAI adultPrice/ticketPrice 报价；税费总额未确认，不能等同于含税总价
  - 未访问 jumpUrl 或任何预订页
  - FlyAI 体验模式：部分结果受限
- **CNY 846**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-01 / 单程 · 查询 2026-10-01T02:34:16.256749+00:00
  - Jetstar GK 28：HKG 2026-11-01 01:10 → NRT 2026-11-01 06:20
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 670～1150；本轮同条件可比。

**交叉验证与结论**

- 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。
- 社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。

值得继续关注的依据是存在社区线索，且本次查到可核对的航班报价。是否足够便宜还应结合你的预算和出行条件。

**主要限制**

- 仅核查列出的具体日期；不是整个日期窗口的最低价保证。
- 社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。
- 典型价格仅来自Google本次同条件洞察；不代表自建历史库、历史最低或库存保证。
- 从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。
- 发布时间为页面原文；相对时间以抓取时间为参照

Deal基础判断：**处于 Google 典型区间**。同一搜索条件的 Google 价格洞察；不是 FareScout 自建历史库或可售承诺。

## 研究循环与来源状态


| 阶段 | 来源 | 状态 | 说明 |
|---|---|---|---|
| discovery | FareScout | ok | 已直接开始探索，无需先填写目的地或完整日期 |
| goal | FareScout | ok | 保留上下文：\[&#x27;HKG&#x27;\]；地区 JP；2026-11-01～2026-11-30；排除红眼 False |
| community_search | 小红书 / socai | info | 只读搜索：香港 日本 机票 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 机票 |
| source_retry | 小红书 / socai | failed | 前次命令超时；有界重试：香港 日本 机票 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 机票 |
| community_search | 小红书 / socai | failed | NO\_READABLE\_POSTS: 未取得可阅读的帖子正文；可能需要登录、人工验证或站点适配更新 |
| community_search | Reddit public | info | 只读搜索：香港 日本 机票 |
| community_search | Reddit public | failed | ConnectTimeout: 来源调用失败；未保存可能含凭证的原始异常 |
| community_search | FareScout | info | 所有本轮社区来源失败；保留并尝试使用已有社区证据 |
| community_search | 小红书 / socai | info | 只读搜索：香港飞日本 机票 便宜 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 机票 便宜 |
| community_search | 小红书 / socai | ok | 查询 香港飞日本 机票 便宜；已阅读 3 篇正文/评论 |
| evidence | 小红书 / socai | ok | 大湾区日本航点77折！冲绳东京大阪等都有！ |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| evidence | 小红书 / socai | ok | 💰1200香港大阪往返机票🥹机票天才在评论区 |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| evidence | 小红书 / socai | ok | 抢到了trip香港往返东京680的机票！ |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| plan | FareScout | info | 宽查询来源失败，补一次更短的同范围社区查询 |
| community_search | 小红书 / socai | info | 只读搜索：香港 日本 机票 捡漏 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 机票 捡漏 |
| community_search | 小红书 / socai | ok | 查询 香港 日本 机票 捡漏；已阅读 3 篇正文/评论 |
| evidence | 小红书 / socai | ok | 大湾区日本航点77折！冲绳东京大阪等都有！ |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| evidence | 小红书 / socai | ok | 快运｜香港大阪9折最低来回1.5K，跨国庆也有 |
| quality | FareScout | info | 价格可能依赖未分析图片 |
| evidence | 小红书 / socai | ok | 💰1200香港大阪往返机票🥹机票天才在评论区 |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| extract | FareScout | ok | 从 4 篇已读内容筛选 2 个有引用的候选 |
| candidate | FareScout | ok | 多篇独立讨论指向香港-大阪：快运9折覆盖11月初与11月19-24日，另有往返约1200-1373元的廉航晒价；均为往返口径，需按单程重新核验。 |
| candidate | FareScout | ok | 促销帖把东京列入1.6k往返档，另有香港往返东京680元的晒价（含离境税退还口径）；东京为11月热门航点，值得按单程样本日期核验。 |
| date_exploration | FlyAI | info | 范围粗筛 HKG-KIX；不假定逐日覆盖 |
| date_exploration | FlyAI | ok | 范围结果实际含 5 个日期 |
| date_plan | FareScout | info | HKG-KIX 代表日：2026-11-01, 2026-11-15, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-KIX 2026-11-01 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-01：3 条匹配报价 |
| date_exploration | SerpAPI | info | coarse：HKG-KIX 2026-11-15 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-15：3 条匹配报价 |
| date_exploration | SerpAPI | info | coarse：HKG-KIX 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-30：3 条匹配报价 |
| date_exploration | FlyAI | info | 范围粗筛 HKG-NRT；不假定逐日覆盖 |
| date_exploration | FlyAI | ok | 范围结果实际含 3 个日期 |
| date_plan | FareScout | info | HKG-NRT 代表日：2026-11-01, 2026-11-02, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-NRT 2026-11-01 |
| date_exploration | SerpAPI | ok | HKG-NRT 2026-11-01：3 条匹配报价 |
| date_exploration | SerpAPI | info | coarse：HKG-NRT 2026-11-02 |
| date_exploration | SerpAPI | ok | HKG-NRT 2026-11-02：3 条匹配报价 |
| date_exploration | SerpAPI | info | coarse：HKG-NRT 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-NRT 2026-11-30：3 条匹配报价 |
| date_exploration | SerpAPI | info | fine：HKG-KIX 2026-11-29 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-29：3 条匹配报价 |
| date_selected | FareScout | ok | HKG-KIX 选 2026-11-30 精确复验；仅为已查样本中的选择 |
| fare | FlyAI | info | verification：HKG-KIX 2026-11-30 |
| fare | FlyAI | ok | HKG-KIX 2026-11-30：3 条匹配报价 |
| fare | SerpAPI | info | verification：HKG-KIX 2026-11-30 |
| fare | SerpAPI | ok | HKG-KIX 2026-11-30：3 条匹配报价 |
| coverage | FareScout | info | HKG-KIX 日期探索结束；未覆盖部分保持未知 |
| date_selected | FareScout | ok | HKG-NRT 选 2026-11-01 精确复验；仅为已查样本中的选择 |
| fare | FlyAI | info | verification：HKG-NRT 2026-11-01 |
| fare | FlyAI | ok | HKG-NRT 2026-11-01：3 条匹配报价 |
| fare | SerpAPI | info | verification：HKG-NRT 2026-11-01 |
| fare | SerpAPI | ok | HKG-NRT 2026-11-01：3 条匹配报价 |
| coverage | FareScout | info | HKG-NRT 日期探索结束；未覆盖部分保持未知 |
| conflict | FareScout | info | 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conflict | FareScout | info | 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conclusion | FareScout | ok | 有当前报价的候选不足3条；查询扩展未成功取得正文；至少3条路线的多日期有效覆盖尚未满足 |

停止原因：有当前报价的候选不足3条；查询扩展未成功取得正文；至少3条路线的多日期有效覆盖尚未满足

研究仅进行读取与搜索，没有下单、锁座、乘机人填写或支付。
