"""岗位库：录入、编辑、删除和检索岗位。"""

from __future__ import annotations

import sqlite3

import streamlit as st

from jobpilot.domain.models import JOB_TYPES, STATUSES, Job, JobFilters
from jobpilot.domain.service import DuplicateJobLink, JobNotFound
from jobpilot.domain.validation import ValidationError
from jobpilot.storage.db import UnsupportedSchemaVersion
from jobpilot.ui_context import current_service


STATUS_COLORS = {
    "收藏": "gray",
    "准备投递": "orange",
    "已投递": "blue",
    "测评/笔试": "green",
    "面试": "violet",
    "Offer": "green",
    "已拒绝": "gray",
    "已结束": "gray",
    "已放弃": "gray",
}

FORM_FIELDS = (
    "company",
    "job_title",
    "job_type",
    "city",
    "job_url",
    "status",
    "applied_at",
    "deadline",
    "next_action",
    "next_action_date",
    "notes",
)


def _retryable_error(message: str) -> None:
    st.error(message)
    if st.button("重试", key="library_retry"):
        st.rerun()
    st.stop()


try:
    service = current_service()
except (sqlite3.Error, OSError, UnsupportedSchemaVersion):
    _retryable_error("无法读取本地数据库，请检查文件权限或重试。")


def _clear_form_state(prefix: str) -> None:
    for name in FORM_FIELDS:
        st.session_state.pop(f"{prefix}_{name}", None)


def _clear_filters() -> None:
    st.session_state["library_query"] = ""
    st.session_state["library_status"] = "全部状态"
    st.session_state["library_type"] = "全部类型"
    st.session_state["library_city"] = "全部城市"


def _form(job_id: int | None) -> None:
    try:
        existing = service.get_job(job_id) if job_id is not None else None
    except JobNotFound:
        st.error("该岗位已不存在，列表已刷新。")
        return
    except (sqlite3.Error, OSError):
        st.error("岗位读取失败，请关闭后重试。")
        return

    prefix = f"job_{job_id}" if existing else "job_new"
    slots: dict[str, object] = {}
    with st.form(f"{prefix}_form", clear_on_submit=False):
        st.markdown("**基础信息**")
        company = st.text_input(
            "公司名称 *", value=existing.company if existing else "", max_chars=100,
            key=f"{prefix}_company",
        )
        slots["company"] = st.empty()
        title = st.text_input(
            "岗位名称 *", value=existing.job_title if existing else "", max_chars=100,
            key=f"{prefix}_job_title",
        )
        slots["job_title"] = st.empty()
        base_cols = st.columns(2)
        with base_cols[0]:
            job_type = st.selectbox(
                "招聘类型", JOB_TYPES,
                index=JOB_TYPES.index(existing.job_type) if existing else 0,
                key=f"{prefix}_job_type",
            )
            slots["job_type"] = st.empty()
        with base_cols[1]:
            city = st.text_input(
                "城市", value=existing.city or "" if existing else "", max_chars=60,
                key=f"{prefix}_city",
            )
            slots["city"] = st.empty()
        url = st.text_input(
            "招聘链接", value=existing.job_url or "" if existing else "",
            max_chars=2048, placeholder="https://", key=f"{prefix}_job_url",
        )
        slots["job_url"] = st.empty()

        with st.expander("进度、日期与备注（可选）", expanded=existing is not None):
            status = st.selectbox(
                "投递状态", STATUSES,
                index=STATUSES.index(existing.status) if existing else 0,
                key=f"{prefix}_status",
            )
            slots["status"] = st.empty()
            date_cols = st.columns(2)
            with date_cols[0]:
                applied_at = st.date_input(
                    "首次投递日期", value=existing.applied_at if existing else None,
                    max_value=service.today_provider(), format="YYYY-MM-DD",
                    key=f"{prefix}_applied_at",
                )
                slots["applied_at"] = st.empty()
            with date_cols[1]:
                deadline = st.date_input(
                    "招聘截止日期", value=existing.deadline if existing else None,
                    format="YYYY-MM-DD", key=f"{prefix}_deadline",
                )
                slots["deadline"] = st.empty()
            st.caption("进入已投递、测评/笔试、面试或 Offer 时，首次投递日期留空将自动填今天。")
            next_action = st.text_input(
                "下一步任务", value=existing.next_action or "" if existing else "",
                max_chars=200, key=f"{prefix}_next_action",
            )
            slots["next_action"] = st.empty()
            next_action_date = st.date_input(
                "下一步任务日期", value=existing.next_action_date if existing else None,
                format="YYYY-MM-DD", key=f"{prefix}_next_action_date",
            )
            slots["next_action_date"] = st.empty()
            notes = st.text_area(
                "备注", value=existing.notes or "" if existing else "",
                max_chars=2000, key=f"{prefix}_notes",
            )
            slots["notes"] = st.empty()

        submitted = st.form_submit_button("保存岗位", type="primary", use_container_width=True)

    if st.button("取消", key=f"{prefix}_cancel", use_container_width=True):
        st.rerun()

    if not submitted:
        return

    payload = {
        "company": company,
        "job_title": title,
        "job_type": job_type,
        "city": city,
        "job_url": url,
        "status": status,
        "applied_at": applied_at,
        "deadline": deadline,
        "next_action": next_action,
        "next_action_date": next_action_date,
        "notes": notes,
    }
    try:
        if existing:
            service.update_job(existing.id, payload)
        else:
            service.create_job(payload)
    except ValidationError as error:
        for field, message in error.errors.items():
            if field in slots:
                slots[field].error(message)
            else:
                st.error(message)
    except DuplicateJobLink as error:
        slots["job_url"].error("该链接已保存，请编辑现有岗位。")
        if error.existing_job:
            st.info(f"现有岗位：{error.existing_job.company} · {error.existing_job.job_title}")
    except JobNotFound:
        st.error("该岗位已不存在，列表已刷新。")
    except (sqlite3.Error, OSError):
        st.error("操作未完成，记录未改变。请重试；输入内容已保留。")
    else:
        st.session_state["library_notice"] = "岗位已保存"
        st.rerun()


