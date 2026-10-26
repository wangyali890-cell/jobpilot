"""Streamlit Community Cloud 公开演示入口：每个会话独立临时数据库。"""

from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st

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
