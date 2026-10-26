"""与 Streamlit 无关的字段校验和标准化。"""

from __future__ import annotations

import re
from datetime import date
from typing import Mapping
from urllib.parse import urlsplit

from .models import APPLIED_STATUSES, JOB_FIELD_NAMES, JOB_TYPES, STATUSES, Job, JobValues


class ValidationError(ValueError):
    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__("；".join(errors.values()))


def _text(value: object, field: str, maximum: int, errors: dict[str, str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors[field] = "请输入文本"
        return None
    cleaned = value.strip()
    if len(cleaned) > maximum:
        errors[field] = f"不能超过 {maximum} 个字符"
    return cleaned or None


def _date(value: object, field: str, errors: dict[str, str]) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        errors[field] = "请输入有效的日期（YYYY-MM-DD）"
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors[field] = "请输入有效的日期（YYYY-MM-DD）"
        return None


def normalize_job(
    raw: Mapping[str, object],
    *,
    today: date,
    previous: Job | None = None,
    applied_at_provided: bool = False,
) -> JobValues:
    """校验输入；进入已投递及后续阶段时自动补首次投递日期。"""

    unexpected = set(raw) - set(JOB_FIELD_NAMES)
    if unexpected:
        raise ValidationError({"form": "包含未知字段"})

    errors: dict[str, str] = {}
    company = _text(raw.get("company"), "company", 100, errors)
    title = _text(raw.get("job_title"), "job_title", 100, errors)
    job_type = raw.get("job_type", "校招")
    city = _text(raw.get("city"), "city", 60, errors)
    url = _text(raw.get("job_url"), "job_url", 2048, errors)
    status = raw.get("status", "收藏")
    applied_at = _date(raw.get("applied_at"), "applied_at", errors)
    deadline = _date(raw.get("deadline"), "deadline", errors)
    next_action = _text(raw.get("next_action"), "next_action", 200, errors)
    next_action_date = _date(raw.get("next_action_date"), "next_action_date", errors)
    notes = _text(raw.get("notes"), "notes", 2000, errors)

    if not company:
        errors.setdefault("company", "请填写公司名称")
    if not title:
        errors.setdefault("job_title", "请填写岗位名称")
    if job_type not in JOB_TYPES:
        errors["job_type"] = "请选择招聘类型"
    if status not in STATUSES:
        errors["status"] = "请选择有效的投递状态"

    if url:
        try:
            parsed = urlsplit(url)
            if (
                parsed.scheme.lower() not in ("http", "https")
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or any(ch.isspace() for ch in url)
            ):
                raise ValueError
            _ = parsed.port
        except ValueError:
            errors["job_url"] = "请输入有效的招聘链接"

    if applied_at and applied_at > today:
        errors["applied_at"] = "首次投递日期不能晚于今天"
    if next_action_date and not next_action:
        errors["next_action"] = "填写任务日期时，请同时填写下一步任务"

    if status in APPLIED_STATUSES and applied_at is None:
        if previous and previous.applied_at and applied_at_provided:
            errors["applied_at"] = "当前状态下不能清空首次投递日期"
        else:
            applied_at = today

    if errors:
        raise ValidationError(errors)

    return JobValues(
        company=company,
        job_title=title,
        job_type=job_type,
        city=city,
        job_url=url,
        status=status,
        applied_at=applied_at,
        deadline=deadline,
        next_action=next_action,
        next_action_date=next_action_date,
        notes=notes,
    )
