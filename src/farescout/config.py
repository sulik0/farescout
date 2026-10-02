from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Settings:
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    model_key: str = field(default="", repr=False)
    serpapi_key: str = field(default="", repr=False)
    flyai_key: str = field(default="", repr=False)
    socai_bin: str = "socai"
    flyai_bin: str = "flyai"
    data_dir: Path = Path("data")
    source_timeout: int = 90
    max_seconds: int = 480
    max_fare_calls: int = 10
    max_date_calls: int = 25
    coarse_dates: int = 3
    fine_dates: int = 1
    socai_notes: int = 3
    socai_mode: str = "selective"
    socai_comments: int = 1
    socai_connect_timeout: int = 180
    fare_concurrency: int = 2
    quote_reuse_seconds: int = 120
    date_hint_source: str = "explore"
    evidence_quality: bool = True
    deal_strength: bool = True
    web_fallback: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(Path.cwd() / ".env", override=False)
        return cls(
            model=os.getenv("FARESCOUT_MODEL", "deepseek-chat"),
            base_url=os.getenv("FARESCOUT_MODEL_BASE_URL", "https://api.deepseek.com"),
            model_key=os.getenv("FARESCOUT_MODEL_API_KEY", ""),
            serpapi_key=os.getenv("SERPAPI_API_KEY", ""),
            flyai_key=os.getenv("FLYAI_API_KEY", ""),
            socai_bin=os.getenv("SOCAI_BIN", "socai"),
            flyai_bin=os.getenv("FLYAI_BIN", "flyai"),
            data_dir=Path(os.getenv("FARESCOUT_DATA_DIR", "data")),
            source_timeout=max(5, min(180, int(os.getenv("FARESCOUT_SOURCE_TIMEOUT", "90")))),
            max_seconds=max(15, min(900, int(os.getenv("FARESCOUT_MAX_SECONDS", "480")))),
            max_fare_calls=max(1, min(20, int(os.getenv("FARESCOUT_MAX_FARE_CALLS", "10")))),
            max_date_calls=max(0, min(40, int(os.getenv("FARESCOUT_MAX_DATE_CALLS", "25")))),
            coarse_dates=max(2, min(5, int(os.getenv("FARESCOUT_COARSE_DATES", "3")))),
            fine_dates=max(0, min(2, int(os.getenv("FARESCOUT_FINE_DATES", "1")))),
            socai_notes=max(2, min(5, int(os.getenv("FARESCOUT_SOCAI_NOTES", "3")))),
            socai_mode=os.getenv("FARESCOUT_SOCAI_MODE", "selective"),
            socai_comments=max(0, min(3, int(os.getenv("FARESCOUT_SOCAI_COMMENTS", "1")))),
            socai_connect_timeout=max(60, min(300, int(os.getenv("FARESCOUT_SOCAI_CONNECT_TIMEOUT", "180")))),
            fare_concurrency=max(1, min(3, int(os.getenv("FARESCOUT_FARE_CONCURRENCY", "2")))),
            quote_reuse_seconds=max(0, min(180, int(os.getenv("FARESCOUT_QUOTE_REUSE_SECONDS", "120")))),
            date_hint_source=os.getenv("FARESCOUT_DATE_HINT_SOURCE", "explore"),
            evidence_quality=os.getenv("FARESCOUT_EVIDENCE_QUALITY", "1") == "1",
            deal_strength=os.getenv("FARESCOUT_DEAL_STRENGTH", "1") == "1",
            web_fallback=os.getenv("FARESCOUT_WEB_FALLBACK", "1") == "1",
        )
