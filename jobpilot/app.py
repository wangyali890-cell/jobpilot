"""JobPilot 本地 Web 应用入口。"""

import streamlit as st


def run_app(*, demo: bool = False) -> None:
    st.set_page_config(
        page_title="JobPilot 演示" if demo else "JobPilot",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    with st.sidebar:
        st.markdown("## JobPilot")
        st.caption("岗位与投递进度管理")
        if demo:
            st.info("公开演示：岗位均为虚构。修改只在当前会话暂存，请勿输入真实求职信息。")

    page = st.navigation(
        [
            st.Page("views/library.py", title="岗位库", icon=":material/bookmarks:", default=True),
            st.Page("views/board.py", title="进度看板", icon=":material/view_kanban:"),
            st.Page("views/overview.py", title="求职总览", icon=":material/overview:"),
        ],
        position="sidebar",
    )
    page.run()


if __name__ == "__main__":
    run_app()
