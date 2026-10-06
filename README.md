# 飞探 FareScout P1.5

P1.5 已加入社区读取恢复、阶段耗时、日期调用优化和促销去重。之后补上同一轮续跑、提前展示报价和按研究缺口决定下一步，见[研究恢复验收](docs/current/research-recovery-acceptance.md)。

浏览器专项已完成固定本地 managed profile 的连续调用、FareScout 重启、专用 Chrome 重启和睡眠后的实际读取，共 8 / 8 次取得正文。用户已确认前三组没有重复调试授权或小红书登录；睡眠后的弹窗观察仍待确认。标准启动默认使用 managed，断线时会保留研究并自动尝试连接一次。日常 Chrome 改为显式的开发 / 备用选择，详见[浏览器会话稳定性](docs/current/browser-session-stability.md)。此前 daily Chrome 授权恢复得到 3 篇正文和 5 条有报价的航线，仍为 `partial`；[旧 CDP 验收](docs/current/cdp-stability-acceptance.md)保留历史条件与失败记录。

从模糊机票需求出发，读取社区正文/评论，依据已读线索扩展查询，再调用实时机票来源验证。输出 Markdown 报告和可恢复的 JSON 会话。产品唯一基准是 [完整需求](docs/current/product-requirements.md)。

**独立 CLI 已完成一次真实研究闭环。** socai 在已连接的 Chrome 中读取小红书正文与评论，模型根据已读帖子提出新的搜索词，FlyAI 与 SerpAPI 核对当前票价。首轮读取 12 篇社区内容，找到 5 条有依据、可继续查价的路线，用时约 3 分 18 秒；“日本呢 → 11 月呢 → 不要红眼”也在同一会话完成。查看 [P1 当前验收记录](docs/current/acceptance.md)、[P0 历史验收记录](docs/history/p0-acceptance.md) 和 [最新首轮报告](reports/05-standalone-discovery.md)。一次成功运行尚不能证明长期稳定性或机会质量始终优于人工研究。

系统如何开展研究、Agent 会做什么、为什么选用这些组件，见[完整处理过程与产品价值](docs/current/system-overview.md)。

P1 在原有研究流程中加入明确记录的约束、实时研究轨迹和历史回放，并按预算先粗查、再精查日期。核心真实验收通过后启用证据质量标签、可编辑约束及 Google 典型价基础判断。实现方式与暂缓事项见 [P1 实现说明](docs/current/implementation.md)，本阶段实测与逐项结果见 [P1 验收](docs/current/acceptance.md)。原 POC 报告保留为历史记录，不能当作现在价格。全部文档按当前版本、历史记录和参考资料分类，见[文档导航](docs/README.md)。

## 本机立即查看结果

在此项目目录运行：

```sh
./scripts/run-this-machine.sh serve --port 8765
# 浏览器打开 http://127.0.0.1:8765
# 或查看原 POC：
./scripts/run-this-machine.sh report --session standalone-20260930
./scripts/run-this-machine.sh doctor
```

`serve` 启动三栏研究工作台：左侧提问和选择历史记录，中央先展示航线、日期和报价，右侧查看实时研究轨迹。每张航线卡片都可追溯社区原文、日期探索和验价记录。条件和技术统计默认收起；修改条件会在同一会话创建下一轮研究。界面说明及验证见[前端研究工作台](docs/current/frontend-workspace.md)。服务仅监听本机，单个研究任务串行执行以保护 socai 浏览器连接。断线时已完成内容会保留。默认的专用 Chrome 会自动尝试连接一次，成功后续跑原轮次；页面要求登录或验证时，需要在专用窗口处理。日常 Chrome 备用模式需要点击“重新连接并继续”，可能再次出现授权确认。默认最多等待 10 分钟，超时后仍可手动恢复。如果只是来源失败而没有确认断线，可用“恢复这轮研究”继续。不要同时从 CLI 和网页运行研究。`report` 显示原 POC 最后一轮。首轮及追问报告保存在 `reports/`。本机脚本优先使用 `.venv`、已恢复的 `/private/tmp/farescout-p1-venv`，然后尝试旧运行环境；临时目录清理后按下面步骤重新安装。`.env` 凭证仅保留在本机。

