import sqlite3
from datetime import date, timedelta

import pytest

from jobpilot.domain.models import JobFilters
from jobpilot.domain.service import DuplicateJobLink, JobNotFound, JobService
from jobpilot.domain.validation import ValidationError


TODAY = date(2026, 10, 26)


@pytest.fixture
def service(tmp_path):
    return JobService(tmp_path / "jobpilot.db", today_provider=lambda: TODAY, timeout=0.05)


def test_create_persists_after_reopening_and_schema_is_versioned(service):
    created = service.create_job({"company": "星河科技", "job_title": "产品经理"})
    reopened = JobService(service.database.path, today_provider=lambda: TODAY)
    assert reopened.get_job(created.id).company == "星河科技"
    with sqlite3.connect(service.database.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1


def test_duplicate_link_is_blocked_but_same_job_can_keep_its_link(service):
    first = service.create_job(
        {"company": "星河", "job_title": "产品经理", "job_url": " https://example.com/123 "}
    )
    updated = service.update_job(first.id, {"notes": "已阅读要求"})
    assert updated.job_url == "https://example.com/123"
    with pytest.raises(DuplicateJobLink) as error:
        service.create_job(
            {"company": "远山", "job_title": "产品经理", "job_url": "https://example.com/123"}
        )
    assert error.value.existing_job.id == first.id
    assert len(service.list_jobs()) == 1


def test_update_delete_and_missing_job(service):
    first = service.create_job({"company": "星河", "job_title": "产品经理"})
    second = service.create_job({"company": "远山", "job_title": "增长产品经理"})
    edited = service.update_job(first.id, {"city": "北京", "notes": "已收藏"})
    assert (edited.city, edited.notes) == ("北京", "已收藏")
    service.delete_job(first.id)
    assert [job.id for job in service.list_jobs()] == [second.id]
    with pytest.raises(JobNotFound):
        service.get_job(first.id)
    with pytest.raises(JobNotFound):
        service.delete_job(first.id)


def test_status_can_skip_stages_and_applied_count_survives_terminal_status(service):
    job = service.create_job({"company": "星河", "job_title": "产品经理"})
    changed = service.set_status(job.id, "面试")
    assert changed.applied_at == TODAY
    assert service.get_overview().applied_jobs == 1
    assert service.get_overview().interviewing_jobs == 1
    unchanged = service.set_status(job.id, "面试")
    assert unchanged.updated_at == changed.updated_at
    rejected = service.set_status(job.id, "已拒绝")
    assert rejected.applied_at == TODAY
    assert service.get_overview().applied_jobs == 1
    assert service.get_overview().interviewing_jobs == 0


def test_first_application_date_can_only_be_cleared_outside_applied_stages(service):
    job = service.create_job({"company": "星河", "job_title": "产品经理", "status": "已投递"})
    with pytest.raises(ValidationError) as error:
        service.update_job(job.id, {"applied_at": None})
    assert "applied_at" in error.value.errors
    service.set_status(job.id, "已放弃")
    cleared = service.update_job(job.id, {"applied_at": None})
    assert cleared.applied_at is None


def test_search_and_filters_combine_and_treat_wildcards_as_text(service):
    service.create_job({"company": "星河科技", "job_title": "AI 产品经理", "city": "北京"})
    service.create_job({"company": "星河科技", "job_title": "增长产品经理", "city": "上海", "job_type": "实习"})
    service.create_job({"company": "远山", "job_title": "运营", "city": "北京"})
    found = service.list_jobs(JobFilters(query="星河", city="北京", job_type="校招"))
    assert [job.job_title for job in found] == ["AI 产品经理"]
    assert service.list_jobs(JobFilters(query="%")) == []
    assert service.list_jobs(JobFilters(query="' OR 1=1--")) == []


def test_overview_date_boundaries_and_terminal_exclusion(service):
    service.create_job(
        {
            "company": "今天",
            "job_title": "岗位一",
            "deadline": TODAY,
            "next_action": "准备笔试",
            "next_action_date": TODAY + timedelta(days=7),
        }
    )
    service.create_job(
        {"company": "昨天", "job_title": "岗位二", "deadline": TODAY - timedelta(days=1)}
    )
    service.create_job(
        {"company": "第八天", "job_title": "岗位三", "deadline": TODAY + timedelta(days=8)}
    )
    service.create_job(
        {"company": "终止", "job_title": "岗位四", "status": "Offer", "deadline": TODAY}
    )
    service.create_job({"company": "无日期", "job_title": "岗位五"})
    overview = service.get_overview()
    assert overview.total_jobs == 5
    assert overview.applied_jobs == 1
    assert [item.due_date for item in overview.upcoming] == [TODAY, TODAY + timedelta(days=7)]
    assert [item.company for item in overview.overdue] == ["昨天"]


def test_locked_database_does_not_change_old_status(service):
    job = service.create_job({"company": "星河", "job_title": "产品经理"})
    lock = sqlite3.connect(service.database.path)
    try:
        lock.execute("BEGIN IMMEDIATE")
        with pytest.raises(sqlite3.OperationalError):
            service.set_status(job.id, "面试")
    finally:
        lock.rollback()
        lock.close()
    assert service.get_job(job.id).status == "收藏"
    assert service.get_job(job.id).applied_at is None
