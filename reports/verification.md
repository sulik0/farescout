# 工程验证记录（最新）

2026-09-30，本机实际执行：

```text
PYTHONPATH=src /private/tmp/farescout-poc-venv/bin/python -m pytest -q
...............................                                          [100%]
31 passed in 6.82s
```

`python -m pip install -e . --no-deps` 已成功构建并安装 `farescout-0.1.0`；`farescout --help` 可用。宿主浏览器路径与后续独立 socai 路径的真实记录分别留存。最新独立运行：4 轮会话、12 篇正文、首轮 5 条验价路线、3 次成功追问；FlyAI 和 SerpAPI 均实际返回报价。每条模型引用可在原正文/评论找到，票价航段、日期、机场和红眼条件通过程序校验。

早期 doctor 显示 socai 未连接、SerpAPI 未配置；用户更新本机配置后已重测。旧状态保留在技术历史中，不代表最新验收。隔离测试的构造数据只验证程序，不代替真实来源研究。交付压缩包排除 `.env`、`data/` 等私有运行目录。

完成完整运行后，又对 socai 进行独立只读复测，取得 5 篇正文、4 条评论；其后状态查询 `browser_connected=true`。空闲时曾出现暂时的 disconnected 状态，详见技术验证历史。
