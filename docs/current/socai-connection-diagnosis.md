# 为什么 Chrome 会重复要求确认

本次排查日期：2026-10-02。使用本机 socai 0.6.1，继续连接用户日常使用的 Chrome，没有切换 profile，没有关闭 Chrome，也没有调用 `socai stop`。

## 实际查到什么

FareScout 每次启动的是一个新的 socai CLI 客户端，客户端通过本地 socket 请求同一个 daemon。新 CLI 进程不等于新浏览器会话。代码只会在超时或取消时结束当前客户端 PID，没有结束进程组、daemon PID 或 Chrome PID。

连续三次 `xhs search` 的结果如下；每次只请求一篇正文，不属于完整产品验收。

| 调用 | 耗时 | 正文 | 调用后连接 |
|---|---:|---:|---|
| 香港 日本 机票 | 35.921秒 | 1篇 | connected |
| 香港 大阪 机票 | 24.546秒 | 1篇 | connected |
| 香港 东京 机票 | 29.197秒 | 0篇 | connected |

三次调用的 daemon PID 均为7976，Chrome PID均为20626，endpoint端口均为9222、指纹均为`ca9fa658a8d7ea43`。第二、第三次调用前后 `browser_connected=true`。随后检查 CDP TCP 连接仍为同一个客户端端口61086、文件描述符12。

另一次实验把已连接浏览器上的 CLI 调用在0.5秒后取消。取消前后 daemon、Chrome、endpoint指纹和完整 CDP TCP 连接均不变，`browser_connected`仍为true。这证明结束 CLI 客户端不会自动拆掉已经建立的连接。

随后用 FareScout 的逐篇读取模式连续调用两次，两次均搜索超时，各约60秒；但上述PID、endpoint和TCP连接仍保持不变。再用完整扫描模式连续调用两次，分别101.419秒和98.732秒，都取得正文，PID、endpoint和TCP连接仍未改变。网页耗时和逐篇读取超时仍需排查，不能将它们解释为重复授权，也不能据此宣布P1.5速度与稳定性通过。

## 后续读取修复

排查连接后继续核对socai的真实卡片返回：0.6.1的精简结果没有单独的 `xsec_token` 字段，但帖子链接里仍有正文读取所需的访问参数。适配器现从匹配帖子编号的小红书链接中提取，只在内存使用。连接后的搜索卡片等待由30秒调整为最多60秒；逐篇失败时只回退完整扫描一次。

修复后单篇适配器实测37.068秒取得正文，连接仍保持。随后完整研究已跑通；重复冷启动的最终结果单独见[P1.5验收](p15-acceptance.md)。此前失败探测保留，不能把旧失败解释成Chrome再次授权。

## 为什么仍有重复确认的风险

socai 的源码区分已经连接和正在连接两种状态。客户端断开会取消当前请求；如果当时仍在连接，它会中断连接尝试，下一次调用就需要重新建立连接。如果已经连接，取消请求会保留连接。

FareScout 原来对搜索卡片只给30秒。首次调用把连接、等待用户批准和搜索放在同一个超时里，可能在用户批准完成之前取消请求；随后重试又开始连接。这是一条明确存在的风险路径，但本次没有故意取消尚未批准的连接以制造新的授权提示，也不能据此断言此前每次提示都是它造成的。首轮完整调用35.921秒包含网页读取，不等于单独等待权限用了35.921秒。

Chrome退出后旧的 `DevToolsActivePort` 文件也可能还在。排查初期发现Chrome没有运行，而旧endpoint指纹仍存在；重新打开Chrome后指纹改变。文件存在不能证明endpoint有效。

受限执行环境曾让 `socai status` 返回 `DAEMON_UNAVAILABLE`，正常本机权限下同一个daemon仍在运行。此前仅凭这条状态推断daemon已经退出不够准确；应同时检查本机进程及IPC权限。本次增加了权限错误分类，避免在无权访问现有daemon时尝试另起服务。

## 已修改什么

