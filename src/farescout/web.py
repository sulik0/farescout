from __future__ import annotations

import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .engine import Researcher, Store
from .report import render_report
from .safety import clean_text, source_error


class Application:
    def __init__(self, settings, researcher_factory=Researcher):
        self.settings, self.factory = settings, researcher_factory
        self.store = Store(settings.data_dir)
        self.lock = threading.Lock()
        self.active = None
        self.error = None
        self.error_session = None

    def start(self, session_id, message, *, resume=False):
        self.store.path(session_id)
        if resume:
            saved = self.store.load(session_id)
            if not saved or not saved.turns or saved.turns[-1].status == 'complete':
                raise ValueError('只能恢复已有未完成的最后一轮研究')
            message = saved.turns[-1].user_input
        if not message.strip() or len(message) > 3000:
            raise ValueError("请输入1～3000字的研究需求")
        with self.lock:
            if self.active:
                raise RuntimeError("已有研究进行中，请等待完成再继续")
            self.active, self.error, self.error_session = session_id, None, None
        def work():
            try:
                researcher = self.factory(self.settings)
                options = {'resume': True} if resume else {}
                asyncio.run(researcher.run(clean_text(message, 3000), self.store.load(session_id), session_id, **options))
            except Exception as error:
                self.error = str(source_error("research", error))
                self.error_session = session_id
            finally:
                with self.lock:
                    self.active = None
        threading.Thread(target=work, daemon=True).start()


def create_server(settings, port=8765, researcher_factory=Researcher):
    app = Application(settings, researcher_factory)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def trusted(self):
            expected = f"127.0.0.1:{self.server.server_port}"
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            return host == expected and (origin is None or origin == f"http://{expected}")

        def respond(self, body, status=200, content_type="application/json; charset=utf-8"):
            raw = body.encode() if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if not self.trusted():
                return self.respond({"error": "仅允许本机访问"}, 403)
            parsed = urlparse(self.path)
            if parsed.path == '/api/browser':
                from .providers import Socai
                source = Socai(app.settings)
                try:
                    ready = asyncio.run(source.browser_ready())
                    return self.respond({'ready':ready, 'connection':source.connection})
                except Exception as error:
                    return self.respond({'ready':False, 'connection':source.connection, 'error':str(source_error('socai', error))})
            path = parsed.path
            try:
                if path == "/":
                    return self.respond(Path(__file__).with_name("ui.html").read_text(), content_type="text/html; charset=utf-8")
                assets = {"/assets/ui.css": ("ui.css", "text/css"),
                          "/assets/ui.mjs": ("ui.mjs", "text/javascript"),
                          "/assets/ui-state.mjs": ("ui-state.mjs", "text/javascript")}
                if path in assets:
                    filename, content_type = assets[path]
                    return self.respond(Path(__file__).with_name(filename).read_text(),
                                        content_type=content_type + "; charset=utf-8")
                if path == "/api/sessions":
                    sessions = []
                    for file in sorted(app.store.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                        try:
                            session = app.store.load(file.stem)
                            if session and session.turns:
                                t = session.turns[-1]
                                sessions.append({"id": session.id, "message": t.user_input, "status": t.status,
                                                 "started_at": t.started_at.isoformat(), "turns": len(session.turns)})
                        except (ValueError, OSError):
                            continue
                    return self.respond({"sessions": sessions, "active": app.active})
                parts = path.strip("/").split("/")
                if len(parts) not in {3, 4} or parts[:2] != ["api", "sessions"]:
                    return self.respond({"error": "未找到"}, 404)
                session_id = parts[2]
                app.store.path(session_id)
                if len(parts) == 4 and parts[3] == "events":
                    return self.events(session_id)
                session = app.store.load(session_id)
                if session is None:
                    return self.respond({"error": (app.error if app.error_session == session_id else None) or "会话尚未创建",
                                         "active": app.active}, 404)
                if len(parts) == 4 and parts[3] == "report":
                    if not session.turns:
                        return self.respond({"error": "会话尚无研究轮次"}, 404)
                    turn_id = parse_qs(parsed.query).get("turn", [session.turns[-1].id])[0]
                    turn = next((t for t in session.turns if t.id == turn_id), None)
                    if turn is None:
                        return self.respond({"error": "轮次不存在"}, 404)
                    return self.respond(render_report(session, turn), content_type="text/markdown; charset=utf-8")
                if len(parts) == 4:
                    return self.respond({"error": "未找到"}, 404)
                return self.respond({"session": session.model_dump(mode="json"), "active": app.active,
                                     "error": app.error if app.error_session == session_id else None})
            except (ValueError, OSError):
                return self.respond({"error": "会话无效或无法读取"}, 400)

        def events(self, session_id):
            # Disk is the shared truth for CLI, live UI, reconnect and history replay.
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            last_id = self.headers.get("Last-Event-ID", "")
            seen = set()
            resumed = not last_id
            try:
                for tick in range(3600):
                    session = app.store.load(session_id)
                    if session:
                        events = [e for t in session.turns for e in t.events]
                        if not resumed:
                            known = {e.id for e in events}
                            if last_id not in known:
                                resumed = True
                        for event in events:
                            if not resumed:
                                seen.add(event.id)
                                if event.id == last_id:
                                    resumed = True
                                continue
                            if event.id in seen:
                                continue
                            seen.add(event.id)
                            self.wfile.write(f"id: {event.id}\nevent: research\ndata: {event.model_dump_json()}\n\n".encode())
                        self.wfile.flush()
                    if app.active != session_id:
                        self.wfile.write(b"event: done\ndata: {}\n\n")
                        self.wfile.flush()
                        return
                    if tick % 40 == 0:
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
                    time.sleep(0.25)
            except (BrokenPipeError, ConnectionResetError):
                return

        def do_POST(self):
            if not self.trusted():
                return self.respond({"error": "仅允许本机同源请求"}, 403)
            if self.path not in {"/api/run", "/api/resume"}:
                return self.respond({"error": "未找到"}, 404)
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 20000:
                    raise ValueError()
                data = json.loads(self.rfile.read(length))
                session_id, message = data["session_id"], data.get("message", "")
                if not isinstance(session_id, str) or not isinstance(message, str):
                    raise ValueError()
                app.start(session_id, message, resume=self.path == '/api/resume')
                return self.respond({"session_id": session_id, "status": "started"}, 202)
            except RuntimeError as error:
                return self.respond({"error": str(error)}, 409)
            except (ValueError, KeyError, TypeError):
                return self.respond({"error": "请求格式或会话ID无效"}, 400)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.app = app
    return server


def serve(settings, port):
    server = create_server(settings, port)
    print(f"飞探研究界面：http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
