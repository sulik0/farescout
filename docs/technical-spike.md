# 技术验证记录（Technical Spike）

测试环境：macOS、Python 3.13、Node.js 20；测试日期 2026-09-30（Asia/Shanghai）。需求原文 SHA-256：`9c256eb67d466f8c80e629f8cbf7f05f5a48dc7c1f693d8efe8d8b6aed82d454`。模型配置只检查是否存在，不记录密钥或私有服务地址。

| 验证项 | 结果 | 实际发现 |
|---|---|---|
| 模型按指定格式返回结果 | PASS | 实际生成宽查询、约束变更、引用证据的候选和扩展查询 |
| socai CLI 安装与只读命令 | PASS | 官方 v0.6.1 已安装；校验过发布包；`xhs search` 支持正文和评论 |
| socai 独立 Chrome 连接 | FAIL | `CDP disconnected`，没有可连接的 Chrome；当前 doctor 为 browser_connected=false |
| 登录后的宿主浏览器读取 | PASS | 两次宽查询及一次扩展查询实际执行，3 篇正文进入程序证据集，其中 2 篇带评论 |
| FlyAI 实时票价 | PASS | 官方 `@fly-ai/flyai-cli@1.0.16` 体验模式取得真实航段、日期、金额；不访问 jumpUrl |
| SerpAPI Google Flights | FAIL | 没有配置 Key；不能计作成功使用的来源 |
| Reddit 备用社区 | FAIL | 本次真实尝试 ConnectTimeout；切换备用来源的情况仍记录在研究报告里 |
| 研究循环（Research Loop） | PASS（宿主协作路径） | 模型根据社区帖子里的航司和目的地提出扩展查询，再对 5 条候选实时验价 |

初始票价 spike 使用预设的 HKG→NRT / 2026-11-10，仅证明 API 可调用，不计入社区发现验收。FlyAI 实际会返回同城市其他机场：适配器按真实航段校验，不能把 HND 冒充 NRT。其实际字段为 `ticketPrice`，与示例文档的 `adultPrice` 不同，现已同时识别这两种字段。未确认含税总价，所有 FlyAI 结果持续显示税费口径未知。

本机 npm 曾遇证书链错误，因此使用官方 npm registry 包与完整性摘要验证的本地 CLI。Node 读取从系统钥匙串导出的**公共 CA 证书**，始终保持 TLS 校验开启。没有读取私钥、关闭证书校验或替换系统证书。

依赖安装路径最初位于 Documents，出现 Python import 文件读取停顿；运行环境移至 `/private/tmp/farescout-poc-venv` 后可运行。已验证 `pip install -e . --no-deps` 构建安装成功。源码与交付仍在当前项目目录。

浏览器调用存在明显延迟，首次整体研究超时；已实现 `resume`、迟到回执匹配及候选保留。重试没有修改第一次失败记录。研究的 `started_at` 到最终 `finished_at` 包含跨用户轮次等待与开发修复，不是可用的无人干预性能基准。续跑阶段约 4 分钟，仅证明已有证据条件下能接通剩余链路。

官方参考：[socai](https://github.com/socai-io/socai)、[Chrome 连接](https://socai.io/connect)、[FlyAI](https://github.com/alibaba-flyai/flyai-skill)、[SerpAPI Flights](https://serpapi.com/google-flights-api)、[Pydantic AI](https://ai.pydantic.dev/)。

## 2026-09-30 后续独立复测（当时的最新结果）

用户在本机连接 Chrome 并配置 SerpAPI 后，最初 doctor 仍显示 socai daemon 不可用；首次只读查询启动 daemon，随后 `socai status --json` 显示 `browser_connected=true`。接着发现 **适配器仍按旧字段 `note` 解析**，发布版 v0.6.1 实际返回 `notes[].entity` 和 `top_comments`。修正并加入回归测试后，单次 `Socai.search` 成功取得 5 篇正文及 6 条评论。

SerpAPI 实际以 HKG→OKA、2026-10-14 返回 3 条含税机票报价。之后重新独立运行整个模糊输入，不使用宿主回执：2 次宽查询 + 1 次根据已读证据扩展查询，12 篇正文，5 条候选全部获得当前报价，4 条由 FlyAI 与 SerpAPI 双渠道支持。完整细节与逐轮追问见 [最新验收](acceptance.md) 和 [最新首轮报告](../reports/05-standalone-discovery.md)。前表是首次 spike 的历史状态，以此处重测为准。

独立研究完成后，空闲时 `doctor` 曾再次显示 `DAEMON_UNAVAILABLE`，单独的 socai `status` 也曾显示浏览器端点不可达；随后同一只读搜索重试成功取得 5 篇正文和 4 条评论，再查 `status` 为 `browser_connected=true`。这说明本机连接可按需恢复，但状态快照不是长期稳定性证明。
