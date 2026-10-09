# Social Research 浏览器会话稳定性专项

2026-10-06 开始，2026-10-10 更新。本专项只解决社区研究使用哪个浏览器、登录是否保留，以及断线后怎样恢复。先验证 socai managed Chrome；日常 existing Chrome 只保留为开发和备用路径，不再把“日常 Chrome 的 CDP 永不断开”作为主要目标。

## 10 月 10 日最新结果

空闲后两次真实正文读取成功，耗时 26.415 / 12.855 秒。首次连接不可用时，socai 自动启动同一 profile，约 4.198 秒后观测到连接；再空闲 30 秒后复用连接。用户确认没有调试授权弹窗，也没有重新登录。首次请求之前的空闲时长没有受控记录，不能当作三小时 idle 对照。

完整研究中故意关闭专用 Chrome，发现 WebSocket 已终止后，daemon 仍会短暂报告已连接，约 4.9 秒后才更新。原实现因此把错误当普通 CLI 失败，没有恢复。现已核对当前 daemon PID 与首次终止日志，提前识别断线，并等待 daemon 更新后再发起本轮一次自动重连。旧终止日志和新连接不会误触发恢复。

修复后四次真实受控断线均自动续跑原 Session / Turn，重连请求耗时 8.018～14.392 秒。正文和观察时间保留，已完成查询不重复。最后一次在已有一个精确日期和 3 个报价后关闭 Chrome，直接核对了精确日期、报价 ID、金额和原观察时间保留；暂停到续跑也未重复日期调用。首次修复后的重连由用户确认没有授权或登录；后续没有逐次补问，不能仅凭 CLI 状态认定没有弹窗。

最后一轮 117.982 秒，40.460 秒出现首条结果、51.955 秒出现前三条，最终 6 篇正文和 5 条有报价路线。六个新研究会话全部为 `partial`：SerpAPI 额度耗尽，补齐 Node 后 FlyAI 能返回报价，但每条路线只有一个精确日期成功、税费口径未知。用户明确同意先交付稳定性结果，完整票价验收暂留 FAIL。

逐轮 `complete / partial / blocked`、调用量、阶段耗时、失败、日期覆盖和脱敏证据统一放在 [10 月 10 日验收记录](../../reports/browser-session-stability/2026-10-10/acceptance.md)。整套回归 131 项通过；跳过的 1 项前端检查补齐 Node 后单独通过，合计 132 项检查通过。仍未验证精确三小时 idle、长睡眠、机器重启或长期登录过期。本轮没有新增睡眠操作；下面保留 10 月 6 日的首次验证记录，不覆盖当时失败和未确认条件。

后续日期研究修正已在[独立验收](date-research-acceptance.md)中记录：无断线注入的新研究取得 5 条路线各两个成功日期。它补齐日期覆盖，未解决 SerpAPI 无额度或第二个实时票价源交叉验证；上面的受控断线数据仍是历史结果。

## 怎样决定默认浏览器

managed 首次登录后，至少要通过连续正文读取、FareScout 服务重启、专用 Chrome 重启，以及 Mac 睡眠唤醒后的读取检查。每个条件都记录连接状态、用户是否重新批准调试、恢复耗时、实际正文数和失败原因。仅有 `browser_connected=true` 不算来源可用，也不能证明小红书登录态保留。

如果 managed 在这些条件下都能恢复，且不再要求手动批准远程调试，就让 FareScout 默认使用它。如果失败，先区分小红书页面限制、登录未保留、CDP 断线和浏览器进程退出；再验证 FareScout 单独维护 Chrome 进程、socai 只连接该进程的方案。不同时新建多个方案让用户重复登录。

## 10 月 6 日配置与已确认的行为

新 managed profile 放在 `~/Library/Application Support/FareScout/chrome-managed`，daemon 与配置放在相邻的 `socai-managed` 目录。它们不经过 iCloud 同步，与日常 Chrome、10 月 4 日的实验 profile 分开。没有复制 Cookie 或读取 Cookie 数据库；用户在新窗口首次登录。

