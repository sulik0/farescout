# 上午授权后，下午为什么又需要确认 Chrome

2026-10-04。针对当前本机 socai 0.6.1、Chrome 154.0.8037.97 和 `existing` 模式排查。用户确认上午已批准 Chrome 授权，下午又遇到确认请求。本次只读检查日志和进程，没有重连 Chrome、重启 daemon、修改电源设置或切换登录态。

## 判断

**可以确认原 CDP 会话断开，daemon 和 Chrome 主进程都没有退出。睡眠是目前最值得验证的触发条件；尚不能确认底层是谁关闭了 WebSocket。**

| 怀疑的原因 | 本次判断 | 依据 |
| --- | --- | --- |
| 3 小时 idle timeout | 不支持作为这次原因 | 11:34研究结束，12:48已经断开，只有约74分钟；本机socai的daemon空闲退出为24小时；远端90秒空闲释放不适用于existing模式 |
| daemon / CDP 意外断开 | CDP断开已确认；daemon未退出 | 日志记载CDP session is closed，同一daemon仍运行，但到Chrome 9222的原TCP连接已不存在 |
| FareScout清理进程杀掉daemon | 本次排除 | daemon PID7976从10月1日09:43:08启动后未重启；代码只结束自己创建的CLI客户端，不结束进程组或daemon |

没有找到“本机CDP固定3小时超时”的证据。Chrome对应版本的源码下载未成功，不能据此声称已经排除Chrome所有可能的内部策略；不过这次在约74分钟时就断开，不符合从本次研究结束起算3小时的解释。

## 时间线

以下均为北京时间，UTC日志已转换为同一时区。

| 时间 | 事实 |
| --- | --- |
| 10月1日09:43:08 | 当前socai daemon启动，PID7976 |
| 10月4日11:11:23 | 当前Chrome主进程启动，PID46958 |
| 上午 | 用户批准调试授权；只读探测随后成功取得正文，连续两轮研究都读到社区证据 |
| 11:32:50 | 记录browser_connected=true，复用已建立连接 |
| 11:34:06 | 第二轮研究结束，保留两条有报价的路线 |
| 12:48:22.816 | daemon记录CDP session is closed |
| 12:48:23 | macOS记录Idle Sleep，开始空闲睡眠 |
| 13:59:00 → 14:00:19 | 短暂唤醒，随后再次空闲睡眠 |
| 16:58:54 | macOS记录正常唤醒 |
| 17:07:10 | 新研究看到daemon仍在，但browser_connected=false；endpoint指纹仍为b5eb7c8be2ef259c |
| 17:07:30 / 17:07:51 / 17:08:11 | socai内部三次连接尝试各约20秒后失败 |
| 本次检查 | daemon和Chrome启动时间仍不变；socai状态disconnected，error_code=BROWSER_ENDPOINT_UNREACHABLE |

CDP报错与睡眠日志相差不到一秒，是很强的时间关联。日志记录时间不等于底层事件的精确发生时间，不能用这个关联证明Chrome必然因睡眠主动撤销许可，也不能区分系统挂起、Chrome关闭WebSocket或其他连接错误。

## 为什么断开后会再弹窗