- 调用搜索前读取状态。已经连接时直接复用；尚未连接时给首次授权独立的180秒等待预算，可通过 `FARESCOUT_SOCAI_CONNECT_TIMEOUT` 修改。
- 首次连接等待超时后停止该来源，本轮不自动重试连接，避免再次弹出权限请求。研究总时间预算仍然有效，用户取消也会停止请求。
- 超时后再次核对状态。如果Chrome已经连接，归类为网页搜索超时，不归类为授权超时。
- 发现本地socket被执行环境拒绝访问时，返回 `DAEMON_IPC_PERMISSION_DENIED`，提示从正常本机终端运行，不重建daemon。
- 只结束自己启动的CLI PID，并处理客户端恰好已退出的竞态；不调用 `stop`、不重启浏览器、不设置每轮新的 `SOCAI_HOME` 或CDP endpoint。

## 怎样复测

在正常本机终端运行，先确认Chrome已打开并登录小红书：

```sh
PYTHONPATH=src python scripts/probe-socai-reuse.py --calls 3
PYTHONPATH=src python scripts/probe-socai-reuse.py --mode adapter --calls 2 --output adapter.json
```

按README配置 `SOCAI_BIN` 和 Python 环境。脚本保留状态、PID、endpoint指纹及CDP TCP连接，原始帖子访问token只留在忽略提交的私有目录。首次若需要授权，用户批准一次；后续查看状态和TCP连接是否持续复用。

同一Chrome/CDP会话内可以复用授权。退出Chrome、停止daemon、切换profile或使用不兼容的socai版本后，可能需要新的首次授权；不能承诺跨这些会话永久免确认。

81项自动化测试通过，覆盖首次连接等待、连接后的短超时、IPC权限拒绝和连接成功后网页超时的区别。日志证明实际连接持续复用；未直接记录Chrome授权弹窗的视觉次数，不将它写成已测量的计数。

源码依据：[daemon请求与取消处理](https://github.com/socai-io/socai/blob/v0.6.1/cli/src/daemon.rs)、[运行时连接复用](https://github.com/socai-io/socai/blob/v0.6.1/core/src/runtime/engine.rs)、[endpoint发现](https://github.com/socai-io/socai/blob/v0.6.1/core/src/cdp/endpoint.rs)。官方说明也将确认范围定义为每次会话一次：[Chrome连接说明](https://socai.io/connect)。审计文件见 `reports/p15/socai-connection/`。


## 后续发现的新会话断开

完成连接复用探测及多轮社区读取后，2026-10-02 10:41:37（北京时间）daemon记录 `CDP session is closed`。最终版本新研究在11:34:36才开始，三轮均发生新的WebSocket握手失败（socai内部每次等待20秒、重试3次）。daemon和Chrome进程编号、endpoint文件指纹未变，Chrome仍监听9222，但原TCP连接已经断开。不能将端口存在当作已经连接，也不能将这次断开归因于后来的FareScout请求超时。

目前未确认是谁或什么动作关闭了CDP会话，已请用户核对新的Chrome连接请求。客户端180秒等待不延长socai内部约60秒的连接预算；同一轮连接失败后FareScout停止该来源，但不同的新研究仍各自允许一次首次连接尝试。此后最终验收0/3，详见[P1.5完整记录](p15-acceptance.md)。此前连接持续复用的结论只适用于观测期间，不是永久免确认保证。


## 2026-10-04 的进一步验证

本次确认了同一 daemon / endpoint 下仍会丢失 CDP 连接。断开时间与 macOS 空闲睡眠记录相差不足一秒，暂不能把它写成已确认的唯一原因。应用现在记录连接变化，并能恢复同一轮；真实报价恢复保留了原文时间与已完成日期探索。连续和空闲后的完整验收仍未通过，详情见[研究恢复验收](research-recovery-acceptance.md)。

今日对三小时超时、daemon退出、客户端清理及睡眠的逐项判断，见[完整断线排查与解决方案](cdp-disconnect-investigation.md)。
