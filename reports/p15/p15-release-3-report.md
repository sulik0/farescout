# 飞探 FareScout 研究报告

**状态：partial** · 会话 `p15-release-3` · 轮次 `a56ec8d672eb1b44`

需求：香港 11 月飞日本哪里便宜？

出发：HKG；地区：JP；日期：2026-11-01～2026-11-30；单程，1 成人，经济舱。

排除红眼：未要求。

研究开始：2026-10-02T02:07:57.317659+00:00；结束：2026-10-02T02:15:57.311011+00:00。

研究假设：

- 未指定行程：先比较 1 成人、经济舱、单程；不同口径不混比
- 日期窗口已收窄到 2026 年 11 月，精确报价仍按样本日期

调用统计（工具调用，不把范围请求展开成虚构的逐日调用）：

- 社区 5 次；日期探索 13 次；最终精确验价 0 次；模型操作 3 次。
- 本轮耗时 479.993 秒。

- socai实际命令 18 次（含状态检查、搜索、正文读取与重试）；模型实际请求 3 次（含Pydantic AI重试）。
- 本轮报价复用 0 次；这些不是新增API调用，保留原抓取时间。
- 正文 3 篇；按已识别的转载/活动分为 2 组，未证明作者相互独立。

各类请求耗时：

| 请求类别 | 累计秒数 |
|---|---|
| browser_connection | 0.0 |
| 社区搜索（含读取） | 351.662 |
| 日期请求 | 36.172 |
| 日期阶段实际用时 | 31.248 |
| 模型 | 7.716 |
| 扩展查询（含读取） | 89.346 |
| 搜索卡片 | 208.911 |
| 社区完整扫描 | 216.875 |

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

本轮整理 5 个调查方向，其中 4 个取得可核对的当前报价。

| 值得继续看的方向 | 当次各渠道最低报价（相互不作含税比较） |
|---|---|
| HKG → OKA | Google Flights / SerpAPI CNY 739（含税） |
| HKG → FUK | Google Flights / SerpAPI CNY 850（含税） |
| HKG → NRT | Google Flights / SerpAPI CNY 846（含税） |
| HKG → CTS | Google Flights / SerpAPI CNY 1218（含税） |
| HKG → KIX | 当前未验证 |

## 1. 香港 HKG → 冲绳 OKA

**发现依据 / 社区出现价格（不是当前票价）**