代码包不包含本机 `.env` 或运行目录。安装后如需回放本次两轮真实验收，可先导入保存的历史 Session（不会调用来源，也不会更新报价时间）：

```sh
mkdir -p data
cp reports/p1-context-session.json data/web-1790819986976.json
farescout serve --port 8765
```

## 通用安装与启动

需要 Python 3.11+、Node.js 20+、网络，以及可调用的兼容模型 API。

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
npm install -g @fly-ai/flyai-cli@1.0.16
cp .env.example .env
```

已有 `.env` 时跳过最后一行，避免覆盖凭证。默认 managed 需要带独立配置补丁的 socai 0.6.1。本仓库不包含预编译二进制；需要 Rust / Cargo、curl、patch，然后在新的构建目录执行：

```sh
./scripts/build-socai-diagnostic.sh "$HOME/Library/Application Support/FareScout/socai-build"
# 将输出的 source/target/debug/socai 的绝对路径填入 .env 的 SOCAI_BIN
```

脚本核对官方源码归档校验值，应用首次传输日志与独立配置两个小补丁，使用锁定依赖构建并运行传输测试。它不替换或停止现有 daemon。构建目录已有 source 时需要另选目录；不要删除浏览器 profile。普通[官方 0.6.1 CLI](https://github.com/socai-io/socai/releases/tag/v0.6.1)可用于明确选择的 `existing` 备用模式，但不支持这里的独立配置路径。可执行文件不在 PATH 时填写绝对路径；升级后重新验证配置隔离和实际正文读取。

```sh
farescout doctor
farescout serve --port 8765
farescout spike
farescout run '帮我研究深圳香港最近有什么便宜国际机票。' --session demo
farescout run '日本呢？' --session demo
farescout run '11 月呢？' --session demo
farescout run '不要红眼' --session demo
# 或连续对话：
farescout chat --session demo
# 超时后续跑同一轮：
farescout resume --session demo
```

所有命令在项目目录执行，以读取该目录的 `.env`。真实研究会消耗模型/来源配额。退出码：0=本轮满足最小闭环与至少 3 条当前报价，2=部分完成/来源受阻，130=用户中断；请结合报告，而非只看退出码判断产品是否达标。

## 环境变量

| 变量 | 用途 |
|---|---|
| `FARESCOUT_MODEL` | 模型名称，默认示例 `deepseek-chat` |
| `FARESCOUT_MODEL_BASE_URL` | 兼容模型服务的 API 根地址 |
| `FARESCOUT_MODEL_API_KEY` | 必填模型凭证，只在本机 `.env` 配置 |
| `SERPAPI_API_KEY` | 可选 Google Flights 第二验价渠道；未配置会明确记录失败 |
| `FLYAI_API_KEY` | 可选 FlyAI 凭证；本次基础查询使用官方体验模式 |
| `SOCAI_BIN` / `FLYAI_BIN` | 可执行文件路径，不能填任意 shell 命令 |
| `FARESCOUT_SOCIAL_BROWSER` | 默认 `managed`，使用专用 Chrome；`existing` 为日常 Chrome 开发 / 备用模式 |
| `FARESCOUT_BROWSER_ROOT` | 可选专用浏览器数据目录；macOS 默认 `~/Library/Application Support/FareScout`，请勿放在 iCloud 或项目目录 |
| `SOCAI_HOME` / `SOCAI_CONFIG_PATH` | 可选显式指定 daemon / 配置路径；managed 会检查配置文件与预期 profile 一致，通常无需设置 |
| `FARESCOUT_DATA_DIR` | 会话、报告、研究回执目录，默认 `data` |
| `FARESCOUT_SOURCE_TIMEOUT` | 单次来源超时秒数，默认 90，5–180 |
| `FARESCOUT_MAX_SECONDS` | 每次研究/续跑时间预算，默认 480，上限 900 |
| `FARESCOUT_MAX_FARE_CALLS` | 精确验价调用预算，默认 10，上限 20 |
| `FARESCOUT_MAX_DATE_CALLS` | 范围粗筛/粗查/邻近精查合计预算，默认 25，上限 40；与最终验价预算分开 |
| `FARESCOUT_COARSE_DATES` | 每条路线代表日期数，默认 3（首/中/尾），范围低价或证据日期可替换中间日 |
| `FARESCOUT_FINE_DATES` | 每条路线低价日期附近追加样本，默认 1；仍受总日期预算限制 |
| `FARESCOUT_SOCAI_NOTES` | 每次最多读取3篇正文；先看搜索结果第一页，不为凑卡片数量滚动；卡片本身不算证据 |
| `FARESCOUT_SOCAI_MODE` | 默认 `selective`，先搜卡片再读正文；可选 `scan` 使用socai完整扫描。逐篇模式无正文时只回退扫描一次 |
| `FARESCOUT_SOCAI_COMMENTS` | 每篇最多读取评论数，默认1；范围0–3 |
| `FARESCOUT_SOCAI_CONNECT_TIMEOUT` | 首次Chrome连接等待，默认180秒；已连接时卡片搜索最多60秒、单篇读取最多40秒，仍受来源及总时间预算限制 |
| `FARESCOUT_RECOVERY_WAIT_SECONDS` | 工作台断线后的恢复等待时间，默认 600 秒，范围 15～1800 秒；managed 每轮自动连接最多一次，existing 只检查状态 |
| `FARESCOUT_FARE_CONCURRENCY` | SerpAPI精确日期查询并发数，默认2；FlyAI CLI及社区浏览器仍串行 |
| `FARESCOUT_QUOTE_REUSE_SECONDS` | 同一轮、同来源、同条件报价最多复用120秒；不会更改原抓取时间 |
| `FARESCOUT_DATE_HINT_SOURCE` | 默认 `explore`，优先Google Travel Explore，失败或无有效日期时回退FlyAI range；可选 `flyai` |
| `FARESCOUT_EVIDENCE_QUALITY` | 默认 1，正文质量/商业信号/同文关联标签；0 禁用 |
| `FARESCOUT_DEAL_STRENGTH` | 默认 1，使用当次 Google Price Insights；缺少可比基线就明确未知，0 禁用 |
| `FARESCOUT_WEB_FALLBACK` | 默认 1；允许 Reddit 公共正文备用来源，需网络 |
| `NODE_EXTRA_CA_CERTS` | 可选受信任公共 CA PEM 路径，用于企业代理等环境；不要关闭 TLS 校验 |

模型负责整理研究条件、提出候选路线和扩展查询；程序不会把模型生成的价格当作当前票价。“最近”默认明日起未来 60 天；“日期无所谓”探索未来 180 天；“11 月”解释为下一次 11 月并显示年份。验价默认 1 成人经济舱单程。日期范围较宽时，系统优先用 Google Travel Explore 找日期线索，失败或没有合适日期时尝试 FlyAI range，再抽查少数具体日期，并补查较低报价日期附近的日期，最后向两个来源核对选定日期；本轮刚取得的同条件报价可以复用。没有遍历全部日期，不声称全月最低。

## 浏览器与登录态

### 默认：专用 managed Chrome

`FARESCOUT_SOCIAL_BROWSER=managed` 时，FareScout 把 daemon 配置放在本地 `socai-managed`，把小红书登录保存在相邻的 `chrome-managed` profile。两者与日常 Chrome 分开，不同步到 iCloud。先配置带上述补丁的 `SOCAI_BIN`，再运行 `./scripts/run-this-machine.sh doctor`。诊断只检查状态，不会启动 Chrome；第一次研究或来源探测才按需启动专用窗口。

第一次使用时，在这个窗口手动登录小红书。侧边栏浏览器或日常 Chrome 的登录不会自动复制到这里。可用下面的来源探测确认能读正文；不需要模型或票价 Key：

```sh
PYTHONPATH=src .venv/bin/python scripts/browser-stability-probe.py \
  --scenario managed-first-login --calls 1 \
  --output data/managed-first-login.json
