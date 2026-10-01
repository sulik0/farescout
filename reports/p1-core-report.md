# 飞探 FareScout 研究报告

**状态：complete** · 会话 `web-1790819986976` · 轮次 `27a8b798cf608c81`

需求：香港 11 月飞日本哪里便宜？

出发：HKG；地区：JP；日期：2026-11-01～2026-11-30；单程，1 成人，经济舱。

排除红眼：未要求。

研究开始：2026-10-01T01:59:47.026974+00:00；结束：2026-10-01T02:06:10.555961+00:00。

研究假设：

- 未指定行程：先比较 1 成人、经济舱、单程；不同口径不混比
- 日期窗口已收窄到 2026 年 11 月，精确报价仍按样本日期

调用统计（工具调用，不把范围请求展开成虚构的逐日调用）：

- 社区 3 次；日期探索 13 次；最终精确验价 6 次；模型操作 4 次。
- 本轮耗时 383.529 秒。

本轮整理 3 个调查方向，其中 3 个取得可核对的当前报价。

| 值得继续看的方向 | 当次各渠道最低报价（相互不作含税比较） |
|---|---|
| HKG → KIX | FlyAI / 飞猪 CNY 876（税费未确认）；Google Flights / SerpAPI CNY 893（含税） |
| HKG → NRT | FlyAI / 飞猪 CNY 829（税费未确认）；Google Flights / SerpAPI CNY 846（含税） |
| HKG → CTS | Google Flights / SerpAPI CNY 1351（含税） |

## 1. 香港 HKG → 大阪关西 KIX

**发现依据 / 社区出现价格（不是当前票价）**

