"""按投递阶段展示岗位，并通过统一服务更新状态。"""

from __future__ import annotations

import sqlite3

import streamlit as st

from jobpilot.domain.models import STATUSES, TERMINAL_STATUSES, Job
from jobpilot.domain.service import JobNotFound
from jobpilot.domain.validation import ValidationError
from jobpilot.storage.db import UnsupportedSchemaVersion
from jobpilot.ui_context import current_service


ACTIVE_STATUSES = tuple(status for status in STATUSES if status not in TERMINAL_STATUSES)
TERMINAL_ORDER = tuple(status for status in STATUSES if status in TERMINAL_STATUSES)


def _read_error(message: str) -> None:
    st.error(message)
    if st.button("重试", key="board_retry"):
        st.rerun()
    st.stop()


try:
    service = current_service()
except (sqlite3.Error, OSError, UnsupportedSchemaVersion):
    _read_error("进度看板读取失败，请检查本地数据库并重试。")


def _change_status(job_id: int, previous_status: str) -> None:
    key = f"board_status_{job_id}"
    selected = st.session_state[key]
    if selected == previous_status:
        return
    try:
        service.set_status(job_id, selected)
    except JobNotFound:
        st.session_state.pop(key, None)
        st.session_state["board_feedback"] = ("error", "该岗位已不存在，看板已刷新。")
    except ValidationError:
        st.session_state[key] = previous_status
        st.session_state["board_feedback"] = ("error", "请选择有效的投递状态")
    except (sqlite3.Error, OSError):
        st.session_state[key] = previous_status
        st.session_state["board_feedback"] = ("error", "状态未更新，请重试。")
    else:
        st.session_state["board_feedback"] = ("success", "投递状态已更新")


def _card(job: Job) -> None:
    with st.container(border=True):
        st.markdown(f"**{job.company}**")
        st.write(job.job_title)
        st.caption(f"{job.city or '城市未填'} · {job.job_type}")
        if job.deadline:
            st.caption(f"截止：{job.deadline.isoformat()}")
        st.selectbox(
            "投递状态",
            STATUSES,
            index=STATUSES.index(job.status),
            key=f"board_status_{job.id}",
            on_change=_change_status,
            args=(job.id, job.status),
        )


st.title("进度看板")
st.caption("按阶段查看岗位，直接修改状态")

feedback = st.session_state.pop("board_feedback", None)
if feedback:
    kind, message = feedback
    if kind == "success":
        st.success(message)
    else:
        st.error(message)

try:
    jobs = service.list_jobs()
except (sqlite3.Error, OSError):
    _read_error("进度看板读取失败，请重试。")

if not jobs:
    st.info("还没有可展示的岗位，请先到岗位库添加。")
    st.page_link("views/library.py", label="前往岗位库", icon=":material/arrow_forward:")
else:
    grouped = {status: [job for job in jobs if job.status == status] for status in STATUSES}
    columns = st.columns(len(ACTIVE_STATUSES), gap="small")
    for column, status in zip(columns, ACTIVE_STATUSES):
        with column:
            st.markdown(f"**{status}**")
            st.caption(f"{len(grouped[status])} 条岗位")
            if not grouped[status]:
                st.caption("暂无岗位")
            for job in grouped[status]:
                _card(job)

    terminal_count = sum(len(grouped[status]) for status in TERMINAL_ORDER)
    with st.expander(f"终止状态 · {terminal_count}"):
        if not terminal_count:
            st.caption("暂无岗位")
        for status in TERMINAL_ORDER:
            if grouped[status]:
                st.subheader(f"{status} · {len(grouped[status])}")
                for job in grouped[status]:
                    _card(job)
