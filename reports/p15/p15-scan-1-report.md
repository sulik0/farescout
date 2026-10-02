# 飞探 FareScout 研究报告

**状态：partial** · 会话 `p15-scan-1` · 轮次 `320fca328812536d`

需求：香港 11 月飞日本哪里便宜？

出发：HKG；地区：JP；日期：2026-11-01～2026-11-30；单程，1 成人，经济舱。

排除红眼：未要求。

研究开始：2026-10-02T02:17:02.789408+00:00；结束：2026-10-02T02:22:47.229588+00:00。

研究假设：

- 未指定行程：先比较 1 成人、经济舱、单程；不同口径不混比
- 日期窗口已收窄到 2026 年 11 月，精确报价仍按样本日期

调用统计（工具调用，不把范围请求展开成虚构的逐日调用）：

- 社区 4 次；日期探索 20 次；最终精确验价 5 次；模型操作 3 次。
- 本轮耗时 344.44 秒。

- socai实际命令 10 次（含状态检查、搜索、正文读取与重试）；模型实际请求 3 次（含Pydantic AI重试）。
- 本轮报价复用 5 次；这些不是新增API调用，保留原抓取时间。
- 正文 5 篇；按已识别的转载/活动分为 4 组，未证明作者相互独立。

各类请求耗时：

| 请求类别 | 累计秒数 |
|---|---|
| browser_connection | 0.0 |
| 社区搜索（含读取） | 158.915 |
| 日期请求 | 53.174 |
| 日期阶段实际用时 | 49.13 |
| 最终验价 | 5.905 |
| 模型 | 8.199 |
| 扩展查询（含读取） | 128.174 |
| 社区完整扫描 | 271.939 |

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

本轮整理 5 个调查方向，其中 5 个取得可核对的当前报价。

| 值得继续看的方向 | 当次各渠道最低报价（相互不作含税比较） |
|---|---|
| HKG → OKA | Google Flights / SerpAPI CNY 739（含税） |
| HKG → FUK | FlyAI / 飞猪 CNY 816（税费未确认）；Google Flights / SerpAPI CNY 850（含税） |
| HKG → NRT | Google Flights / SerpAPI CNY 846（含税） |
| HKG → CTS | Google Flights / SerpAPI CNY 1218（含税） |
| HKG → KIX | FlyAI / 飞猪 CNY 876（税费未确认）；Google Flights / SerpAPI CNY 893（含税） |

## 1. 香港 HKG → 冲绳 OKA

**发现依据 / 社区出现价格（不是当前票价）**

