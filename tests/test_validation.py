from datetime import date

import pytest

from jobpilot.domain.validation import ValidationError, normalize_job


TODAY = date(2026, 10, 26)


def test_minimum_record_is_normalized():
    job = normalize_job({"company": "  星河科技  ", "job_title": " 产品经理 "}, today=TODAY)
    assert job.company == "星河科技"
    assert job.job_title == "产品经理"
    assert job.job_type == "校招"
    assert job.status == "收藏"
    assert job.job_url is None
    assert job.applied_at is None


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"company": " ", "job_title": "产品经理"}, "company"),
        ({"company": "星河", "job_title": " "}, "job_title"),
        ({"company": "星河", "job_title": "A" * 101}, "job_title"),
        ({"company": "星河", "job_title": "产品经理", "job_url": "javascript:alert(1)"}, "job_url"),
        ({"company": "星河", "job_title": "产品经理", "job_url": "https://"}, "job_url"),
        ({"company": "星河", "job_title": "产品经理", "deadline": "2026-02-30"}, "deadline"),
        ({"company": "星河", "job_title": "产品经理", "applied_at": "2026-10-27"}, "applied_at"),
        ({"company": "星河", "job_title": "产品经理", "next_action_date": "2026-10-27"}, "next_action"),
        ({"company": "星河", "job_title": "产品经理", "status": "未知"}, "status"),
    ],
)
def test_invalid_fields_return_field_specific_errors(payload, field):
    with pytest.raises(ValidationError) as error:
        normalize_job(payload, today=TODAY)
    assert field in error.value.errors


def test_applied_status_fills_first_application_date():
    job = normalize_job(
        {"company": "星河", "job_title": "产品经理", "status": "面试"},
        today=TODAY,
    )
    assert job.applied_at == TODAY


def test_past_deadlines_and_tasks_are_allowed():
    job = normalize_job(
        {
            "company": "星河",
            "job_title": "产品经理",
            "deadline": "2026-10-20",
            "next_action": "准备面试",
            "next_action_date": "2026-10-25",
        },
        today=TODAY,
    )
    assert job.deadline == date(2026, 10, 20)
    assert job.next_action_date == date(2026, 10, 25)
