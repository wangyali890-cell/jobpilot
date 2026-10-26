"""Streamlit Community Cloud 公开演示入口：每个会话独立临时数据库。"""

from pathlib import Path
from tempfile import TemporaryDirectory
import sys

import streamlit as st

# Community Cloud launches this file from the package directory without
# installing the local project as a package. Add the repository root so the
# absolute ``jobpilot`` imports below resolve in that environment.
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from jobpilot.app import run_app
from jobpilot.demo_data import seed_demo
from jobpilot.domain.service import JobService


if "jobpilot_demo_db_path" not in st.session_state:
    demo_dir = TemporaryDirectory(prefix="jobpilot-demo-")
    demo_db_path = Path(demo_dir.name) / "jobs.db"
    seed_demo(JobService(demo_db_path))
    st.session_state["jobpilot_demo_directory"] = demo_dir
    st.session_state["jobpilot_demo_db_path"] = str(demo_db_path)

run_app(demo=True)
