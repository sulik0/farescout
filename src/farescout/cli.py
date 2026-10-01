from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

from .bridge import BrowserBridge
from .config import Settings
from .engine import Researcher, Store
from .models import FareRequest, now
from .providers import FlyAI, RedditCommunity, SerpAPI, Socai, command_json
from .report import render_report
from .research import Brain, evolve_goal, today_local
from .safety import source_error


def progress(event):
    print(f"[{event.stage}] {event.source or 'FareScout'} {event.status}: {event.detail}", file=sys.stderr, flush=True)


async def doctor(settings: Settings) -> dict:
    result = {
        "model_configured": bool(settings.model_key),
        "serpapi_configured": bool(settings.serpapi_key),
        "flyai_key_configured": bool(settings.flyai_key),
        "socai_installed": bool(shutil.which(settings.socai_bin)),
        "flyai_installed": bool(shutil.which(settings.flyai_bin)),
        "browser": "unknown",
        "secrets": "配置值不会输出，仅读取是否存在",
    }
    if result["socai_installed"]:
        try:
            state = await command_json(settings.socai_bin, ["status", "--json"], settings, "socai")
            result["browser"] = {
                k: state.get(k) for k in ["cli_version", "browser_connected", "browser_state", "profile_mode", "error_code"]
            }
        except Exception as error:
            result["browser"] = str(source_error("socai", error))
    return result


async def spike(settings: Settings) -> dict:
    """A live source probe, explicitly NOT a completed discovery run."""
    result = {"kind": "technical_spike_not_end_to_end", "started_at": now().isoformat(), "sources": {}}
    try:
        plan = await Brain(settings).plan("深圳香港便宜国际机票", evolve_goal("深圳香港便宜国际机票"))
        result["sources"]["model"] = {"status": "PASS", "queries": plan}
    except Exception as error:
        result["sources"]["model"] = {"status": "FAIL", "reason": str(source_error("model", error))}
    for query in ["深圳 香港 便宜国际机票", "香港 国际机票 促销"]:
        name = "socai:" + query
        try:
            items = await Socai(settings).search(query)
            result["sources"][name] = {"status": "PASS", "evidence": [e.model_dump(mode="json") for e in items]}
        except Exception as error:
            result["sources"][name] = {"status": "FAIL", "reason": str(source_error(name, error))}
    from datetime import timedelta
    request = FareRequest(origin="HKG", destination="HND", outbound_date=today_local() + timedelta(days=14))
    result["fare_probe_note"] = "预先指定路线仅用于验证 API 能力；不是由社区发现，不能计作完整 P0"
    for provider in [FlyAI(settings), SerpAPI(settings)]:
        try:
            fares = await provider.verify(request)
            result["sources"][provider.name] = {"status": "PASS", "fares": [f.model_dump(mode="json") for f in fares]}
        except Exception as error:
            result["sources"][provider.name] = {"status": "FAIL", "reason": str(source_error(provider.name, error))}
    result["finished_at"] = now().isoformat()
    return result


async def async_main(args):
    settings = Settings.from_env()
    if args.command == "doctor":
        print(json.dumps(await doctor(settings), ensure_ascii=False, indent=2))
        return 0
    if args.command == "spike":
        data = await spike(settings)
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        output = settings.data_dir / "technical-spike.json"
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(str(output.resolve()))
        return 0 if all(x["status"] == "PASS" for x in data["sources"].values()) else 2
    store = Store(settings.data_dir)
    session = store.load(args.session)
    if args.command == "report":
        if not session or not session.turns:
            print("没有此会话的研究报告", file=sys.stderr)
            return 2
        print(render_report(session, session.turns[-1]))
        return 0
    social = None
    if args.browser_bridge:
        social = [BrowserBridge(Path(args.browser_bridge))] + ([RedditCommunity(settings)] if settings.web_fallback else [])
    engine = Researcher(settings, social=social, on_event=progress)
    messages = [args.message] if args.command == "run" else ([session.turns[-1].user_input] if args.command == "resume" and session and session.turns else [])
    if args.command == "resume" and not messages:
        print("没有可续跑的会话", file=sys.stderr)
        return 2
    while True:
        if args.command == "chat":
            try:
                message = input("飞探 > ").strip()
            except EOFError:
                break
            if message in {"exit", "quit", "退出"}:
                break
            if not message:
                continue
        else:
            message = messages.pop()
        session = await engine.run(message, session, args.session, resume=args.command == "resume")
        store.save(session)
        print(render_report(session, session.turns[-1]))
        print(f"会话已保存：{store.path(session.id).resolve()}", file=sys.stderr)
        if args.command in {"run", "resume"}:
            return 0 if session.turns[-1].status == "complete" else 2
    return 0


def main():
    parser = argparse.ArgumentParser(description="飞探 FareScout：社区发现 → 自主调查 → 实时验价。只读，不预订。")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="隐私安全的环境诊断，不打开浏览器")
    sub.add_parser("spike", help="真实来源技术验证（可能产生 API 用量）")
    web = sub.add_parser("serve", help="本机实时研究轨迹界面与历史回放")
    web.add_argument("--port", type=int, default=8765)
    for name in ["run", "chat", "report", "resume"]:
        p = sub.add_parser(name)
        p.add_argument("--session", default="default")
        if name == "run":
            p.add_argument("message")
        if name in {"run", "chat", "resume"}:
            p.add_argument("--browser-bridge", help="宿主 Browser Harness 回执目录，独立 CLI 默认使用 socai")
    try:
        args = parser.parse_args()
        if args.command == "serve":
            from .web import serve
            serve(Settings.from_env(), args.port)
            return_code = 0
        else:
            return_code = asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("研究已中断。", file=sys.stderr)
        return_code = 130
    except Exception as error:
        print(str(source_error("cli", error)), file=sys.stderr)
        return_code = 2
    raise SystemExit(return_code)


if __name__ == "__main__":
    main()
