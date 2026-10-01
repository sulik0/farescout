from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse


class SourceFailure(Exception):
    def __init__(self, source: str, code: str, message: str):
        self.source, self.code = source, code
        super().__init__(f"{code}: {message}")


def public_url(value: str) -> str:
    """Never persist xsec_token, session IDs, booking tokens or API keys."""
    u = urlparse(value)
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        return ""
    if any(part in u.path.lower() for part in ["checkout", "payment", "passenger", "order", "booking"]):
        return ""
    return urlunparse(("https", u.hostname, u.path, "", "", ""))


def clean_text(value: object, max_length: int = 16000) -> str:
    text = str(value or "")[:max_length]
    text = re.sub(r"https?://[^\s<>\"]+", lambda m: public_url(m[0]) or "[链接已隐藏]", text)
    text = re.sub(r"(?i)(api[_-]?key|xsec_token|session[_-]?token|authorization|cookie|password)\s*[:=]\s*[^\s,;]+", r"\1=[REDACTED]", text)
    return text.replace("\x00", "")


def source_error(source: str, error: Exception) -> SourceFailure:
    # Never stringify provider exceptions: they can contain auth URLs or secrets.
    if isinstance(error, SourceFailure):
        return error
    return SourceFailure(source, type(error).__name__, "来源调用失败；未保存可能含凭证的原始异常")
