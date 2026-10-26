"""岗位统计、未来七天和逾期日期事项。"""

from __future__ import annotations

import sqlite3

import streamlit as st

from jobpilot.domain.models import DueItem
from jobpilot.storage.db import UnsupportedSchemaVersion
from jobpilot.ui_context import current_service


def _read_error() -> None:
    st.error("总览读取失败，请重试。")
    if st.button("重试", key="overview_retry"):
        st.rerun()
    st.stop()


def _view_job(job_id: int) -> None:
    st.session_state["library_focus_job_id"] = job_id
    for key, value in (
        ("library_query", ""),
        ("library_status", "全部状态"),
        ("library_type", "全部类型"),
        ("library_city", "全部城市"),
    ):
        st.session_state[key] = value
    st.switch_page("views/library.py")


def _due_item(item: DueItem, *, section: str, index: int) -> None:
    with st.container(border=True):
        cols = st.columns([3, 1], gap="small", vertical_alignment="center")
        with cols[0]:
            st.markdown(f"**{item.company} · {item.job_title}**")
            st.caption(f"{item.due_date.isoformat()} · {item.kind}")
            if item.detail:
                st.write(item.detail)
            if section == "overdue":
                st.badge("已逾期", color="orange")
        with cols[1]:
            if st.button("查看", key=f"due_{section}_{index}_{item.job_id}", use_container_width=True):
                _view_job(item.job_id)


st.title("求职总览")
st.caption("查看累计投递与接下来要处理的事")

try:
    overview = current_service().get_overview()
except (sqlite3.Error, OSError, UnsupportedSchemaVersion):
    _read_error()

metrics = st.columns(3, gap="small")
with metrics[0]:
    st.metric("岗位总数", overview.total_jobs)
with metrics[1]:
    st.metric("累计投递数", overview.applied_jobs)
with metrics[2]:
    st.metric("当前面试数", overview.interviewing_jobs)

if overview.total_jobs == 0:
    st.info("还没有岗位，先到岗位库添加第一条记录。")
    st.page_link("views/library.py", label="前往岗位库", icon=":material/arrow_forward:")

sections = st.columns(2, gap="large")
with sections[0]:
    st.subheader(f"未来 7 天 · {len(overview.upcoming)}")
    if not overview.upcoming:
        st.info("暂无近期事项")
    for index, item in enumerate(overview.upcoming):
        _due_item(item, section="upcoming", index=index)
with sections[1]:
    st.subheader(f"逾期事项 · {len(overview.overdue)}")
    if not overview.overdue:
        st.info("暂无逾期事项")
    for index, item in enumerate(overview.overdue):
        _due_item(item, section="overdue", index=index)