从 3 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [大湾区航空｜77折，香港往返日本国庆最低1.4k](https://www.xiaohongshu.com/explore/6abc7c77000000001c00eb8e) · 小红书 / socai · 发布/更新：10-01 · 读取：2026-10-02T02:18:53.878396+00:00
  - 原文：\[赞R\]香港-冲绳来回 10月5日-10月9日（请两日）退税后约1457元
  - 社区晒价：1457元；航司：大湾区航空。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。
- [香港出发｜大湾区航空来回机票77折优惠](https://www.xiaohongshu.com/explore/6abb38f20000000014039915) · 小红书 / socai · 发布/更新：09-30 · 读取：2026-10-02T02:18:53.878544+00:00
  - 原文：适用航点（香港出发）： 曼谷、马尼拉、泗水、舟山、重庆、乌鲁木齐、昆明、台北、马尔代夫、东京、札幌、大阪、仙台、福冈及冲绳。
  - 社区晒价：未取得可引用价格；航司：大湾区航空。
  - 证据质量：正文不同但活动线索相同；按同一促销计数，作者关系未知。同一活动线索。
- [11月淡季也不便宜了](https://www.xiaohongshu.com/explore/6a798ae50000000032031a74) · 小红书 / socai · 发布/更新：08-10 · 读取：2026-10-02T02:19:43.416117+00:00
  - 原文：#香港快运 #冲绳 #冲绳旅游
  - 社区晒价：未取得可引用价格；航司：香港快运。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-04。

实际精确请求日期（含失败）：2026-11-04, 2026-11-05, 2026-11-30；范围响应返回日期：2026-11-04。

失败日期：2026-11-04。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-04 | SerpAPI / Google Travel Explore | range | ok | 739.0 / adult_fare_tax_unknown |
| 2026-11-30 | SerpAPI | coarse | ok | 739.0 / total_including_taxes |
| 2026-11-04 | SerpAPI | coarse | ok | 739.0 / total_including_taxes |
| 2026-11-05 | SerpAPI | fine | ok | 739.0 / total_including_taxes |
| 2026-11-04 | FlyAI | verification | failed | 未取得 / 未知 |
| 2026-11-04 | SerpAPI | verification | ok | 739.0 / total_including_taxes |

- **CNY 739**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-04 / 单程 · 查询 2026-10-02T02:22:04.934820+00:00
  - Hong Kong Express UO 824：HKG 2026-11-04 15:50 → OKA 2026-11-04 19:20
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 520～740；本轮同条件可比。

**交叉验证与结论**

- 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。
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

## 2. 香港 HKG → 福冈 FUK

**发现依据 / 社区出现价格（不是当前票价）**

从 2 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [大湾区航空｜77折，香港往返日本国庆最低1.4k](https://www.xiaohongshu.com/explore/6abc7c77000000001c00eb8e) · 小红书 / socai · 发布/更新：10-01 · 读取：2026-10-02T02:18:53.878396+00:00
  - 原文：\[赞R\]香港-福冈来回 10月3日-10月10日（请三日）退税后约1694元
  - 社区晒价：1694元；航司：大湾区航空。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。
- [香港出发｜大湾区航空来回机票77折优惠](https://www.xiaohongshu.com/explore/6abb38f20000000014039915) · 小红书 / socai · 发布/更新：09-30 · 读取：2026-10-02T02:18:53.878544+00:00
  - 原文：曼谷、马尼拉、泗水、舟山、重庆、乌鲁木齐、昆明、台北、马尔代夫、东京、札幌、大阪、仙台、福冈及冲绳。
  - 社区晒价：未取得可引用价格；航司：大湾区航空。
  - 证据质量：正文不同但活动线索相同；按同一促销计数，作者关系未知。同一活动线索。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-04。

实际精确请求日期（含失败）：2026-11-04, 2026-11-05, 2026-11-30；范围响应返回日期：2026-11-04。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-04 | SerpAPI / Google Travel Explore | range | ok | 850.0 / adult_fare_tax_unknown |
| 2026-11-30 | SerpAPI | coarse | ok | 1115.0 / total_including_taxes |
| 2026-11-04 | SerpAPI | coarse | ok | 850.0 / total_including_taxes |
| 2026-11-05 | SerpAPI | fine | ok | 850.0 / total_including_taxes |
| 2026-11-04 | FlyAI | verification | ok | 816.0 / adult_fare_tax_unknown |
| 2026-11-04 | SerpAPI | verification | ok | 850.0 / total_including_taxes |

- **CNY 816**（票价，税费口径未确认）· [FlyAI / 飞猪](https://flyai.open.fliggy.com/) · 出发 2026-11-04 / 单程 · 查询 2026-10-02T02:22:35.883845+00:00
  - 香港快运 UO638：HKG 2026-11-04 12:55:00 → FUK 2026-11-04 17:00:00
  - 行李：未确认，不能假定包含托运行李。
  - FlyAI adultPrice/ticketPrice 报价；税费总额未确认，不能等同于含税总价
  - 未访问 jumpUrl 或任何预订页
  - FlyAI 体验模式：部分结果受限
- **CNY 850**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-04 / 单程 · 查询 2026-10-02T02:22:12.539461+00:00
  - Hong Kong Express UO 638：HKG 2026-11-04 12:55 → FUK 2026-11-04 17:00
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 820～1050；本轮同条件可比。

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

## 3. 香港 HKG → 东京成田 NRT

**发现依据 / 社区出现价格（不是当前票价）**

从 2 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [大湾区航空｜77折，香港往返日本国庆最低1.4k](https://www.xiaohongshu.com/explore/6abc7c77000000001c00eb8e) · 小红书 / socai · 发布/更新：10-01 · 读取：2026-10-02T02:18:53.878396+00:00
  - 原文：\[赞R\]香港-东京来回 12月3日-12月8日（红叶）退税后约1781元
  - 社区晒价：1781元；航司：大湾区航空。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。
- [香港出发｜大湾区航空来回机票77折优惠](https://www.xiaohongshu.com/explore/6abb38f20000000014039915) · 小红书 / socai · 发布/更新：09-30 · 读取：2026-10-02T02:18:53.878544+00:00
  - 原文：曼谷、马尼拉、泗水、舟山、重庆、乌鲁木齐、昆明、台北、马尔代夫、东京、札幌、大阪、仙台、福冈及冲绳。
  - 社区晒价：未取得可引用价格；航司：大湾区航空。
  - 证据质量：正文不同但活动线索相同；按同一促销计数，作者关系未知。同一活动线索。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-14。

实际精确请求日期（含失败）：2026-11-14, 2026-11-15, 2026-11-30；范围响应返回日期：2026-11-14。

失败日期：2026-11-14。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-14 | SerpAPI / Google Travel Explore | range | ok | 846.0 / adult_fare_tax_unknown |
| 2026-11-30 | SerpAPI | coarse | ok | 846.0 / total_including_taxes |
| 2026-11-14 | SerpAPI | coarse | ok | 846.0 / total_including_taxes |
| 2026-11-15 | SerpAPI | fine | ok | 846.0 / total_including_taxes |
| 2026-11-14 | FlyAI | verification | failed | 未取得 / 未知 |
| 2026-11-14 | SerpAPI | verification | ok | 846.0 / total_including_taxes |

- **CNY 846**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-14 / 单程 · 查询 2026-10-02T02:22:17.352019+00:00
  - Jetstar GK 28：HKG 2026-11-14 01:10 → NRT 2026-11-14 06:20
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 670～1150；本轮同条件可比。

**交叉验证与结论**

- 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。
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

## 4. 香港 HKG → 札幌新千岁 CTS

**发现依据 / 社区出现价格（不是当前票价）**

从 2 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [大湾区航空｜77折，香港往返日本国庆最低1.4k](https://www.xiaohongshu.com/explore/6abc7c77000000001c00eb8e) · 小红书 / socai · 发布/更新：10-01 · 读取：2026-10-02T02:18:53.878396+00:00
  - 原文：\[赞R\]香港-札幌来回 11月12日-11月18日（可能有雪）退税后1742元
  - 社区晒价：1742元；航司：大湾区航空。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。
- [香港出发｜大湾区航空来回机票77折优惠](https://www.xiaohongshu.com/explore/6abb38f20000000014039915) · 小红书 / socai · 发布/更新：09-30 · 读取：2026-10-02T02:18:53.878544+00:00
  - 原文：曼谷、马尼拉、泗水、舟山、重庆、乌鲁木齐、昆明、台北、马尔代夫、东京、札幌、大阪、仙台、福冈及冲绳。
  - 社区晒价：未取得可引用价格；航司：大湾区航空。
  - 证据质量：正文不同但活动线索相同；按同一促销计数，作者关系未知。同一活动线索。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：2026-11-30。

实际精确请求日期（含失败）：2026-11-03, 2026-11-29, 2026-11-30；范围响应返回日期：2026-11-03。

失败日期：2026-11-30。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-03 | SerpAPI / Google Travel Explore | range | ok | 1227.0 / adult_fare_tax_unknown |
| 2026-11-30 | SerpAPI | coarse | ok | 1218.0 / total_including_taxes |
| 2026-11-03 | SerpAPI | coarse | ok | 1227.0 / total_including_taxes |
| 2026-11-29 | SerpAPI | fine | ok | 1227.0 / total_including_taxes |
| 2026-11-30 | FlyAI | verification | failed | 未取得 / 未知 |
| 2026-11-30 | SerpAPI | verification | ok | 1218.0 / total_including_taxes |

- **CNY 1218**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-30 / 单程 · 查询 2026-10-02T02:22:21.990048+00:00
  - Jetstar GK 28：HKG 2026-11-30 01:10 → NRT 2026-11-30 06:20
  - Jetstar GK 105：NRT 2026-11-30 08:35 → CTS 2026-11-30 10:15
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 1050～1600；本轮同条件可比。

**交叉验证与结论**

- 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。
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

## 5. 香港 HKG → 大阪关西 KIX

**发现依据 / 社区出现价格（不是当前票价）**

从 1 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [快运｜香港大阪9折最低来回1.5K，跨国庆也有](https://www.xiaohongshu.com/explore/6ab4a8860000000015008f93) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-02T02:19:43.416089+00:00
  - 原文：红叶季：11月19日-11月24日 2126HKD-200HKD（离境税），约等于1.6K
  - 社区晒价：2126HKD；航司：未确认。
  - 证据质量：价格可能依赖未分析图片。不同正文，作者/活动来源独立性未确认。
- [快运｜香港大阪9折最低来回1.5K，跨国庆也有](https://www.xiaohongshu.com/explore/6ab4a8860000000015008f93) · 小红书 / socai · 发布/更新：09-25 · 读取：2026-10-02T02:19:43.416089+00:00
  - 原文：闲日：10月底、11月初、12月初都有 1946HKD-200HKD（离境税），约等于1.5K
  - 社区晒价：1946HKD；航司：未确认。
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

- **CNY 876**（票价，税费口径未确认）· [FlyAI / 飞猪](https://flyai.open.fliggy.com/) · 出发 2026-11-30 / 单程 · 查询 2026-10-02T02:22:47.222718+00:00
  - 乐桃航空 MM064：HKG 2026-11-30 12:45:00 → KIX 2026-11-30 17:10:00
  - 行李：未确认，不能假定包含托运行李。
  - FlyAI adultPrice/ticketPrice 报价；税费总额未确认，不能等同于含税总价
  - 未访问 jumpUrl 或任何预订页
  - FlyAI 体验模式：部分结果受限
- **CNY 893**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-30 / 单程 · 查询 2026-10-02T02:22:27.786969+00:00
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

- 根据证据 `faa50028675b68ec` 中的“香港快运”扩展搜索：**香港快运 冲绳 11月 促销**。理由：有帖提到11月淡季冲绳价格与买两三程活动，需确认该活动在11月的可用日期与是否仍有效。

| 阶段 | 来源 | 状态 | 说明 |
|---|---|---|---|
| discovery | FareScout | ok | 已直接开始探索，无需先填写目的地或完整日期 |
| model | model | ok | 模型操作：patch |
| goal | FareScout | ok | 保留上下文：\[&#x27;HKG&#x27;\]；地区 JP；2026-11-01～2026-11-30；排除红眼 False |
| model | model | ok | 模型操作：plan |
| community_search | 小红书 / socai | info | 只读搜索：香港 日本 机票 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 机票 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_scan | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| source_retry | 小红书 / socai | failed | Search did not transition to a valid Xiaohongshu result page；有界重试：香港 日本 机票 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 机票 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_scan | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| evidence | 小红书 / socai | ok | 大湾区航空｜77折，香港往返日本国庆最低1.4k |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| evidence | 小红书 / socai | ok | 大湾区日本航点77折！冲绳东京大阪等都有！ |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| evidence | 小红书 / socai | ok | 香港出发｜大湾区航空来回机票77折优惠 |
| quality | FareScout | info | 正文不同但活动线索相同；按同一促销计数，作者关系未知 |
| community_search | 小红书 / socai | ok | 查询 香港 日本 机票；已阅读 3 篇正文/评论 |
| community_search | 小红书 / socai | info | 只读搜索：香港飞日本 十一月 便宜机票 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 十一月 便宜 机票 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_scan | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| evidence | 小红书 / socai | ok | 快运｜香港大阪9折最低来回1.5K，跨国庆也有 |
| quality | FareScout | info | 价格可能依赖未分析图片 |
| evidence | 小红书 / socai | ok | 11月淡季也不便宜了 |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| community_search | 小红书 / socai | ok | 查询 香港飞日本 十一月 便宜机票；已阅读 3 篇正文/评论 |
| model | model | ok | 模型操作：discover |
| extract | FareScout | ok | 从 5 篇已读内容筛选 5 个有引用的候选 |
| expansion_plan | FareScout | info | 有帖提到11月淡季冲绳价格与买两三程活动，需确认该活动在11月的可用日期与是否仍有效。 |
| query_expansion | 小红书 / socai | info | 只读搜索：香港快运 冲绳 11月 促销 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港快运 冲绳 11月 促销 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_scan | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| source_retry | 小红书 / socai | failed | Search did not transition to a valid Xiaohongshu result page；有界重试：香港快运 冲绳 促销 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港快运 冲绳 促销 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_scan | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| query_expansion | 小红书 / socai | failed | NO\_READABLE\_POSTS: 未取得可阅读的帖子正文；Search did not transition to a valid Xiaohongshu result page |
| query_expansion | Reddit public | info | 只读搜索：香港快运 冲绳 11月 促销 |
| query_expansion | Reddit public | failed | ConnectTimeout: 来源调用失败；未保存可能含凭证的原始异常 |
| query_expansion | FareScout | info | 所有本轮社区来源失败；保留并尝试使用已有社区证据 |
| candidate | FareScout | ok | 多篇社区帖提到香港出发冲绳的促销与价格线索，且冲绳在11月属淡季讨论范围；促销适用出行日期覆盖2026年11月，但需核实具体日期可用性与单程口径。 |
| candidate | FareScout | ok | 福冈在多个大湾区航空促销帖中被列为适用航点并给出往返价格参考，出行日期窗口覆盖11月，值得作为候选目的地核实单程可用日期。 |
| candidate | FareScout | ok | 东京在多个促销帖中被列为适用航点并有往返价格参考；社区未指定成田或羽田，此处以成田作为待验证样本，需核实11月单程可用日期。 |
| candidate | FareScout | ok | 有帖子给出11月12-18日香港-札幌往返价格线索，正好落在11月窗口内；札幌也在促销适用航点列表中，适合核实单程与具体日期。 |
| candidate | FareScout | ok | 有帖子明确给出11月19-24日大阪往返价格线索，且11月初被列为闲日；另有促销把大阪列为适用航点，适合核实11月单程可用性。 |
| date_exploration | SerpAPI | info | 范围粗筛 HKG-OKA；不假定逐日覆盖 |
| date_exploration | SerpAPI | ok | 范围结果实际含 1 个日期 |
| date_plan | FareScout | info | HKG-OKA 代表日：2026-11-04, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-OKA 2026-11-04 |
| date_exploration | SerpAPI | info | coarse：HKG-OKA 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-OKA 2026-11-30：3 条匹配报价 |
| date_exploration | SerpAPI | ok | HKG-OKA 2026-11-04：3 条匹配报价 |
| date_exploration | SerpAPI | info | 范围粗筛 HKG-FUK；不假定逐日覆盖 |
| date_exploration | SerpAPI | ok | 范围结果实际含 1 个日期 |
| date_plan | FareScout | info | HKG-FUK 代表日：2026-11-04, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-FUK 2026-11-04 |
| date_exploration | SerpAPI | info | coarse：HKG-FUK 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-FUK 2026-11-30：3 条匹配报价 |
| date_exploration | SerpAPI | ok | HKG-FUK 2026-11-04：3 条匹配报价 |
| date_exploration | SerpAPI | info | 范围粗筛 HKG-NRT；不假定逐日覆盖 |
| date_exploration | SerpAPI | ok | 范围结果实际含 1 个日期 |
| date_plan | FareScout | info | HKG-NRT 代表日：2026-11-14, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-NRT 2026-11-14 |
| date_exploration | SerpAPI | info | coarse：HKG-NRT 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-NRT 2026-11-30：3 条匹配报价 |
| date_exploration | SerpAPI | ok | HKG-NRT 2026-11-14：3 条匹配报价 |
| date_exploration | SerpAPI | info | 范围粗筛 HKG-CTS；不假定逐日覆盖 |
| date_exploration | SerpAPI | ok | 范围结果实际含 1 个日期 |
| date_plan | FareScout | info | HKG-CTS 代表日：2026-11-03, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-CTS 2026-11-03 |
| date_exploration | SerpAPI | info | coarse：HKG-CTS 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-CTS 2026-11-30：3 条匹配报价 |
| date_exploration | SerpAPI | ok | HKG-CTS 2026-11-03：3 条匹配报价 |
| date_exploration | SerpAPI | info | 范围粗筛 HKG-KIX；不假定逐日覆盖 |
| date_exploration | SerpAPI | ok | 范围结果实际含 1 个日期 |
| date_plan | FareScout | info | HKG-KIX 代表日：2026-11-04, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-KIX 2026-11-04 |
| date_exploration | SerpAPI | info | coarse：HKG-KIX 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-30：3 条匹配报价 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-04：3 条匹配报价 |
| date_exploration | SerpAPI | info | fine：HKG-OKA 2026-11-05 |
| date_exploration | SerpAPI | ok | HKG-OKA 2026-11-05：3 条匹配报价 |
| date_selected | FareScout | ok | HKG-OKA 选 2026-11-04 精确复验；仅为已查样本中的选择 |
| fare | FlyAI | info | verification：HKG-OKA 2026-11-04 |
| fare | FlyAI | failed | API\_ERROR: FlyAI 未返回成功状态 |
| fare | SerpAPI | ok | 复用本轮刚取得的同条件报价；保留原抓取时间 |
| coverage | FareScout | info | HKG-OKA 日期探索结束；未覆盖部分保持未知 |
| date_exploration | SerpAPI | info | fine：HKG-FUK 2026-11-05 |
| date_exploration | SerpAPI | ok | HKG-FUK 2026-11-05：3 条匹配报价 |
| date_selected | FareScout | ok | HKG-FUK 选 2026-11-04 精确复验；仅为已查样本中的选择 |
| fare | FlyAI | info | verification：HKG-FUK 2026-11-04 |
| fare | FlyAI | ok | HKG-FUK 2026-11-04：3 条匹配报价 |
| fare | SerpAPI | ok | 复用本轮刚取得的同条件报价；保留原抓取时间 |
| coverage | FareScout | info | HKG-FUK 日期探索结束；未覆盖部分保持未知 |
| date_exploration | SerpAPI | info | fine：HKG-NRT 2026-11-15 |
| date_exploration | SerpAPI | ok | HKG-NRT 2026-11-15：3 条匹配报价 |
| date_selected | FareScout | ok | HKG-NRT 选 2026-11-14 精确复验；仅为已查样本中的选择 |
| fare | FlyAI | info | verification：HKG-NRT 2026-11-14 |
| fare | FlyAI | failed | API\_ERROR: FlyAI 未返回成功状态 |
| fare | SerpAPI | ok | 复用本轮刚取得的同条件报价；保留原抓取时间 |
| coverage | FareScout | info | HKG-NRT 日期探索结束；未覆盖部分保持未知 |
| date_exploration | SerpAPI | info | fine：HKG-CTS 2026-11-29 |
| date_exploration | SerpAPI | ok | HKG-CTS 2026-11-29：3 条匹配报价 |
| date_selected | FareScout | ok | HKG-CTS 选 2026-11-30 精确复验；仅为已查样本中的选择 |
| fare | FlyAI | info | verification：HKG-CTS 2026-11-30 |
| fare | FlyAI | failed | API\_ERROR: FlyAI 未返回成功状态 |
| fare | SerpAPI | ok | 复用本轮刚取得的同条件报价；保留原抓取时间 |
| coverage | FareScout | info | HKG-CTS 日期探索结束；未覆盖部分保持未知 |
| date_exploration | SerpAPI | info | fine：HKG-KIX 2026-11-29 |
| date_exploration | SerpAPI | ok | HKG-KIX 2026-11-29：3 条匹配报价 |
| date_selected | FareScout | ok | HKG-KIX 选 2026-11-30 精确复验；仅为已查样本中的选择 |
| fare | FlyAI | info | verification：HKG-KIX 2026-11-30 |
| fare | FlyAI | ok | HKG-KIX 2026-11-30：3 条匹配报价 |
| fare | SerpAPI | ok | 复用本轮刚取得的同条件报价；保留原抓取时间 |
| coverage | FareScout | info | HKG-KIX 日期探索结束；未覆盖部分保持未知 |
| date_phase | FareScout | info | 日期探索与验价阶段实际用时（包含并发请求） |
| conflict | FareScout | info | 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conflict | FareScout | info | 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conflict | FareScout | info | 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conflict | FareScout | info | 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conflict | FareScout | info | 实时渠道税费口径不同，分别展示，不能直接合成价格区间或节省金额。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conclusion | FareScout | ok | 查询扩展未成功取得正文 |

停止原因：查询扩展未成功取得正文

研究仅进行读取与搜索，没有下单、锁座、乘机人填写或支付。
