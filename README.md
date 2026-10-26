# JobPilot

个人校招岗位与投递进度管理工具。产品范围见 [PRD](./JobPilot_PRD_V1.0.md)，页面交互见[彩色原型](./prototype/index.html)，实现取舍见[技术方案](./JobPilot_技术方案_V1.0.md)。

## 当前进度

- 已完成：项目虚拟环境、依赖配置、SQLite 数据层、岗位字段校验，以及三页可持久化的 Streamlit 应用。岗位库支持新增、编辑、删除、搜索和筛选；进度看板支持更新状态；求职总览显示统计和日期事项。
- 从总览事项点击“查看”会定位到对应岗位，再点击“显示全部岗位”返回完整列表。
- 彩色原型是独立 HTML 演示，刷新后恢复虚构示例数据；日常录入请使用 Streamlit 应用。

## 环境与测试

在 Windows PowerShell 中，从项目目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run jobpilot/app.py --server.address 127.0.0.1
```

应用默认把个人岗位存到 `data/jobpilot.db`。浏览器打开终端输出的本地地址即可使用。需要隔离测试数据时，可以先设置 `JOBPILOT_DB_PATH` 环境变量，将数据库指向另一条本地路径。

公开作品集演示使用独立入口 `jobpilot/demo_app.py` 和虚构临时数据；部署步骤及其与本机数据的边界见 [DEPLOYMENT.md](./DEPLOYMENT.md)。

数据层使用 `JobService`：

```python
from jobpilot.domain.service import JobService

service = JobService()  # 默认使用 data/jobpilot.db
job = service.create_job({"company": "示例公司", "job_title": "产品经理"})
print(job.id, service.get_overview().total_jobs)
```

真实岗位、备注和本地数据库文件不要提交到 Git。测试使用临时 SQLite 数据库与虚构岗位。

本工作区的 `.git` 目录由 Codex 沙箱账号创建。当前 Windows 用户直接运行 Git 可能收到“dubious ownership”提示；项目文件和测试不受影响。未修改用户的全局 Git 信任配置。
