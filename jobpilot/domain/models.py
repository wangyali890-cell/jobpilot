"""岗位数据结构；日期在领域层保持为 ``date``。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


JOB_FIELD_NAMES = (
    "company",
    "job_title",
    "job_type",
    "city",
    "job_url",
    "status",
    "applied_at",
    "deadline",
    "next_action",
    "next_action_date",
    "notes",
)

STATUSES = (
    "收藏",
    "准备投递",
    "已投递",
    "测评/笔试",
    "面试",
    "Offer",
    "已拒绝",
    "已结束",
    "已放弃",
)
JOB_TYPES = ("校招", "实习")
APPLIED_STATUSES = frozenset(("已投递", "测评/笔试", "面试", "Offer"))
TERMINAL_STATUSES = frozenset(("Offer", "已拒绝", "已结束", "已放弃"))


@dataclass(frozen=True, kw_only=True)
class JobValues:
    company: str
    job_title: str
    job_type: str
    city: str | None
    job_url: str | None
    status: str
    applied_at: date | None
    deadline: date | None
    next_action: str | None
    next_action_date: date | None
    notes: str | None


@dataclass(frozen=True, kw_only=True)
class Job(JobValues):
    id: int
    created_at: str
    updated_at: str


@dataclass(frozen=True, kw_only=True)
class JobFilters:
    query: str = ""
    status: str | None = None
    job_type: str | None = None
    city: str | None = None


@dataclass(frozen=True, kw_only=True)
class DueItem:
    job_id: int
    company: str
    job_title: str
    due_date: date
    kind: str
    detail: str | None = None


@dataclass(frozen=True, kw_only=True)
class Overview:
    total_jobs: int
    applied_jobs: int
    interviewing_jobs: int
    upcoming: tuple[DueItem, ...]
    overdue: tuple[DueItem, ...]
