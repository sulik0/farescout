# FareScout P0 开发计划与后续记录

本文记录 P0 起步时的实施计划及后来验证后的调整；其中“当时遇到的主要风险”反映的是起步阶段，不代表当前环境。唯一产品基准是 `../current/product-requirements.md`，即原始需求的逐字副本。先交付本机命令行工具（CLI）和可审计的 Markdown/JSON 研究报告，避免先搭建前端、数据库或通用 Agent 平台。

## 复用的组件和选择原因

- **Pydantic AI**：复用模型调用、结构化输出、验证和重试。FareScout 只约束研究阶段、证据引用与预算。模型地址/名称可配置。
- **socai CLI**：优先复用小红书搜索、正文和评论读取、Chrome 会话连接。已发布的 0.6.1 只开放 `xhs search` 研究命令（该版本没有 `task begin`），不暴露写操作或任意 shell。
- **FlyAI CLI**：先验证官方 `@fly-ai/flyai-cli` 的结构化只读航班查询；官方说明基础调用可不配置 Key，适合当前环境。
- **SerpAPI Google Flights**：配置 Key 后作为第二验价渠道。只对少量候选和具体日期请求；禁用缓存，价格必须来自响应字段。
- **浏览器备用路径**：优先使用 socai 已有能力；无法读取时，记录实际访问的研究站点和需要人工确认的原因。OpenCLI/Browser Harness 作为可选备用研究适配器，不自研浏览器引擎。

## 参考评估

- [socai](https://github.com/socai-io/socai)：`xhs search` 默认继续打开正文/评论，最贴合 P0。
- [OpenCLI](https://github.com/jackwener/opencli)：适合 Chrome 扩展连接与站点命令；避免同时强制配置两套浏览器基础设施。
- [Prism travel-agent](https://github.com/Prism-Shadow/travel-agent)：借鉴可见操作、观察后验证与标签页边界，不整体 fork，其预订路径超出范围。
- [DeepSeek Harness](https://www.deepseek.com/harness/en/)：可复用但当前需要的只是范围明确的研究流程和按格式整理的推理任务，Pydantic AI 更轻便。
- [Pydantic AI](https://ai.pydantic.dev/)：Pydantic AI 可以按指定格式返回结果，便于检查候选、扩展依据和上下文更新。
- [FlyAI](https://github.com/alibaba-flyai/flyai-skill)：直接验证官方 CLI，不把泛化旅行产品或广告起价当作精确航班价。
- [SerpAPI](https://serpapi.com/google-flights-api)：日期/币种/行程类型明确，适合作为可核查的验价来源，需要 API Key。
- [huahuanao travel-agent](https://github.com/huahuanao/travel-agent)：参考不同来源分别提供信息的做法，不把相同转载误算成独立证据。

## FareScout 自己负责哪些工作

FareScout 自己负责保存研究目标及多轮修改，筛选可用的社区证据，提取帖子内容，并至少根据一次已读证据扩展查询。它还会筛选少量候选路线、按相同条件比较票价、解释价格冲突，在某个来源失败时尝试其他来源，并在达到预算后停止。研究会话和验收报告也由 FareScout 保存。价格数据与模型输出分离，模型不能创建“当前价格”。

## 怎样跑通 P0

模糊输入直接进入 Discovery → 2～3 次宽查询并阅读正文/评论 → 引用已读证据产生新查询 → 选择最多 5 条候选 → 按具体日期/单程或往返条件调用 FlyAI/SerpAPI → 汇总社区晒价、当前验价、时间戳、限制与冲突。证据不足则输出真实不足，不能凑满 3～5 个。

先做分别验证各数据来源能否独立工作，再运行整条链路。用同一会话继续“日本呢 → 11 月呢 → 不要红眼”，保留机场、目标、证据和历史，不复用不符合新条件的旧报价。

## 当时遇到的主要风险

初始环境没有配置模型/SerpAPI Key、socai 或浏览器连接。后续模型已配置，socai 已安装；Chrome 独立连接仍未完成，SerpAPI 尚未配置。已使用登录后的宿主 Browser Harness 作为社区读取路径，FlyAI 官方体验模式作为实时验价来源。站点登录/CAPTCHA 必须人工处理；真实链路受网络、配额和第三方结构影响。只有真实成功运行才把对应 DoD 标为 PASS；模拟测试只证明程序行为。

## 当时决定暂缓的工作

网站发布、账户体系、订单及支付、价格历史库、预测/监控、OCR/ASR、完整交通成本引擎、大规模抓取和复杂评分。先确保一次真实研究成立。

## 实测后作出的调整

增加薄文件桥接以复用已登录的宿主 Browser Harness，不复制登录态。浏览器等待有预算，支持迟到回执和断点续跑，保留原读取时间。候选先保存再执行查询扩展，避免扩展超时丢失发现。实测 FlyAI 的 `ticketPrice` 与文档 `adultPrice` 字段不同，兼容两者且始终标记税费口径未知。主路径以发布版 CLI 为准，不照搬主分支尚未发布的命令。

## P0 的实际结果

用户连接 Chrome 并配置 SerpAPI 后，我们修正了 socai v0.6.1 的帖子字段 `notes[].entity` 和评论字段 `top_comments` 解析。独立命令行版本随后读到 12 篇社区正文，根据其中的线索扩展了一次查询，筛出 5 条路线，并用 FlyAI 和 SerpAPI 两个渠道核对票价。宿主 Browser Harness 桥接仍可作为备用研究路径。产品质量风险转为样本日期覆盖、价格口径不一致、行李及跨境成本未归一化，以及长期重复运行稳定性。详见 `p0-acceptance.md`。
# P1 后续实施记录（2026-10-01）

P1 继续使用 Pydantic AI、socai、FlyAI、SerpAPI，以及原有的 Session（会话）和 Evidence（证据）数据结构。新字段都提供默认值，因此旧版 schema 1 数据仍能读取；系统完成每个实际操作后都会立即保存对应事件。本机界面使用 Python 标准库提供 HTTP 服务，以 SSE 推送事件，并由一页原生 HTML/JS 展示；命令行和界面共用同一研究流程与本机会话，不再引入另一套运行环境。

日期探索先用 FlyAI 查询整段日期范围，取得可核对的日期线索；再抽查日期窗开头、中间和末尾的少数日期。系统可以用范围查询或社区帖子里的日期替换其中一个样本，也会根据已查价格补查一个邻近日期，最后尝试用两个来源复验选定日期。探索日期和最终验价分别设有调用上限。范围查询只记录服务实际返回的日期，不会声称已经查过整个日期窗。查询失败或因预算不足跳过时，系统都会保存记录；没有检查的日期仍标为未知。

先真实研究“香港 11 月飞日本哪里便宜？”，并确认界面能够回放过程；之后再启用根据原文生成的证据质量标签、约束编辑和 SerpAPI Price Insights 基础判断。主要风险是社区结果页稳定性、范围查询仅返回部分日期、FlyAI 税费未知与接口配额；新来源、Multi-Agent、Runtime 迁移与复杂评分继续暂缓。
