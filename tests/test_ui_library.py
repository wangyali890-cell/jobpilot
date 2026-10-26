"""岗位库与真实 SQLite 存储连接后的页面回归检查。"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from jobpilot.domain.service import JobService


def test_library_renders_persisted_jobs_and_empty_search(monkeypatch, tmp_path):
    db_path = tmp_path / "ui.db"
    monkeypatch.setenv("JOBPILOT_DB_PATH", str(db_path))
    JobService(db_path).create_job(
        {"company": "星河科技", "job_title": "产品经理实习生", "city": "上海"}
    )

    app_path = Path(__file__).resolve().parents[1] / "jobpilot" / "app.py"
    app = AppTest.from_file(app_path).run()
    assert not app.exception
    assert any("产品经理实习生" in item.value for item in app.markdown)
    assert any(button.key == "edit_1" for button in app.button)

    app.text_input(key="library_query").set_value("不存在").run()
    assert not app.exception
    assert any("没有匹配的岗位" in item.value for item in app.info)
    assert not any(button.key == "edit_1" for button in app.button)

    next(button for button in app.button if button.label == "清除筛选").click().run()
    assert any(button.key == "delete_1" for button in app.button)
    app.button(key="delete_1").click().run()
    assert JobService(db_path).get_job(1).company == "星河科技"
    assert not app.exception
    assert any(button.key == "delete_confirm_1" for button in app.button)