从 4 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [乐桃偷偷大促！枫叶季往返大阪1.1k起！](https://www.xiaohongshu.com/explore/6aaa326300000000270179c2) · 小红书 / socai · 发布/更新：09-16 · 读取：2026-10-01T02:04:56.411462+00:00
  - 原文：• 香港 → 大阪：单程 HK$550起
  - 社区晒价：HK$550起；航司：未确认。
- [乐桃又大促！枫叶季往返大阪1.1k起！](https://www.xiaohongshu.com/explore/6aaa34ba000000002700857a) · 小红书 / socai · 发布/更新：09-16 · 读取：2026-10-01T02:04:56.411570+00:00
  - 原文：香港→大阪：单程 HK$550起
  - 社区晒价：HK$550起；航司：未确认。
- [快运｜香港大阪9折最低来回1.5K，跨国庆也有](https://www.xiaohongshu.com/explore/6ab4a8860000000015008f93) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:03:31.563574+00:00
  - 原文：闲日：10月底、11月初、12月初都有 1946HKD-200HKD（离境税），约等于1.5K
  - 社区晒价：1946HKD-200HKD；航司：未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-30。

实际精确请求日期（含失败）：2026-11-01, 2026-11-29, 2026-11-30；范围响应返回日期：2026-11-02, 2026-11-03, 2026-11-04, 2026-11-09, 2026-11-30。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-30 | FlyAI | range | ok | 876.0 / adult_fare_tax_unknown |
| 2026-11-02 | FlyAI | range | ok | 910.0 / adult_fare_tax_unknown |
| 2026-11-03 | FlyAI | range | ok | 910.0 / adult_fare_tax_unknown |
| 2026-11-04 | FlyAI | range | ok | 910.0 / adult_fare_tax_unknown |
| 2026-11-09 | FlyAI | range | ok | 910.0 / adult_fare_tax_unknown |
| 2026-11-01 | SerpAPI | coarse | ok | 952.0 / total_including_taxes |
| 2026-11-30 | SerpAPI | coarse | ok | 893.0 / total_including_taxes |
| 2026-11-29 | SerpAPI | fine | ok | 952.0 / total_including_taxes |
| 2026-11-30 | FlyAI | verification | ok | 876.0 / adult_fare_tax_unknown |
| 2026-11-30 | SerpAPI | verification | ok | 893.0 / total_including_taxes |

- **CNY 876**（票价，税费口径未确认）· [FlyAI / 飞猪](https://flyai.open.fliggy.com/) · 出发 2026-11-30 / 单程 · 查询 2026-10-01T02:05:49.265277+00:00
  - 乐桃航空 MM064：HKG 2026-11-30 12:45:00 → KIX 2026-11-30 17:10:00
  - 行李：未确认，不能假定包含托运行李。
  - FlyAI adultPrice/ticketPrice 报价；税费总额未确认，不能等同于含税总价
  - 未访问 jumpUrl 或任何预订页
  - FlyAI 体验模式：部分结果受限
- **CNY 893**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-30 / 单程 · 查询 2026-10-01T02:05:51.458687+00:00
  - Peach Aviation MM 64：HKG 2026-11-30 12:45 → KIX 2026-11-30 17:10
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程

**交叉验证与结论**

- 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。
- 社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。

值得继续关注的依据是存在社区线索，且本次查到可核对的航班报价。是否足够便宜还应结合你的预算和出行条件。

**主要限制**

- 仅核查列出的具体日期；不是整个日期窗口的最低价保证。
- 没有可靠典型价格，不声称历史低点或折扣幅度。
- 社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。
- 从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。
- 发布时间为页面原文；相对时间以抓取时间为参照

## 2. 香港 HKG → 东京成田 NRT

**发现依据 / 社区出现价格（不是当前票价）**

从 2 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [捡漏：2400拿下北海道东京大阪机票](https://www.xiaohongshu.com/explore/6ab54ad7000000001801a7da) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:02:47.439207+00:00
  - 原文：东京✈️香港1058
  - 社区晒价：1058；航司：未确认。
- [秋叶季香港大阪1.2 k](https://www.xiaohongshu.com/explore/6a8f0007000000002c03f78f) · 小红书 / socai · 发布/更新：08-26 · 读取：2026-10-01T02:03:31.563650+00:00
  - 原文：东京香港深圳有吗
  - 社区晒价：未取得可引用价格；航司：未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-01。

实际精确请求日期（含失败）：2026-11-01, 2026-11-02, 2026-11-30；范围响应返回日期：2026-11-02, 2026-11-25, 2026-11-30。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-02 | FlyAI | range | ok | 829.0 / adult_fare_tax_unknown |
| 2026-11-30 | FlyAI | range | ok | 1052.0 / adult_fare_tax_unknown |
| 2026-11-25 | FlyAI | range | ok | 1085.0 / adult_fare_tax_unknown |
| 2026-11-01 | SerpAPI | coarse | ok | 846.0 / total_including_taxes |
| 2026-11-02 | SerpAPI | coarse | ok | 846.0 / total_including_taxes |
| 2026-11-30 | SerpAPI | coarse | ok | 995.0 / total_including_taxes |
| 2026-11-01 | FlyAI | verification | ok | 829.0 / adult_fare_tax_unknown |
| 2026-11-01 | SerpAPI | verification | ok | 846.0 / total_including_taxes |

- **CNY 829**（票价，税费口径未确认）· [FlyAI / 飞猪](https://flyai.open.fliggy.com/) · 出发 2026-11-01 / 单程 · 查询 2026-10-01T02:05:53.200576+00:00
  - 香港快运 UO650：HKG 2026-11-01 14:00:00 → NRT 2026-11-01 19:05:00
  - 行李：未确认，不能假定包含托运行李。
  - FlyAI adultPrice/ticketPrice 报价；税费总额未确认，不能等同于含税总价
  - 未访问 jumpUrl 或任何预订页
  - FlyAI 体验模式：部分结果受限
- **CNY 846**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-01 / 单程 · 查询 2026-10-01T02:05:55.472206+00:00
  - Jetstar GK 28：HKG 2026-11-01 01:10 → NRT 2026-11-01 06:20
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程

**交叉验证与结论**

- 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。
- 社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。

值得继续关注的依据是存在社区线索，且本次查到可核对的航班报价。是否足够便宜还应结合你的预算和出行条件。

**主要限制**

- 仅核查列出的具体日期；不是整个日期窗口的最低价保证。
- 没有可靠典型价格，不声称历史低点或折扣幅度。
- 社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。
- 从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。
- 发布时间为页面原文；相对时间以抓取时间为参照
- 页面显示最后编辑时间，原发帖时间未知

## 3. 香港 HKG → 札幌新千岁 CTS

**发现依据 / 社区出现价格（不是当前票价）**

从 1 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [捡漏：2400拿下北海道东京大阪机票](https://www.xiaohongshu.com/explore/6ab54ad7000000001801a7da) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:02:47.439207+00:00
  - 原文：大阪✈️札幌268（其实支付宝当时255）
  - 社区晒价：268；航司：未确认。
- [捡漏：2400拿下北海道东京大阪机票](https://www.xiaohongshu.com/explore/6ab54ad7000000001801a7da) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-01T02:02:47.439207+00:00
  - 原文：三程都是廉航...这段时间广州深圳全日空飞北海道的很多2200左右的价格，最低2100都不到
  - 社区晒价：2200左右；航司：未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-29。

实际精确请求日期（含失败）：2026-11-01, 2026-11-13, 2026-11-29, 2026-11-30；范围响应返回日期：2026-11-13, 2026-11-16。

失败日期：2026-11-29。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-13 | FlyAI | range | ok | 1184.0 / adult_fare_tax_unknown |
| 2026-11-16 | FlyAI | range | ok | 1476.0 / adult_fare_tax_unknown |
| 2026-11-01 | SerpAPI | coarse | ok | 1486.0 / total_including_taxes |
| 2026-11-13 | SerpAPI | coarse | ok | 1541.0 / total_including_taxes |
| 2026-11-30 | SerpAPI | coarse | ok | 1392.0 / total_including_taxes |
| 2026-11-29 | SerpAPI | fine | ok | 1351.0 / total_including_taxes |
| 2026-11-29 | FlyAI | verification | failed | 未取得 / 未知 |
| 2026-11-29 | SerpAPI | verification | ok | 1351.0 / total_including_taxes |

- **CNY 1351**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-29 / 单程 · 查询 2026-10-01T02:06:10.549130+00:00
  - Jetstar GK 28：HKG 2026-11-29 01:10 → NRT 2026-11-29 06:20
  - Jetstar GK 105：NRT 2026-11-29 08:35 → CTS 2026-11-29 10:15
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程

**交叉验证与结论**

- 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。
- 社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。

值得继续关注的依据是存在社区线索，且本次查到可核对的航班报价。是否足够便宜还应结合你的预算和出行条件。

**主要限制**

- 仅核查列出的具体日期；不是整个日期窗口的最低价保证。
- 没有可靠典型价格，不声称历史低点或折扣幅度。
- 社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。
- 从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。
- 页面显示最后编辑时间，原发帖时间未知

## 研究循环与来源状态

- 根据证据 `d581b73988c36452` 中的“乐桃”扩展搜索：**乐桃 香港 大阪 11月 单程**。理由：乐桃促销公告写明出发期覆盖 2026/9/22–2027/1/31 且香港→大阪单程 HK$550 起，但抢票窗口为 9/17–9/20，需确认 11 月单程是否仍可购、是否仅限指定日期航班。

| 阶段 | 来源 | 状态 | 说明 |
|---|---|---|---|
| discovery | FareScout | ok | 已直接开始探索，无需先填写目的地或完整日期 |
| goal | FareScout | ok | 保留上下文：\[&#x27;HKG&#x27;\]；地区 JP；2026-11-01～2026-11-30；排除红眼 False |
| community_search | 小红书 / socai | info | 只读搜索：香港飞日本 机票 便宜 |
| source_retry | 小红书 / socai | info | 页面未稳定，去掉排序并改用短关键词重试：香港飞日本 机票 便宜 |
| community_search | 小红书 / socai | ok | 查询 香港飞日本 机票 便宜；已阅读 2 篇正文/评论 |
| evidence | 小红书 / socai | ok | 捡漏：2400拿下北海道东京大阪机票 |
| evidence | 小红书 / socai | ok | 香港往返东京/大阪机票¥685 |
| community_search | 小红书 / socai | info | 只读搜索：香港 日本 特价机票 11月 |
| community_search | 小红书 / socai | ok | 查询 香港 日本 特价机票 11月；已阅读 3 篇正文/评论 |
| evidence | 小红书 / socai | ok | 快运｜香港大阪9折最低来回1.5K，跨国庆也有 |
| evidence | 小红书 / socai | ok | 秋叶季香港大阪1.2 k |
| evidence | 小红书 / socai | ok | 乐桃偷偷大促！枫叶季往返大阪1.1k起！ |
| extract | FareScout | ok | 从 5 篇已读内容筛选 3 个有引用的候选 |
| expansion_plan | FareScout | info | 乐桃促销公告写明出发期覆盖 2026/9/22–2027/1/31 且香港→大阪单程 HK$550 起，但抢票窗口为 9/17–9/20，需确认 11 月单程是否仍可购、是否仅限指定日期航班。 |
| query_expansion | 小红书 / socai | info | 只读搜索：乐桃 香港 大阪 11月 单程 |
| query_expansion | 小红书 / socai | ok | 查询 乐桃 香港 大阪 11月 单程；已阅读 2 篇正文/评论 |
| evidence | 小红书 / socai | ok | 乐桃偷偷大促！枫叶季往返大阪1.1k起！ |
| evidence | 小红书 / socai | ok | 乐桃又大促！枫叶季往返大阪1.1k起！ |
| candidate | FareScout | ok | 多篇独立社区帖集中讨论香港—大阪关西线，且明确覆盖 11 月（含 11 月初闲日与 11 月下旬枫叶季），是本次 HKG 出发、11 月窗口内线索最密集的日本目的地；单程口径下乐桃去程 HK$550 起与快运九折活动均给出可核验的查询方向。 |
| candidate | FareScout | ok | 东京方向在社区帖中出现香港—东京航段价格与往返低价标题，且评论区有人主动询问东京/香港/深圳组合，说明需求与讨论存在；但相关帖多为 9 月发布、活动入口未证实，需按待验证线索调查 11 月可用性。 |
| candidate | FareScout | ok | 北海道在社区帖中被反复提及（含广州/深圳出发全日空飞北海道的价格讨论），说明 11 月前后存在北海道方向的低价讨论；但帖内香港出发段只到大阪，香港—札幌需作为待验证样本调查，不能视为社区已确认的香港直飞线索。 |
| date_exploration | FlyAI | info | 范围粗筛 HKG-KIX；不假定逐日覆盖 |
| date_exploration | FlyAI | ok | 范围结果实际含 5 个日期 |
| date_plan | FareScout | info | HKG-KIX 代表日：2026-11-01, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-KIX 2026-11-01 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-01：3 条匹配报价 |
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
| date_exploration | SerpAPI | info | fine：HKG-CTS 2026-11-29 |
| date_exploration | SerpAPI | ok | HKG-CTS 2026-11-29：3 条匹配报价 |
| date_selected | FareScout | ok | HKG-CTS 选 2026-11-29 精确复验；仅为已查样本中的选择 |
| fare | FlyAI | info | verification：HKG-CTS 2026-11-29 |
| fare | FlyAI | failed | API\_ERROR: FlyAI 未返回成功状态 |
| fare | SerpAPI | info | verification：HKG-CTS 2026-11-29 |
| fare | SerpAPI | ok | HKG-CTS 2026-11-29：3 条匹配报价 |
| coverage | FareScout | info | HKG-CTS 日期探索结束；未覆盖部分保持未知 |
| conflict | FareScout | info | 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| conflict | FareScout | info | 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| conflict | FareScout | info | 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| conclusion | FareScout | ok | 已完成有预算日期探索与候选验证；未覆盖日期保持未知 |

停止原因：已完成有预算日期探索与候选验证；未覆盖日期保持未知

研究仅进行读取与搜索，没有下单、锁座、乘机人填写或支付。
