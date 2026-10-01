# 飞探 FareScout 研究报告

**状态：complete** · 会话 `web-1790819986976` · 轮次 `b4d5e6155e8f8583`

需求：2026-11-01 至 2026-11-30，单程，不要红眼

出发：HKG；地区：JP；日期：2026-11-01～2026-11-30；单程，1 成人，经济舱。

排除红眼：是（任一段当地 22:00～06:00 或跨夜保守排除）。

研究开始：2026-10-01T02:48:19.643345+00:00；结束：2026-10-01T02:49:38.408287+00:00。

研究假设：

- 未指定行程：先比较 1 成人、经济舱、单程；不同口径不混比
- 用户日期窗 2026-11-01～2026-11-30；有预算采样，未覆盖日期未知

调用统计（工具调用，不把范围请求展开成虚构的逐日调用）：

- 社区 0 次；日期探索 14 次；最终精确验价 6 次；模型操作 2 次。
- 本轮耗时 78.765 秒。

- socai实际搜索命令 未记录 次（含重试）；模型实际请求 2 次（含Pydantic AI重试）。

约束解释：

| 字段 | 生效值 | 来源 | 规则 |
|---|---|---|---|
| origins | \[&#x27;HKG&#x27;\] | 沿用上下文 |  |
| region | JP | 沿用上下文 |  |
| date_from | 2026-11-01 | 用户明确 | 按明确日期生效 |
| date_to | 2026-11-30 | 用户明确 | 按明确日期生效 |
| date_mode | flexible | 用户明确 |  |
| trip_type | one\_way | 用户明确 | 默认1成人经济舱单程；往返须确认完整去回程 |
| stay_days | 5 | 沿用上下文 |  |
| no_red_eye | True | 用户明确 | 开启时排除任一航段当地22:00–06:00或跨夜；跨夜长途可能被保守排除 |

本轮整理 3 个调查方向，其中 3 个取得可核对的当前报价。

| 值得继续看的方向 | 当次各渠道最低报价（相互不作含税比较） |
|---|---|
| HKG → KIX | FlyAI / 飞猪 CNY 876（税费未确认）；Google Flights / SerpAPI CNY 893（含税） |
| HKG → NRT | FlyAI / 飞猪 CNY 829（税费未确认）；Google Flights / SerpAPI CNY 995（含税） |
| HKG → CTS | Google Flights / SerpAPI CNY 1542（含税） |

## 1. 香港 HKG → 大阪关西 KIX

**发现依据 / 社区出现价格（不是当前票价）**

从 4 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [乐桃偷偷大促！枫叶季往返大阪1.1k起！](https://www.xiaohongshu.com/explore/6aaa326300000000270179c2) · 小红书 / socai · 发布/更新：09-16 · 读取：2026-10-01T02:04:56.411462+00:00
  - 原文：• 香港 → 大阪：单程 HK$550起
  - 社区晒价：HK$550起；航司：未确认。
  - 证据质量：销售期日期/年份未完全确认；不能断言仍有效。不同正文，作者/活动来源独立性未确认。
- [乐桃又大促！枫叶季往返大阪1.1k起！](https://www.xiaohongshu.com/explore/6aaa34ba000000002700857a) · 小红书 / socai · 发布/更新：09-16 · 读取：2026-10-01T02:04:56.411570+00:00
  - 原文：香港→大阪：单程 HK$550起
  - 社区晒价：HK$550起；航司：未确认。
  - 证据质量：销售期日期/年份未完全确认；不能断言仍有效。不同正文，作者/活动来源独立性未确认。
- [快运｜香港大阪9折最低来回1.5K，跨国庆也有](https://www.xiaohongshu.com/explore/6ab4a8860000000015008f93) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:03:31.563574+00:00
  - 原文：闲日：10月底、11月初、12月初都有 1946HKD-200HKD（离境税），约等于1.5K
  - 社区晒价：1946HKD-200HKD；航司：未确认。
  - 证据质量：价格可能依赖未分析图片。不同正文，作者/活动来源独立性未确认。

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

- **CNY 876**（票价，税费口径未确认）· [FlyAI / 飞猪](https://flyai.open.fliggy.com/) · 出发 2026-11-30 / 单程 · 查询 2026-10-01T02:49:15.580094+00:00
  - 乐桃航空 MM064：HKG 2026-11-30 12:45:00 → KIX 2026-11-30 17:10:00
  - 行李：未确认，不能假定包含托运行李。
  - FlyAI adultPrice/ticketPrice 报价；税费总额未确认，不能等同于含税总价
  - 未访问 jumpUrl 或任何预订页
  - FlyAI 体验模式：部分结果受限
- **CNY 893**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-30 / 单程 · 查询 2026-10-01T02:49:22.961622+00:00
  - Peach Aviation MM 64：HKG 2026-11-30 12:45 → KIX 2026-11-30 17:10
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 640～1000；条件不齐，仅作为来源参考，不算折扣。

**交叉验证与结论**

- 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。
- 社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。

值得继续关注的依据是存在社区线索，且本次查到可核对的航班报价。是否足够便宜还应结合你的预算和出行条件。

**主要限制**

- 仅核查列出的具体日期；不是整个日期窗口的最低价保证。
- 社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。
- 没有本轮可比的可靠典型价格，不声称历史低点或折扣幅度。
- 从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。
- 发布时间为页面原文；相对时间以抓取时间为参照

Deal基础判断：**已验价，廉价程度未知**。未取得与本轮条件一致的可靠典型区间；不估算折扣。

## 2. 香港 HKG → 东京成田 NRT

**发现依据 / 社区出现价格（不是当前票价）**

从 2 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [捡漏：2400拿下北海道东京大阪机票](https://www.xiaohongshu.com/explore/6ab54ad7000000001801a7da) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:02:47.439207+00:00
  - 原文：函馆✈️东京498 东京✈️香港1058
  - 社区晒价：东京✈️香港1058；航司：未确认。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。
- [香港往返东京/大阪机票¥685](https://www.xiaohongshu.com/explore/6ab4d8a0000000001a032e79) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:02:47.439294+00:00
  - 原文：香港出发可退税200港币，即实付799港币，往返带托运  日本航空 &amp; 香港航空
  - 社区晒价：实付799港币；航司：未确认。
  - 证据质量：出现商业/导流关键词；不等于虚假。不同正文，作者/活动来源独立性未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-01。

实际精确请求日期（含失败）：2026-11-01, 2026-11-02, 2026-11-30；范围响应返回日期：2026-11-02, 2026-11-04, 2026-11-30。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-02 | FlyAI | range | ok | 829.0 / adult_fare_tax_unknown |
| 2026-11-30 | FlyAI | range | ok | 1052.0 / adult_fare_tax_unknown |
| 2026-11-04 | FlyAI | range | ok | 1085.0 / adult_fare_tax_unknown |
| 2026-11-01 | SerpAPI | coarse | ok | 995.0 / total_including_taxes |
| 2026-11-02 | SerpAPI | coarse | ok | 995.0 / total_including_taxes |
| 2026-11-30 | SerpAPI | coarse | ok | 995.0 / total_including_taxes |
| 2026-11-01 | FlyAI | verification | ok | 829.0 / adult_fare_tax_unknown |
| 2026-11-01 | SerpAPI | verification | ok | 995.0 / total_including_taxes |

- **CNY 829**（票价，税费口径未确认）· [FlyAI / 飞猪](https://flyai.open.fliggy.com/) · 出发 2026-11-01 / 单程 · 查询 2026-10-01T02:49:24.463362+00:00
  - 香港快运 UO650：HKG 2026-11-01 14:00:00 → NRT 2026-11-01 19:05:00
  - 行李：未确认，不能假定包含托运行李。
  - FlyAI adultPrice/ticketPrice 报价；税费总额未确认，不能等同于含税总价
  - 未访问 jumpUrl 或任何预订页
  - FlyAI 体验模式：部分结果受限
- **CNY 995**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-01 / 单程 · 查询 2026-10-01T02:49:27.009115+00:00
  - Hong Kong Express UO 650：HKG 2026-11-01 14:00 → NRT 2026-11-01 19:05
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 670～1150；条件不齐，仅作为来源参考，不算折扣。

**交叉验证与结论**

- 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。
- 社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。

值得继续关注的依据是存在社区线索，且本次查到可核对的航班报价。是否足够便宜还应结合你的预算和出行条件。

**主要限制**

- 仅核查列出的具体日期；不是整个日期窗口的最低价保证。
- 社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。
- 没有本轮可比的可靠典型价格，不声称历史低点或折扣幅度。
- 从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。
- 页面显示最后编辑时间，原发帖时间未知

Deal基础判断：**已验价，廉价程度未知**。未取得与本轮条件一致的可靠典型区间；不估算折扣。

## 3. 香港 HKG → 札幌新千岁 CTS

**发现依据 / 社区出现价格（不是当前票价）**

从 1 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [捡漏：2400拿下北海道东京大阪机票](https://www.xiaohongshu.com/explore/6ab54ad7000000001801a7da) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:02:47.439207+00:00
  - 原文：香港✈️大阪762（可退两百hkd） 大阪✈️札幌268（其实支付宝当时255）
  - 社区晒价：大阪✈️札幌268；航司：未确认。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。
- [捡漏：2400拿下北海道东京大阪机票](https://www.xiaohongshu.com/explore/6ab54ad7000000001801a7da) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:02:47.439207+00:00
  - 原文：三程都是廉航...这段时间广州深圳全日空飞北海道的很多2200左右的价格，最低2100都不到
  - 社区晒价：2200左右的价格；航司：未确认。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-01。

实际精确请求日期（含失败）：2026-11-01, 2026-11-02, 2026-11-13, 2026-11-30；范围响应返回日期：2026-11-13, 2026-11-16。

失败日期：2026-11-01。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-13 | FlyAI | range | ok | 1184.0 / adult_fare_tax_unknown |
| 2026-11-16 | FlyAI | range | ok | 2786.0 / adult_fare_tax_unknown |
| 2026-11-01 | SerpAPI | coarse | ok | 1541.0 / total_including_taxes |
| 2026-11-13 | SerpAPI | coarse | ok | 1541.0 / total_including_taxes |
| 2026-11-30 | SerpAPI | coarse | ok | 1926.0 / total_including_taxes |
| 2026-11-02 | SerpAPI | fine | ok | 1542.0 / total_including_taxes |
| 2026-11-01 | FlyAI | verification | failed | 未取得 / 未知 |
| 2026-11-01 | SerpAPI | verification | ok | 1542.0 / total_including_taxes |

- **CNY 1542**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-01 / 单程 · 查询 2026-10-01T02:49:38.400063+00:00
  - Trinity Airways TW 638：HKG 2026-11-01 13:45 → ICN 2026-11-01 18:35
  - Trinity Airways TW 263：ICN 2026-11-02 10:20 → CTS 2026-11-02 13:10
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 1050～1550；条件不齐，仅作为来源参考，不算折扣。

**交叉验证与结论**

- 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。
- 社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。

值得继续关注的依据是存在社区线索，且本次查到可核对的航班报价。是否足够便宜还应结合你的预算和出行条件。

**主要限制**

- 仅核查列出的具体日期；不是整个日期窗口的最低价保证。
- 社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。
- 没有本轮可比的可靠典型价格，不声称历史低点或折扣幅度。
- 从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。
- 页面显示最后编辑时间，原发帖时间未知

Deal基础判断：**已验价，廉价程度未知**。未取得与本轮条件一致的可靠典型区间；不估算折扣。

## 研究循环与来源状态


| 阶段 | 来源 | 状态 | 说明 |
|---|---|---|---|
| discovery | FareScout | ok | 已直接开始探索，无需先填写目的地或完整日期 |
| goal | FareScout | ok | 保留上下文：\[&#x27;HKG&#x27;\]；地区 JP；2026-11-01～2026-11-30；排除红眼 True |
| context | FareScout | ok | 沿用 6 篇原始社区证据；按本轮约束重新筛选并重新验价 |
| extract | FareScout | ok | 从 6 篇已读内容筛选 3 个有引用的候选 |
| candidate | FareScout | ok | 多篇独立社区帖集中讨论香港—大阪线，乐桃单程 HK$550 起的促销出发日期覆盖 2026/10/20–12/22，与用户 11 月窗口重叠；另有香港快运九折活动提到 11 月初闲日。均为社区晒价，需外部适配器核实 11 月单程实际可订日期与是否含托运。 |
| candidate | FareScout | ok | 有帖子提到东京—香港段价格与香港往返东京/大阪的退税后价位，东京方向存在多条独立讨论。该帖含赞助商关键词且评论追问年份，只能作为待验证线索，不能视为当前有效促销。 |
| candidate | FareScout | ok | 社区帖给出香港经大阪到札幌的分段低价线索，评论另提到广深飞北海道约 2200 的价位，说明北海道方向存在可拆段比价的可能。原帖未标注确切出行日期，需核实 11 月单程分段组合与是否红眼。 |
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
| date_exploration | FlyAI | info | 范围粗筛 HKG-CTS；不假定逐日覆盖 |
| date_exploration | FlyAI | ok | 范围结果实际含 2 个日期 |
| date_plan | FareScout | info | HKG-CTS 代表日：2026-11-01, 2026-11-13, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-CTS 2026-11-01 |
| date_exploration | SerpAPI | ok | HKG-CTS 2026-11-01：3 条匹配报价 |
| date_exploration | SerpAPI | info | coarse：HKG-CTS 2026-11-13 |
| date_exploration | SerpAPI | ok | HKG-CTS 2026-11-13：3 条匹配报价 |
| date_exploration | SerpAPI | info | coarse：HKG-CTS 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-CTS 2026-11-30：3 条匹配报价 |
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
| date_exploration | SerpAPI | info | fine：HKG-CTS 2026-11-02 |
| date_exploration | SerpAPI | ok | HKG-CTS 2026-11-02：2 条匹配报价 |
| date_selected | FareScout | ok | HKG-CTS 选 2026-11-01 精确复验；仅为已查样本中的选择 |
| fare | FlyAI | info | verification：HKG-CTS 2026-11-01 |
| fare | FlyAI | failed | API\_ERROR: FlyAI 未返回成功状态 |
| fare | SerpAPI | info | verification：HKG-CTS 2026-11-01 |
| fare | SerpAPI | ok | HKG-CTS 2026-11-01：3 条匹配报价 |
| coverage | FareScout | info | HKG-CTS 日期探索结束；未覆盖部分保持未知 |
| conflict | FareScout | info | 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 已验价，廉价程度未知 |
| conflict | FareScout | info | 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 已验价，廉价程度未知 |
| conflict | FareScout | info | 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 已验价，廉价程度未知 |
| conclusion | FareScout | ok | 已完成有预算日期探索与候选验证；未覆盖日期保持未知 |

停止原因：已完成有预算日期探索与候选验证；未覆盖日期保持未知

研究仅进行读取与搜索，没有下单、锁座、乘机人填写或支付。