首次连接已建立，CLI 的浏览器状态为已连接。但首次搜索未取得卡片，原 CLI 登录诊断未明确报告未登录；实际页面显示“登录后查看搜索结果”。这次调用不能计入登录后的成功率，摘要见 [`managed-before-login.json`](../../reports/browser-session-stability/managed-before-login.json)。独立验证工作台运行在 `http://127.0.0.1:8769/`。登录后的实测结果如下，首次登录前的失败单独保留。

目前使用已构建的 socai 0.6.1 诊断版，保留首次 WebSocket 终止日志和独立配置补丁。也核对了[官方 0.6.3 发布](https://github.com/socai-io/socai/releases/tag/v0.6.3)以及对应源码：`ChromeProcess::drop` 仍会结束它拥有的 Chrome；连接丢失后会释放这个进程守卫。已运行且能连接的 managed Chrome 则由 socai 以 `BrowserOwner::None` 复用。这意味着独立维护浏览器进程可以沿用 socai 的读取能力，不需要另做 Browser Harness。源码核对摘要见 [`source-review.json`](../../reports/browser-session-stability/source-review.json)。这些源码行为解释了为什么连接结束后浏览器也可能退出，不能证明最初是谁触发了 CDP 断线。

Chrome 官方也要求对非默认数据目录使用远程调试开关，并建议把自动化与日常 profile 分开，见[远程调试开关调整](https://developer.chrome.com/blog/remote-debugging-port)。这支持专用 profile 的选型，但不是“此版本永远不会出现确认弹窗”的保证，仍要记录本机实际观察。

## 测试与记录方式

同一 profile 只首次登录一次。重启测试只作用于这个专用 Chrome 或 FareScout 实验服务，不关闭日常 Chrome，不清理 profile，也不使用会影响其他 daemon 的 `socai stop`。睡眠测试先安排用户唤醒；睡眠请求、真实系统电源事件和唤醒后的状态分别记录。

| 条件 | 实际正文读取 | 再次登录 / 调试授权 | 恢复连接 | 从请求到正文 | 记录 |
|---|---|---|---|---|---|
| 连续调用，之间空闲 30 秒 | 3 / 3 | 用户确认均未出现 | 原连接保持 | 22.199 / 56.770 / 13.838 秒 | [连续调用](../../reports/browser-session-stability/managed-continuous.json) |
| FareScout 服务重启 | 1 / 1 | 用户确认均未出现 | 原连接保持 | 9.536 秒 | [服务重启](../../reports/browser-session-stability/fare-service-restart.json)、[正文读取](../../reports/browser-session-stability/managed-service-restart-read.json) |
| 专用 Chrome 重启，后续再空闲 20 秒 | 2 / 2 | 用户确认均未出现 | 第一次约 4.049 秒；后续复用 | 22.691 / 10.179 秒 | [Chrome 重启](../../reports/browser-session-stability/managed-chrome-restart.json)、[正文读取](../../reports/browser-session-stability/managed-chrome-restart-read.json) |
| Mac 睡眠 / 唤醒，后续再空闲 30 秒 | 2 / 2 | 睡眠后的弹窗与登录观察待用户确认 | 第一次约 10.547 秒；后续复用 | 35.928 / 9.188 秒 | [睡眠前后](../../reports/browser-session-stability/managed-sleep.json)、[正文读取](../../reports/browser-session-stability/managed-sleep-read.json) |

四组实际请求共 8 次，8 次都取得正文，没有 `blocked`、`partial` 或空正文。这里的 8 条是读取次数，并非 8 篇不同帖子，也不表示内容经过机票机会判断。四组分别发出 9、3、16、23 次来源 CLI 命令，共 51 次，含搜索、读取、连接状态观察；每次前后独立取样另有 2 次 `status`，共 16 次。本专项没有调用模型或票价 API，不能算作新一轮机票研究验收。56.770 秒的一次正文读取仍偏慢；连接稳定不等于网页响应速度稳定。

全程沿用 daemon PID 95945。FareScout 实验服务从 PID 96482 重启为 97060，没有关闭 daemon 或 Chrome；这里验证的是服务生命周期前后的真实来源读取，没有另起一次完整 Agent 研究。专用 Chrome 从 PID 95958 重启为 97298，睡眠后又自动启动为 97733；profile 目录始终相同，小红书没有再次要求登录的观察已覆盖 Chrome 重启测试。

连接恢复秒数来自每约 2 秒一次的状态观察，包含调度延迟，不是精确的 WebSocket 握手时长。请求到正文的耗时则包括搜索和正文读取，不应混作连接耗时。

### 睡眠附近发生了什么

11:04:39（北京时间）发出睡眠请求，11:04:40.275 的首次 WebSocket 终止日志记录 `websocket_receive_failed / protocol`，11:04:44.780 的 daemon 日志报告会话关闭。系统电源记录随后出现 11:04:45 的 `Sleep`、11:04:46 的 `Wake`，以及后续 Sleep / Wake 事件，见[脱敏电源事件](../../reports/browser-session-stability/managed-power-events.json)。因此不能说 Mac 连续睡足一分钟，也不能说 WebSocket 一定由已经进入睡眠的系统关闭：首次传输终止早于这条 Sleep 记录。可以确认的是，睡眠请求附近原连接退出，Chrome 进程随后不在，但 daemon 未退出。

11:08:30 再次读取时，原 endpoint 标记仍在，连接不可达。socai 自动用同一 profile 重新启动 Chrome，约 10.5 秒恢复连接，约 35.9 秒取得正文；30 秒后再次读取成功。首次传输日志摘要见[连接观察](../../reports/browser-session-stability/managed-transport-observation.json)。`protocol` 是传输结束类别：受控关闭 Chrome 时也出现同类日志，所以不能只凭这个词判断软件缺陷或谁关闭了浏览器。


`scripts/browser-stability-probe.py` 调用现有 Socai 适配器，每次重新创建适配器并实际读取正文，不用上次的内存证据充数。它只记录公开帖子链接、正文长度和连接信息，不导出正文内容、授权 URL 或 Cookie。CLI 状态不能可靠报告 Chrome 弹窗，因此默认记为未知，只有用户或实际 UI 观察后才更新。

使用独立环境变量指向本次 profile 后，可执行：

```sh
export SOCAI_HOME="$HOME/Library/Application Support/FareScout/socai-managed"
export SOCAI_CONFIG_PATH="$SOCAI_HOME/config.json"
# SOCAI_BIN 指向带独立配置补丁的诊断版。首次设置时已创建上述配置；
# 原版仅设置 SOCAI_HOME 不会隔离 Chrome 配置。
PYTHONPATH=src .venv/bin/python scripts/browser-stability-probe.py \
  --scenario managed-continuous --calls 3 --interval 30 \
  --output reports/browser-session-stability/managed-continuous.json
```

脚本不自动重启浏览器、不让 Mac 睡眠。Chrome 和 FareScout 重启由本次受控测试分别执行，先核对 PID、启动参数和 profile，未使用全局 `socai stop`。测试记录保留了睡眠前后的端点变化，也保留首次未登录时的失败。

## 默认配置与恢复流程

标准 CLI / 工作台启动现在默认选择 `FARESCOUT_SOCIAL_BROWSER=managed`。这是根据上述四组真实正文读取作出的选择；睡眠后的“没有弹窗 / 没有再登录”仍等待用户补充观察，不能把它写成已确认。现有日常 Chrome 不再承担无人值守主路径。

首次启动会在本地应用数据目录创建独立的 daemon 配置和 profile。适配器先执行只读 `socai config path`，确认它指向独立配置，再检查 `profile_mode=managed` 和 daemon 版本。原版 CLI 若忽略 `SOCAI_CONFIG_PATH`，就以 `BROWSER_CONFIG_UNSUPPORTED` 停止；不会悄悄连接日常 Chrome。已有配置若指定别的 profile，也会停止并保留原文件。当前需要仓库提供的两个 socai 小补丁，安装步骤见 [README](../../README.md)。

正常研究的只读搜索会按需启动专用 Chrome。工作台若确认来源断线，会保留 Session、Turn、已读正文和已完成日期；自动尝试连接一次，再从未完成步骤继续。尝试次数先写入 checkpoint，服务重启后也不重新累加尝试。连接尝试的 CLI 数量、耗时和失败类别保存到 `browser_recovery` 与研究轨迹。只检查到浏览器已连接，不代表网页登录有效；如果重连页面报告登录或验证要求，停止自动续跑，提示用户在专用窗口处理。后续仍失败时保留结果，允许手动“重新连接并继续”，避免无限重试。

自动连接最多一次的限制按原轮次计算；一轮研究中再次断线时可能需要手动恢复。网页应用会自动等待并续跑；独立 CLI 会保存 checkpoint，但没有后台等待线程，需执行 `resume`。这些恢复行为由回归测试验证，同轮次不会重读已成功的社区步骤、改写原证据时间或重新开始整轮；上述八次真实浏览器检查没有故意制造机票研究中途断线，不能用它们声称已经完成新的完整研究恢复验收。

## 开发 / 备用路径与剩余检查

使用日常 Chrome 时显式设置 `FARESCOUT_SOCIAL_BROWSER=existing`，并移除独立测试时在 shell 导出的 `SOCAI_HOME` / `SOCAI_CONFIG_PATH`。它只观察连接，重新连接由用户主动发起；日常 Chrome 可能再次要求确认。不会在 managed 失败时自动切换 existing，让日常 Chrome 意外弹出调试授权。

本轮没有验证保持唤醒三小时、多次长时间睡眠、机器重启或小红书长期登录过期，8 / 8 不能代表长期可用率。首次登录、验证码和平台限流仍可能需要人工处理；独立 profile 不能绕过平台限制。当前数据支持先采用 managed，而不再另建一套 FareScout Chrome 进程管理。如果后续重复出现 managed 进程退出后无法自动恢复，再验证 FareScout 维护专用 Chrome、socai 复用其 endpoint 的方案。


## 10 月 6 日首次交付检查

- 连续读取、服务重启、Chrome 重启、睡眠后读取：PASS，四组 8 / 8 次取得正文。
- 普通默认配置真实读取：PASS，另一次请求 16.630 秒取得正文，沿用 daemon 95945，未依赖实验 shell 环境。见[默认配置实测](../../reports/browser-session-stability/managed-default-read.json)。全部真实检查合计 9 / 9，来源 CLI 55 次，前后取样 `status` 18 次，模型 / 票价 API 均为 0。
- 不再重复调试授权或登录：连续、服务重启、Chrome 重启由用户确认；睡眠后仍待确认，不能整体标为 PASS。
- 默认工作台配置与历史保留：PASS，8768 工作台已重新启动，实际 `/api/browser` 返回 managed、连接可用、daemon 95945；沿用原来的 `data/recovery-live`，3 条最近的研究仍可读取，`recovery-final-2` 的原 Turn 和 5 条航线保持不变；根 `data` 中另外 12 条历史会话也仍保留在原目录。启动扫描现已跳过数组格式的诊断 JSON，避免把它们当作 Session 导致服务退出。
- 自动重连与原轮次续跑：回归测试 PASS；本轮真实浏览器检查未验证完整机票研究中途断线，不能算新一次完整研究恢复验收。
- 长期无人值守：未完成三小时空闲、多次睡眠和长期登录过期检查。本轮短测只能支持先使用 managed，不能保证长期无人值守。

逐组记录和总调用量见[汇总 JSON](../../reports/browser-session-stability/summary.json)。测试只操作专用 Chrome，未结束日常 Chrome 或其他 daemon；仍保留旧失败记录，没有将状态检查、卡片或旧缓存算作正文读取成功。

最终回归结果：119 项测试通过，含 HTTP 工作台、断线保存、一次自动重连、服务重启后的尝试次数保留、登录提示时停止、并发保护和前端测试。最终工作台状态见[启动与历史核对](../../reports/browser-session-stability/final-workbench-check.json)。

公开记录已去除原始进程清单、本机用户名、个人绝对路径和 TCP 原始行；仅保留检查所需的 PID、连接指纹、时间、次数及公开帖子引用。原始诊断保留在本机忽略目录，不随代码提交。
