"""岗位管理、投递状态与日期统计的单一业务入口。"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Mapping
from zoneinfo import ZoneInfo

from jobpilot.storage.db import Database
from jobpilot.storage.jobs import JobRepository

from .models import (
    JOB_FIELD_NAMES,
    JOB_TYPES,
    STATUSES,
    TERMINAL_STATUSES,
    DueItem,
    Job,
    JobFilters,
    Overview,
)
from .validation import ValidationError, normalize_job


SHANGHAI = ZoneInfo("Asia/Shanghai")


class JobNotFound(LookupError):
    pass


class DuplicateJobLink(ValueError):
    def __init__(self, existing_job: Job | None = None):
        self.existing_job = existing_job
        super().__init__("该链接已保存，请编辑现有岗位")


class JobService:
    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        today_provider: Callable[[], date] | None = None,
        timeout: float = 5.0,
    ):
        self.database = Database(db_path, timeout=timeout)
        self.database.initialize()
        self.repository = JobRepository(self.database)
        self.today_provider = today_provider or (lambda: datetime.now(SHANGHAI).date())

    def _timestamp(self) -> str:
        return datetime.now(SHANGHAI).isoformat(timespec="microseconds")

    def get_job(self, job_id: int) -> Job:
        job = self.repository.get(job_id)
        if job is None:
            raise JobNotFound(f"岗位 {job_id} 不存在")
        return job

    def create_job(self, raw: Mapping[str, object]) -> Job:
        values = normalize_job(raw, today=self.today_provider())
        if values.job_url:
            existing = self.repository.get_by_url(values.job_url)
            if existing:
                raise DuplicateJobLink(existing)
        try:
            return self.repository.create(values, self._timestamp())
        except sqlite3.IntegrityError as exc:
            existing = self.repository.get_by_url(values.job_url) if values.job_url else None
            if existing:
                raise DuplicateJobLink(existing) from exc
            raise

    def update_job(self, job_id: int, changes: Mapping[str, object]) -> Job:
        current = self.get_job(job_id)
        unexpected = set(changes) - set(JOB_FIELD_NAMES)
        if unexpected:
            raise ValidationError({"form": "包含未知字段"})
        raw = {name: getattr(current, name) for name in JOB_FIELD_NAMES}
        raw.update(changes)
        values = normalize_job(
            raw,
            today=self.today_provider(),
            previous=current,
            applied_at_provided="applied_at" in changes,
        )
        if values.job_url:
            existing = self.repository.get_by_url(values.job_url)
            if existing and existing.id != job_id:
                raise DuplicateJobLink(existing)
        try:
            result = self.repository.update(job_id, values, self._timestamp())
        except sqlite3.IntegrityError as exc:
            if values.job_url:
                existing = self.repository.get_by_url(values.job_url)
                if existing and existing.id != job_id:
                    raise DuplicateJobLink(existing) from exc
            raise
        if result is None:
            raise JobNotFound(f"岗位 {job_id} 不存在")
        return result

    def delete_job(self, job_id: int) -> None:
        if not self.repository.delete(job_id):
            raise JobNotFound(f"岗位 {job_id} 不存在")

    def set_status(self, job_id: int, status: str) -> Job:
        if status not in STATUSES:
            raise ValidationError({"status": "请选择有效的投递状态"})
        current = self.get_job(job_id)
        if current.status == status:
            return current
        return self.update_job(job_id, {"status": status})

    def list_jobs(self, filters: JobFilters | None = None) -> list[Job]:
        if filters:
            errors: dict[str, str] = {}
            if filters.status and filters.status not in STATUSES:
                errors["status"] = "请选择有效的投递状态"
            if filters.job_type and filters.job_type not in JOB_TYPES:
                errors["job_type"] = "请选择招聘类型"
            if errors:
                raise ValidationError(errors)
        return self.repository.list(filters)

    def get_overview(self, *, as_of: date | None = None) -> Overview:
        today = as_of or self.today_provider()
        last_upcoming = today + timedelta(days=7)
        jobs = self.repository.list()
        upcoming: list[DueItem] = []
        overdue: list[DueItem] = []
        for job in jobs:
            if job.status in TERMINAL_STATUSES:
                continue
            sources = (
                (job.deadline, "招聘截止", None),
                (job.next_action_date, "下一步任务", job.next_action),
            )
            for due_date, kind, detail in sources:
                if due_date is None:
                    continue
                item = DueItem(
                    job_id=job.id,
                    company=job.company,
                    job_title=job.job_title,
                    due_date=due_date,
                    kind=kind,
                    detail=detail,
                )
                if due_date < today:
                    overdue.append(item)
                elif due_date <= last_upcoming:
                    upcoming.append(item)

        sort_key = lambda item: (item.due_date, item.company, item.job_title, item.kind)
        return Overview(
            total_jobs=len(jobs),
            applied_jobs=sum(job.applied_at is not None for job in jobs),
            interviewing_jobs=sum(job.status == "面试" for job in jobs),
            upcoming=tuple(sorted(upcoming, key=sort_key)),
            overdue=tuple(sorted(overdue, key=sort_key)),
        )