Chrome把许可授予一次远程调试会话。旧会话还活着时，多个socai CLI请求通过同一个daemon复用它；旧会话丢失后，再建立WebSocket是新的调试会话，因此可能重新询问许可。Chrome官方对此有明确说明：[连接已有浏览器会话](https://developer.chrome.com/blog/chrome-devtools-mcp-debug-your-browser-session)。

所以“进程没变、9222仍监听、DevToolsActivePort文件没变”都不能保证上午那次授权对应的连接还活着。下午重连时，socai内部的20秒超时和三次重试还会让确认窗口很短，可能重新发起连接；不能仅靠FareScout外层180秒等待解决。

## socai和FareScout的实现核对

核对的是socai **v0.6.1**：[daemon](https://github.com/socai-io/socai/blob/v0.6.1/cli/src/daemon.rs)、[runtime](https://github.com/socai-io/socai/blob/v0.6.1/core/src/runtime/engine.rs)、[CDP生命周期](https://github.com/socai-io/socai/blob/v0.6.1/core/src/cdp/lifecycle.rs)、[原始WebSocket客户端](https://github.com/socai-io/socai/blob/v0.6.1/core/src/cdp/raw_client.rs)。

- daemon空闲退出阈值24小时，按实际平台命令更新活动时间；status不更新这个计时。本次daemon持续运行，退出阈值没有触发。
- runtime的90秒空闲释放只检查远端托管会话。本次连接模式为existing，不属于remote。
- CDP连接建立后，每2秒调用Target.getTargets；连续3次失败才记录断开。socai已经在检查连接，再加FareScout网页轮询不能保证睡眠期间维持连接。
- raw_client在WebSocket关闭、读写错误或命令通道关闭时退出循环。起初的close code / close reason并没有单独记录成持久日志；后续轮询只能看到session is closed。本次系统统一日志在断开前后50秒也没有找到相关Chrome/socai记录。因此目前缺少更直接的首次断线原因。
- FareScout的command_json只对create_subprocess_exec返回的客户端进程执行kill，没有killpg、pkill、socai stop或Chrome退出命令。socai取消客户端请求时，只取消正在建立的连接；已经建立的浏览器保持连接。以前的真实客户端取消探测也观察到daemon、Chrome和CDP连接均保持。

## 解决方案

### 先保留现有Chrome方式，减少研究期间的睡眠影响

建议给FareScout增加可选的macOS防空闲睡眠措施：执行研究时取得电源断言，任务完成或异常退出时释放。持续研究/演示时，可以由用户明确选择在整个工作台会话期间保持系统唤醒。屏幕可以休眠；机器合盖、手动睡眠或退出Chrome后仍允许断开，不能承诺跨这些动作永久免确认。

在完整开发前，可以用系统自带工具做对照实验。先结束当前工作台服务，再从项目目录启动：

```sh
caffeinate -i ./scripts/run-this-machine.sh serve --port 8768
```

本机man caffeinate确认：-i阻止系统空闲睡眠，运行子命令时断言持续到子命令结束。它不修改永久电源设置。服务长期运行会让电脑更久保持唤醒，用户需要知道这一点；这条命令尚未替用户执行。

仅在任务执行时防睡眠，无法解决上午研究结束、午间机器睡眠、下午继续研究的全部问题。如果目标是整天随时研究且不反复确认，应继续评估专用浏览器方案。

### 断开后恢复已有研究，并给用户足够的确认时间

现有恢复功能保留同一个Turn、原文时间和日期探索，过旧报价只重验原选定日，已经实测。CDP断开后不在后台反复请求授权；用户选择恢复时才请求一次新的连接。

需要进一步调整socai的本机existing连接建立过程：人工授权时采用一次较长的等待，而不是20秒后反复重新握手。已建立连接上的网页命令仍用短超时。这个改动需要socai提供可配置选项，或在固定版本上做小范围补丁并向上游提交；当前没有修改或替换已运行的socai二进制。更长等待只解决“来不及点允许”，不能让已丢失的授权永久有效。

### 如果产品要求跨较长空闲时间可靠恢复，评估专用持久Chrome profile

继续用socai的managed能力或单独启动Chrome，给FareScout使用独立、持久的user-data-dir，通过专用调试端口连接。用户首次在这个浏览器登录小红书；不复制日常Chrome的Cookie或profile。

这种方式把研究浏览器与用户日常浏览器分开，并通过专用启动方式减少对chrome://inspect逐次确认流程的依赖。仍要实测小红书登录保持、睡眠后重连、daemon重启后的恢复和Chrome版本差异；不能现在就称为已经解决。socai的chrome.profile / chrome.profile_dir能力可复用，无需迁移Agent Runtime。本次没有更改这些全局配置。

### 补上首次断线日志，再用对照实验确认

最值得补的socai诊断是：WebSocket第一次关闭的时间、close code、脱敏原因类别、读写错误类别及正常disconnect调用原因。不能只保留后续session is closed；也不能把原始URL、Cookie或令牌写入日志。

建议验收分三组：

1. 保持电脑唤醒，不做额外社区搜索，间隔10分钟、1小时、3小时后重复调用，记录CDP TCP是否还是同一条、是否再弹窗、daemon启动时间是否变化。
2. 用户主动睡眠并唤醒，记录断开位置和新的授权请求；这个实验会影响电脑，不自动替用户执行。
3. 在已连接状态取消一个FareScout CLI客户端，确认daemon和已建立CDP保持；将它与前两组区分。

如果第一组稳定、第二组断开，优先采用防睡眠加恢复流程；若保持唤醒仍会断开，则用首次WebSocket日志继续定位Chrome或socai问题，再比较专用profile。以上新实验尚未完成，不计作稳定性通过。

## 可复用的检查工具

新增[scripts/diagnose-socai-connection.py](../../scripts/diagnose-socai-connection.py)。它只读status、进程启动时间、endpoint指纹和相关日志，不发起CDP连接，不改电源设置，不重启浏览器。今日结果见[脱敏诊断记录](../../reports/recovery/cdp-disconnect-diagnosis.json)。受限执行环境可能读不到进程或IPC，需要在正常本机终端运行。启动时间和睡眠时间只保留与排查相关的范围。