从 1 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [大湾区航空｜77折，香港往返日本国庆最低1.4k](https://www.xiaohongshu.com/explore/6abc7c77000000001c00eb8e) · 小红书 / socai · 发布/更新：10-01 · 读取：2026-10-02T02:09:27.941874+00:00
  - 原文：\[赞R\]香港-冲绳来回 10月5日-10月9日（请两日）退税后约1457元
  - 社区晒价：1457元；航司：大湾区航空。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：未选定。

实际精确请求日期（含失败）：2026-11-04, 2026-11-30；范围响应返回日期：2026-11-04。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-04 | SerpAPI / Google Travel Explore | range | ok | 739.0 / adult_fare_tax_unknown |
| 2026-11-04 | SerpAPI | coarse | ok | 739.0 / total_including_taxes |
| 2026-11-30 | SerpAPI | coarse | ok | 739.0 / total_including_taxes |

- **CNY 739**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-04 / 单程 · 查询 2026-10-02T02:15:31.474745+00:00
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

从 1 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [大湾区航空｜77折，香港往返日本国庆最低1.4k](https://www.xiaohongshu.com/explore/6abc7c77000000001c00eb8e) · 小红书 / socai · 发布/更新：10-01 · 读取：2026-10-02T02:09:27.941874+00:00
  - 原文：\[赞R\]香港-福冈来回 10月3日-10月10日（请三日）退税后约1694元
  - 社区晒价：1694元；航司：大湾区航空。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：未选定。

实际精确请求日期（含失败）：2026-11-04, 2026-11-30；范围响应返回日期：2026-11-04。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-04 | SerpAPI / Google Travel Explore | range | ok | 850.0 / adult_fare_tax_unknown |
| 2026-11-04 | SerpAPI | coarse | ok | 850.0 / total_including_taxes |
| 2026-11-30 | SerpAPI | coarse | ok | 1115.0 / total_including_taxes |

- **CNY 850**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-04 / 单程 · 查询 2026-10-02T02:15:37.544860+00:00
  - Hong Kong Express UO 638：HKG 2026-11-04 12:55 → FUK 2026-11-04 17:00
  - 行李：未确认，不能假定包含托运行李。
  - 航班搜索报价；额外行李/支付方式等费用可能另计
  - 只读搜索，未进入预订流程
  - Google典型区间：CNY 820～1050；本轮同条件可比。

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

## 3. 香港 HKG → 东京成田 NRT

**发现依据 / 社区出现价格（不是当前票价）**

从 1 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [大湾区航空｜77折，香港往返日本国庆最低1.4k](https://www.xiaohongshu.com/explore/6abc7c77000000001c00eb8e) · 小红书 / socai · 发布/更新：10-01 · 读取：2026-10-02T02:09:27.941874+00:00
  - 原文：\[赞R\]香港-东京来回 12月3日-12月8日（红叶）退税后约1781元
  - 社区晒价：1781元；航司：大湾区航空。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：未选定。

实际精确请求日期（含失败）：2026-11-14, 2026-11-30；范围响应返回日期：2026-11-14。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-14 | SerpAPI / Google Travel Explore | range | ok | 846.0 / adult_fare_tax_unknown |
| 2026-11-30 | SerpAPI | coarse | ok | 846.0 / total_including_taxes |
| 2026-11-14 | SerpAPI | coarse | ok | 846.0 / total_including_taxes |

- **CNY 846**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-30 / 单程 · 查询 2026-10-02T02:15:47.514134+00:00
  - Jetstar GK 28：HKG 2026-11-30 01:10 → NRT 2026-11-30 06:20
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

从 1 条已读取的社区内容中发现这条方向，因此纳入调查；优先级考虑证据数量和相关性，未仅按票面价格排序。

- [大湾区航空｜77折，香港往返日本国庆最低1.4k](https://www.xiaohongshu.com/explore/6abc7c77000000001c00eb8e) · 小红书 / socai · 发布/更新：10-01 · 读取：2026-10-02T02:09:27.941874+00:00
  - 原文：\[赞R\]香港-札幌来回 11月12日-11月18日（可能有雪）退税后1742元
  - 社区晒价：1742元；航司：大湾区航空。
  - 证据质量：有正文，未命中风险词；不等于已证实。不同正文，作者/活动来源独立性未确认。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：未选定。

实际精确请求日期（含失败）：2026-11-03, 2026-11-30；范围响应返回日期：2026-11-03。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|
| 2026-11-03 | SerpAPI / Google Travel Explore | range | ok | 1227.0 / adult_fare_tax_unknown |
| 2026-11-30 | SerpAPI | coarse | ok | 1218.0 / total_including_taxes |
| 2026-11-03 | SerpAPI | coarse | ok | 1227.0 / total_including_taxes |

- **CNY 1218**（含税总价）· [Google Flights / SerpAPI](https://www.google.com/travel/flights) · 出发 2026-11-30 / 单程 · 查询 2026-10-02T02:15:53.932372+00:00
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

- [香港出发｜大湾区航空来回机票77折优惠](https://www.xiaohongshu.com/explore/6abb38f20000000014039915) · 小红书 / socai · 发布/更新：09-30 · 读取：2026-10-02T02:09:27.942028+00:00
  - 原文：适用航点（香港出发）： 曼谷、马尼拉、泗水、舟山、重庆、乌鲁木齐、昆明、台北、马尔代夫、东京、札幌、大阪、仙台、福冈及冲绳。
  - 社区晒价：未取得可引用价格；航司：大湾区航空。
  - 证据质量：正文不同但活动线索相同；按同一促销计数，作者关系未知。同一活动线索。

**当前验证价格**

日期窗：2026-11-01～2026-11-30；最终选定：未选定。

实际精确请求日期（含失败）：无；范围响应返回日期：无。

失败日期：无。未覆盖日期保持未知，不声称全月最低。

| 日期 | 来源 | 阶段 | 状态 | 探索/验证价及口径 |
|---|---|---|---|---|

未验证，不能作为当前低价推荐。

**交叉验证与结论**

- 当前价格尚未验证；这只是社区线索，不能据此判断现在仍便宜。

目前只值得保留为待查线索；缺少当前价格证据，暂不推荐。

**主要限制**

- 仅核查列出的具体日期；不是整个日期窗口的最低价保证。
- 帖文、作者或活动来源的独立性未确认；不同正文不自动等于独立佐证。
- 社区可能只提到城市；机场是本次验证样本，不能把城市线索误当成机场已确认。
- 没有本轮可比的可靠典型价格，不声称历史低点或折扣幅度。
- 从深圳跨境前往机场还需交通与时间成本，可能涉及住宿；此处未计入机票报价。
- 发布时间为页面原文；相对时间以抓取时间为参照

Deal基础判断：**当前未验证**。只有社区线索，不能判断当前Deal。

## 研究循环与来源状态

- 根据证据 `0af7b0122901b3c6` 中的“大湾区航空”扩展搜索：**大湾区航空 香港 札幌 11月**。理由：社区正文把 11 月札幌列为好价样本，但未说明该促销在 11 月的可用日期与是否仍有效；用航司名加目的地与月份检索，可确认 11 月可订日期与失效情况。

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
| evidence | 小红书 / socai | ok | 大湾区航空｜77折，香港往返日本国庆最低1.4k |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| evidence | 小红书 / socai | ok | 大湾区日本航点77折！冲绳东京大阪等都有！ |
| quality | FareScout | info | 已读取正文；暂无命中风险词，仍需验价 |
| evidence | 小红书 / socai | ok | 香港出发｜大湾区航空来回机票77折优惠 |
| quality | FareScout | info | 正文不同但活动线索相同；按同一促销计数，作者关系未知 |
| community_search | 小红书 / socai | ok | 查询 香港 日本 机票；已阅读 3 篇正文/评论 |
| community_search | 小红书 / socai | info | 只读搜索：香港飞日本 十一月 机票 便宜 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 十一月 机票 便宜 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_preview | 小红书 / socai | failed | 命令超时 |
| source_retry | 小红书 / socai | failed | 逐篇读取未成功；仅回退一次socai完整扫描；有界重试：香港 日本 十一月 机票 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 十一月 机票 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_scan | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| community_search | 小红书 / socai | failed | NO\_READABLE\_POSTS: 逐篇读取和完整扫描均未取得正文 |
| community_search | Reddit public | info | 只读搜索：香港飞日本 十一月 机票 便宜 |
| community_search | Reddit public | failed | ConnectTimeout: 来源调用失败；未保存可能含凭证的原始异常 |
| community_search | FareScout | info | 所有本轮社区来源失败；保留并尝试使用已有社区证据 |
| plan | FareScout | info | 宽查询来源失败，补一次更短的同范围社区查询 |
| community_search | 小红书 / socai | info | 只读搜索：香港 日本 机票 捡漏 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 机票 捡漏 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_preview | 小红书 / socai | failed | 命令超时 |
| source_retry | 小红书 / socai | failed | 逐篇读取未成功；仅回退一次socai完整扫描；有界重试：香港 日本 机票 捡漏 |
| source_query | 小红书 / socai | info | 实际社区关键词：香港 日本 机票 捡漏 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_scan | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| community_search | 小红书 / socai | failed | NO\_READABLE\_POSTS: 逐篇读取和完整扫描均未取得正文 |
| community_search | Reddit public | skipped | 本轮此备用来源已不可达，避免重复消耗等待预算 |
| community_search | FareScout | info | 所有本轮社区来源失败；保留并尝试使用已有社区证据 |
| model | model | ok | 模型操作：discover |
| extract | FareScout | ok | 从 3 篇已读内容筛选 5 个有引用的候选 |
| expansion_plan | FareScout | info | 社区正文把 11 月札幌列为好价样本，但未说明该促销在 11 月的可用日期与是否仍有效；用航司名加目的地与月份检索，可确认 11 月可订日期与失效情况。 |
| query_expansion | 小红书 / socai | info | 只读搜索：大湾区航空 香港 札幌 11月 |
| source_query | 小红书 / socai | info | 实际社区关键词：大湾区 航空 香港 札幌 11月 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_preview | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| source_retry | 小红书 / socai | failed | 前次未取得可读正文；有界重试：大湾区 航空 香港 札幌 |
| source_query | 小红书 / socai | info | 实际社区关键词：大湾区 航空 香港 札幌 |
| browser_connection | 小红书 / socai | ok | 复用已经连接的Chrome |
| social_scan | 小红书 / socai | ok | 命令已返回；是否读到正文另行核对 |
| query_expansion | 小红书 / socai | failed | NO\_READABLE\_POSTS: 逐篇读取和完整扫描均未取得正文 |
| query_expansion | Reddit public | skipped | 本轮此备用来源已不可达，避免重复消耗等待预算 |
| query_expansion | FareScout | info | 所有本轮社区来源失败；保留并尝试使用已有社区证据 |
| candidate | FareScout | ok | 两篇社区正文都提到香港出发冲绳的往返低价线索，且促销适用出行日期覆盖 2026 年 10 月至 2027 年 1 月 21 日，与 11 月窗口有交集；但社区晒价均为往返口径且为过去日期样本，需按单程重新查询确认。 |
| candidate | FareScout | ok | 福冈在两篇社区正文中都被列为低价航点，促销出行日期覆盖 11 月；社区价格为往返含税退税后口径，需按单程与具体 11 月日期重新核价。 |
| candidate | FareScout | ok | 东京在两篇正文中均被列为促销航点，适用出行日期覆盖 11 月；社区样本日期为 12 月，且未指明成田或羽田，成田仅作为城市级待验证样本。 |
| candidate | FareScout | ok | 札幌是唯一在社区正文中出现 11 月具体日期样本的日本航点，与目标窗口直接重合；但该样本为往返口径且为已过去的日期，需按单程重新查询。 |
| candidate | FareScout | ok | 大阪出现在促销航点清单与低价航点描述中，出行日期窗口覆盖 11 月；社区未指明关西机场，关西仅作为城市级待验证样本，价格需重新查询。 |
| date_exploration | SerpAPI | info | 范围粗筛 HKG-OKA；不假定逐日覆盖 |
| date_exploration | SerpAPI | ok | 范围结果实际含 1 个日期 |
| date_plan | FareScout | info | HKG-OKA 代表日：2026-11-04, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-OKA 2026-11-04 |
| date_exploration | SerpAPI | info | coarse：HKG-OKA 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-OKA 2026-11-04：3 条匹配报价 |
| date_exploration | SerpAPI | ok | HKG-OKA 2026-11-30：3 条匹配报价 |
| date_exploration | SerpAPI | info | 范围粗筛 HKG-FUK；不假定逐日覆盖 |
| date_exploration | SerpAPI | ok | 范围结果实际含 1 个日期 |
| date_plan | FareScout | info | HKG-FUK 代表日：2026-11-04, 2026-11-30；预留少量邻近精查 |
| date_exploration | SerpAPI | info | coarse：HKG-FUK 2026-11-04 |
| date_exploration | SerpAPI | info | coarse：HKG-FUK 2026-11-30 |
| date_exploration | SerpAPI | ok | HKG-FUK 2026-11-04：3 条匹配报价 |
| date_exploration | SerpAPI | ok | HKG-FUK 2026-11-30：3 条匹配报价 |
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
| date_phase | FareScout | info | 日期探索与验价阶段实际用时（包含并发请求） |
| stop | FareScout | info | 达到研究时间预算，保留已取得的证据和报价 |
| conflict | FareScout | info | 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conflict | FareScout | info | 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conflict | FareScout | info | 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conflict | FareScout | info | 社区与实时票价两类来源已连接；只有一个实时渠道成功，缺少第二渠道验价。；社区晒价与本次航班的日期、行李、税费或单程/往返条件未全部对齐；未认定复现社区低价。 |
| deal | FareScout | info | 处于 Google 典型区间 |
| conflict | FareScout | info | 当前价格尚未验证；这只是社区线索，不能据此判断现在仍便宜。 |
| deal | FareScout | info | 当前未验证 |
| conclusion | FareScout | ok | 达到研究时间预算，保留已取得的证据和报价 |

停止原因：达到研究时间预算，保留已取得的证据和报价

研究仅进行读取与搜索，没有下单、锁座、乘机人填写或支付。