```

未登录时可能只有卡片或空结果，不能算来源可用；登录后重新执行。现有 profile 不会被重建或清理，后续连接和浏览器重启继续使用同一目录。原版 socai 若忽略独立配置路径，会明确停止，不会自动连接日常 Chrome。

### 开发 / 备用：existing Chrome

显式设置 `FARESCOUT_SOCIAL_BROWSER=existing`，清除 shell 中的独立 `SOCAI_HOME` / `SOCAI_CONFIG_PATH`，按 [socai 官方指南](https://socai.io/connect)连接日常 Chrome 并手动登录小红书。这个模式可能在 CDP 断线后再次要求调试授权，因此不作为无人值守默认路径，也不会在 managed 失败后自动切换过去。

两种模式都以实际正文读取判断来源是否可用，`browser_connected=true` 不能证明登录有效。适配器只调用只读状态、搜索和正文读取；遇登录、验证码或访问限制时保留进度，提示处理。FareScout 不读取 Cookie 数据库、不导出 profile、不迁移登录态。历史连接复用调查见[排查记录](docs/current/socai-connection-diagnosis.md)，本轮重启、睡眠与恢复时长见[专项验收](docs/current/browser-session-stability.md)。

### 已登录宿主浏览器：早期验证路径

```sh
./scripts/run-this-machine.sh run '深圳香港便宜国际机票' \
  --session new-demo --browser-bridge data/browser-bridge
