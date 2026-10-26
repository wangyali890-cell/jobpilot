"""三页共用同一份岗位数据后的关键使用路径。"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from streamlit.testing.v1 import AppTest

from jobpilot.domain.service import JobService


APP_PATH = Path(__file__).resolve().parents[1] / "jobpilot" / "app.py"


def test_empty_board_and_overview(monkeypatch, tmp_path):
    monkeypatch.setenv("JOBPILOT_DB_PATH", str(tmp_path / "ui.db"))
    app = AppTest.from_file(APP_PATH).run()

    app.switch_page("views/board.py").run()
    assert not app.exception
    assert any("还没有可展示的岗位" in item.value for item in app.info)

    app.switch_page("views/overview.py").run()
    assert not app.exception
    assert [(metric.label, metric.value) for metric in app.metric] == [
        ("岗位总数", "0"),
        ("累计投递数", "0"),
        ("当前面试数", "0"),
    ]


def test_board_status_updates_overview_and_due_item_locates_exact_job(monkeypatch, tmp_path):
    db_path = tmp_path / "ui.db"
    monkeypatch.setenv("JOBPILOT_DB_PATH", str(db_path))
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    service = JobService(db_path)
    first = service.create_job(
        {
            "company": "星河科技",
            "job_title": "产品经理",
            "deadline": today,
            "next_action": "查看邮件",
            "next_action_date": today + timedelta(days=7),
        }
    )
    second = service.create_job({"company": "远山科技", "job_title": "增长实习生"})

    app = AppTest.from_file(APP_PATH).run()
    app.switch_page("views/board.py").run()
    assert not app.exception
    app.selectbox(key=f"board_status_{first.id}").set_value("面试").run()
    assert not app.exception
    assert JobService(db_path).get_job(first.id).applied_at == today
    assert JobService(db_path).get_job(second.id).status == "收藏"

    app.switch_page("views/overview.py").run()
    assert [(metric.label, metric.value) for metric in app.metric] == [
        ("岗位总数", "2"),
        ("累计投递数", "1"),
        ("当前面试数", "1"),
    ]
    assert len([button for button in app.button if button.key.startswith("due_upcoming_")]) == 2

    app.button(key=f"due_upcoming_0_{first.id}").click().run()
    assert not app.exception
    assert any("从总览定位到" in item.value for item in app.info)
    assert any(button.key == f"edit_{first.id}" for button in app.button)
    assert not any(button.key == f"edit_{second.id}" for button in app.button)

    # AppTest renders st.switch_page's result but keeps the old test page as its run target.
    app.switch_page("views/library.py").run()
    next(button for button in app.button if button.label == "显示全部岗位").click().run()
    assert not app.exception
    assert any(button.key == f"edit_{second.id}" for button in app.button)


def test_board_restores_old_status_when_database_is_busy(monkeypatch, tmp_path):
    db_path = tmp_path / "ui.db"
    monkeypatch.setenv("JOBPILOT_DB_PATH", str(db_path))
    job = JobService(db_path).create_job({"company": "星河科技", "job_title": "产品经理"})
    app = AppTest.from_file(APP_PATH, default_timeout=8).run()
    app.switch_page("views/board.py").run()

    with sqlite3.connect(db_path) as lock:
        lock.execute("BEGIN IMMEDIATE")
        app.selectbox(key=f"board_status_{job.id}").set_value("面试").run()
        assert not app.exception
        assert app.selectbox(key=f"board_status_{job.id}").value == "收藏"
        assert any("状态未更新" in item.value for item in app.error)

    assert JobService(db_path).get_job(job.id).status == "收藏"
