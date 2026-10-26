"""SQLite 连接、建表与 schema 版本管理。"""

from __future__ import annotations

import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_VERSION = 1

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY,
      company TEXT NOT NULL CHECK (length(trim(company)) BETWEEN 1 AND 100),
      job_title TEXT NOT NULL CHECK (length(trim(job_title)) BETWEEN 1 AND 100),
      job_type TEXT NOT NULL CHECK (job_type IN ('校招', '实习')),
      city TEXT CHECK (city IS NULL OR length(city) <= 60),
      job_url TEXT UNIQUE,
      status TEXT NOT NULL CHECK (status IN
        ('收藏', '准备投递', '已投递', '测评/笔试', '面试',
         'Offer', '已拒绝', '已结束', '已放弃')),
      applied_at TEXT,
      deadline TEXT,
      next_action TEXT CHECK (next_action IS NULL OR length(next_action) <= 200),
      next_action_date TEXT,
      notes TEXT CHECK (notes IS NULL OR length(notes) <= 2000),
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      CHECK (next_action_date IS NULL OR coalesce(length(trim(next_action)), 0) > 0)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_deadline ON jobs(deadline)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_action_date ON jobs(next_action_date)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_updated ON jobs(updated_at DESC, id DESC)",
)


class UnsupportedSchemaVersion(RuntimeError):
    pass


def default_db_path() -> Path:
    override = os.environ.get("JOBPILOT_DB_PATH")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[2] / "data" / "jobpilot.db"


class Database:
    def __init__(self, path: str | Path | None = None, *, timeout: float = 5.0):
        self.path = Path(path) if path is not None else default_db_path()
        self.timeout = timeout

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=self.timeout)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise UnsupportedSchemaVersion(
                    f"数据库版本 {version} 高于当前程序支持的版本 {SCHEMA_VERSION}"
                )
            if version == 0:
                with connection:
                    for statement in SCHEMA_STATEMENTS:
                        connection.execute(statement)
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