./scripts/run-this-machine.sh resume --session new-demo \
  --browser-bridge data/browser-bridge
```

此模式需要**宿主 Agent（智能体）同时处理浏览器请求**；单独运行命令会等待回执，不会自行控制侧边栏。宿主通过成熟 Browser Harness 搜索、打开帖子、读取真实正文评论，写入匹配的响应。协议及边界见 [浏览器桥接说明](docs/reference/browser-bridge.md)。早期由当前会话中的 Codex 完成这层只读适配，未建立独立后台桥接服务。最新完整验证已走 socai 独立路径，不依赖桥接回执。没有将人工预设航线当作模型发现结果。

每个浏览器请求最多等待 300 秒，整轮仍受总预算限制。续跑时可以接收迟到的回执，但回执必须对应本轮实际发出的查询，保留原读取时间和历史失败。用户连续追问时，系统会继续使用已读的社区证据，重新筛选路线并核对票价；目前不会在每次追问时都重新读取所有社区帖子。

## 数据、测试与限制

- `src/farescout/`：Pydantic AI 推理、来源适配、证据校验、预算、会话与确定性报告。
- `tests/`：隔离测试；模拟数据只用于验证代码，不能计为真实验收。
- `reports/`：本次真实来源结果、逐轮报告、完整研究记录（JSON）。
- `docs/`：计划、原始需求、技术 spike、验收、桥接协议。

```sh
python -m pytest -q
```

本次 FlyAI 返回 `ticketPrice`，但没有说明统一可靠的含税口径，报告明确标成“票价，税费口径未确认”。SerpAPI Google Flights 提供含税总价；两个口径并列展示，不合成价差或节省金额。社区里常见的晒价包含往返、退税后或带行李等不同条件，不能与单程样本直接比较。FlyAI 体验模式结果受限且部分日期返回错误；相应候选继续使用 SerpAPI 验价。最新 11 月追问有 4 条成功航线。

机场词表覆盖的机场还不多，系统也不能识别图片和视频、查询自建历史价格、统一计算行李费用或估算跨境交通成本。基础 Deal 判断只会把 Google 同一次查询、相同条件下的典型价格拿来比较；如果查询缺少典型价，或者当前最低价与实际选定航班条件不同，就不会计算相对典型价的高低。排除红眼航班后也可能无法确认比较条件一致，此时结果会标为未知。商业关键词和重复文案只作为供人复核的提示，不能据此判断账号可信或帖子造假。红眼规则会排除每段当地时间 22:00–06:00 起飞或跨夜的航班，因此可能误排部分长途航班。Google 往返查询还需要确认返程航班的 `departure_token`，目前尚未支持，往返主要使用 FlyAI。FareScout 只做研究，不会预订、锁座、填写乘机人信息或支付。
