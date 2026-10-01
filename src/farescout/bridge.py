"""Optional host-browser transport. The host executes read-only research with its
existing Browser Harness; FareScout does not extract or transfer login state.

This is a transport, not a browser implementation. Standalone CLI uses socai.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .models import Evidence, now
from .providers import socai_evidence
from .safety import SourceFailure


class BrowserBridge:
    name = "小红书 / Host Browser Harness"
    timeout_seconds = 300

    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def read_receipt(self, request_path: Path) -> list[Evidence]:
        request = json.loads(request_path.read_text())
        response_path = request_path.with_name(request_path.name.replace('.request.json', '.response.json'))
        data = json.loads(response_path.read_text())
        if data.get("request_id") != request["id"] or data.get("query") != request["query"]:
            raise SourceFailure(self.name, "MISMATCHED_RECEIPT", "浏览器回执与查询不匹配")
        if data.get("error"):
            raise SourceFailure(self.name, "BROWSER_BLOCKED", "浏览器未完成只读研究")
        records = socai_evidence({"notes": data.get("notes", [])}, request["query"])
        # Legacy receipts did not carry a timestamp: their write time is the latest
        # possible observation time, never the time of a later replay/resume.
        observed = datetime.fromisoformat(data["observed_at"]) if data.get("observed_at") else datetime.fromtimestamp(response_path.stat().st_mtime, timezone.utc)
        for record in records:
            record.source = self.name
            record.observed_at = observed
            record.warnings.append("浏览器读取由宿主工具执行；非 socai 独立运行路径")
        if not records:
            raise SourceFailure(self.name, "NO_READABLE_POSTS", "未返回可核查正文")
        return records

    def recover(self, turn):
        for path in sorted(self.directory.glob("*.request.json")):
            request = json.loads(path.read_text())
            started = datetime.fromisoformat(request["requested_at"])
            if started < turn.started_at or (turn.finished_at and started > turn.finished_at):
                continue
            query = request["query"]
            # Only receipts for searches this turn actually requested are eligible.
            events = [e for e in turn.events if e.source == self.name and e.status == "info" and e.detail == f"只读搜索：{query}"]
            if not events or not path.with_name(path.name.replace('.request.json', '.response.json')).exists():
                continue
            yield events[0].stage, query, self.read_receipt(path)

    async def search(self, query: str) -> list[Evidence]:
        request_id = uuid4().hex
        started = now()
        request = {"id": request_id, "operation": "xhs_search_read", "query": query,
                   "max_posts": 5, "max_comments": 5, "requested_at": started.isoformat(),
                   "allowed_actions": ["search", "open_post", "read_body", "read_comments"],
                   "stop_on": ["captcha", "login_required", "access_denied"]}
        request_path = self.directory / f"{request_id}.request.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
        response_path = self.directory / f"{request_id}.response.json"
        try:
            while not response_path.exists():
                await asyncio.sleep(0.5)
            return self.read_receipt(request_path)
        finally:
            # Keep request/response receipts for auditing, mark cancelled requests.
            if not response_path.exists():
                request_path.with_suffix(".cancelled").write_text(now().isoformat())
