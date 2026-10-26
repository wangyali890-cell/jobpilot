"""公开演示与本机岗位数据隔离。"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from jobpilot.domain.service import JobService


DEMO_PATH = Path(__file__).resolve().parents[1] / "jobpilot" / "demo_app.py"


def test_demo_sessions_have_separate_fictional_databases(monkeypatch, tmp_path):
    personal_db = tmp_path / "personal.db"
    monkeypatch.setenv("JOBPILOT_DB_PATH", str(personal_db))

    first = AppTest.from_file(DEMO_PATH).run()
    second = AppTest.from_file(DEMO_PATH).run()
    assert not first.exception and not second.exception
    first_path = Path(first.session_state["jobpilot_demo_db_path"])
    second_path = Path(second.session_state["jobpilot_demo_db_path"])
    assert first_path != second_path
    assert not personal_db.exists()
    assert len(JobService(first_path).list_jobs()) == 4
    assert len(JobService(second_path).list_jobs()) == 4

    first.switch_page("views/board.py").run()
    first.selectbox(key="board_status_1").set_value("面试").run()
    assert JobService(first_path).get_job(1).status == "面试"
    assert JobService(second_path).get_job(1).status == "收藏"