@st.dialog("添加岗位", position="right")
def add_job_dialog() -> None:
    _form(None)


@st.dialog("编辑岗位", position="right")
def edit_job_dialog(job_id: int) -> None:
    _form(job_id)


@st.dialog("删除岗位？")
def delete_job_dialog(job_id: int) -> None:
    try:
        job = service.get_job(job_id)
    except JobNotFound:
        st.error("该岗位已不存在，列表已刷新。")
        return
    except (sqlite3.Error, OSError):
        st.error("岗位读取失败，请关闭后重试。")
        return
    st.warning(f"将永久删除“{job.company} · {job.job_title}”。此操作无法撤销。")
    actions = st.columns(2)
    with actions[0]:
        if st.button("取消", key=f"delete_cancel_{job_id}", use_container_width=True):
            st.rerun()
    with actions[1]:
        if st.button("确认删除", key=f"delete_confirm_{job_id}", use_container_width=True):
            try:
                service.delete_job(job_id)
            except JobNotFound:
                st.error("该岗位已不存在，列表已刷新。")
            except (sqlite3.Error, OSError):
                st.error("岗位未删除，请重试。")
            else:
                st.session_state["library_notice"] = "岗位已删除"
                st.rerun()


def _job_row(job: Job, today) -> None:
    with st.container(border=True):
        st.markdown(f"**{job.job_title}**")
        st.caption(f"{job.company} · {job.city or '城市未填'} · {job.job_type}")
        st.badge(job.status, color=STATUS_COLORS[job.status])
        if job.deadline:
            st.caption(f"截止日期：{job.deadline.isoformat()}")
            if job.deadline < today and job.status not in (
                "Offer", "已拒绝", "已结束", "已放弃"
            ):
                st.badge("已逾期", color="orange")
        if job.next_action:
            due = f" · {job.next_action_date.isoformat()}" if job.next_action_date else ""
            st.caption(f"下一步：{job.next_action}{due}")
        actions = st.columns(3, gap="small")
        with actions[0]:
            if job.job_url:
                st.link_button("原链接", job.job_url, use_container_width=True)
        with actions[1]:
            if st.button("编辑", key=f"edit_{job.id}", use_container_width=True):
                _clear_form_state(f"job_{job.id}")
                edit_job_dialog(job.id)
        with actions[2]:
            if st.button("删除", key=f"delete_{job.id}", use_container_width=True):
                delete_job_dialog(job.id)


st.title("岗位库")
st.caption("把浏览器收藏变成可追踪的岗位记录")

notice = st.session_state.pop("library_notice", None)
if notice:
    st.success(notice)

if st.button("添加岗位", type="primary", key="add_job"):
    _clear_form_state("job_new")
    add_job_dialog()

try:
    all_jobs = service.list_jobs()
except (sqlite3.Error, OSError):
    _retryable_error("岗位读取失败，请重试。")

focus_id = st.session_state.get("library_focus_job_id")
focus_job = next((job for job in all_jobs if job.id == focus_id), None)
if focus_id is not None and focus_job is None:
    st.session_state.pop("library_focus_job_id", None)
    st.warning("该岗位已不存在，已返回完整岗位库。")

if focus_job:
    st.info(f"从总览定位到：{focus_job.company} · {focus_job.job_title}")
    if st.button("显示全部岗位"):
        st.session_state.pop("library_focus_job_id", None)
        st.rerun()
    visible = [focus_job]
else:
    cities = sorted({job.city for job in all_jobs if job.city})
    query = st.text_input("搜索公司、岗位或城市", key="library_query", placeholder="搜索公司、岗位或城市")
    filter_cols = st.columns(4, gap="small")
    with filter_cols[0]:
        selected_status = st.selectbox("投递状态", ("全部状态", *STATUSES), key="library_status")
    with filter_cols[1]:
        selected_type = st.selectbox("招聘类型", ("全部类型", *JOB_TYPES), key="library_type")
    with filter_cols[2]:
        selected_city = st.selectbox("城市", ("全部城市", *cities), key="library_city")
    with filter_cols[3]:
        st.write("")
        st.button("清除筛选", use_container_width=True, on_click=_clear_filters)

    filters = JobFilters(
        query=query,
        status=None if selected_status == "全部状态" else selected_status,
        job_type=None if selected_type == "全部类型" else selected_type,
        city=None if selected_city == "全部城市" else selected_city,
    )
    try:
        visible = service.list_jobs(filters)
    except (sqlite3.Error, OSError):
        _retryable_error("岗位读取失败，请重试。")

st.caption(f"显示 {len(visible)} / {len(all_jobs)} 条岗位 · 按最近修改排序")
if not all_jobs:
    st.info("还没有岗位，点击“添加岗位”开始记录。")
elif not visible:
    st.info("没有匹配的岗位，试试清除筛选。")
else:
    for item in visible:
        _job_row(item, service.today_provider())
