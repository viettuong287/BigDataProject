"""Tiện ích dùng chung: kết nối Neon, đường dẫn repo, logger ghi song song ra file."""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SQL_DIR = ROOT / "sql"
EVIDENCE_DIR = ROOT / "evidence"


def neon_url(direct: bool = True) -> str:
    """Trả về chuỗi kết nối Neon. direct=True bỏ '-pooler' để COPY/DDL không qua PgBouncer."""
    url = os.environ.get("NEON_DATABASE_URL")
    if not url:
        sys.exit("Thiếu NEON_DATABASE_URL (xem .env.example)")
    if direct:
        url = re.sub(r"-pooler(?=\.)", "", url, count=1)
    return url


def connect(direct: bool = True, autocommit: bool = True) -> psycopg.Connection:
    return psycopg.connect(neon_url(direct), autocommit=autocommit, connect_timeout=30)


def mask(url: str) -> str:
    return re.sub(r":[^:@/]+@", ":****@", url)


class Tee:
    """In ra màn hình và ghi cùng nội dung vào file log trong evidence/."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.f = path.open("w", encoding="utf-8")

    def __call__(self, msg: str = "") -> None:
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
        print(line, flush=True)
        self.f.write(line + "\n")
        self.f.flush()

    def close(self) -> None:
        self.f.close()
