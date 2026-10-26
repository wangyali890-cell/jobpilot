"""为页面选择当前浏览器会话对应的岗位服务。"""

import streamlit as st

from jobpilot.domain.service import JobService


def current_service() -> JobService:
    demo_path = st.session_state.get("jobpilot_demo_db_path")
    return JobService(db_path=demo_path)
