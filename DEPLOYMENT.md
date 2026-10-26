# JobPilot 公开演示部署

## 两个入口

| 入口文件 | 用途 | 数据 |
| --- | --- | --- |
| `jobpilot/app.py` | 个人本机使用 | `data/jobpilot.db`，长期保存在本机 |
| `jobpilot/demo_app.py` | 公开作品集演示 | 每个浏览器会话独立的临时虚构数据，不作长期保存 |

公开演示不读取或复制个人数据库。访客在演示中输入的信息只供当前会话体验，可能因会话结束或云端重启而丢失，因此页面明确提示不要输入真实求职信息。真实使用继续运行本机入口。

## 本机核对公开演示

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run jobpilot/demo_app.py --server.address 127.0.0.1 --server.port 8502
```

打开 `http://127.0.0.1:8502`，确认侧边栏出现“公开演示”提示，岗位库已有四条带“（演示）”的虚构记录，并且三页可正常切换。

## Streamlit Community Cloud

1. 将项目代码推送到独立的 GitHub 仓库。推送前确认 `data/jobpilot.db`、`.venv` 和 `.streamlit/secrets.toml` 没有进入提交。`sites/` 下的作品集站点也不属于应用仓库。
2. 在 [Streamlit Community Cloud](https://share.streamlit.io/) 选择 **Create app → Yup, I have an app**。
3. 选择仓库与分支，**Main file path** 填 `jobpilot/demo_app.py`。
4. 在 **Advanced settings** 将 Python 版本设为 **3.11**，与项目开发环境一致。无需设置 secrets。
5. 部署后核对三页、虚构数据提示，以及不同浏览器会话互不影响。将最终 `streamlit.app` URL 加入作品集页面。

根目录的 `requirements.txt` 固定了 Streamlit 和时区数据版本。Community Cloud 会从 GitHub 读取仓库，并依据依赖文件构建应用；`jobpilot/demo_app.py` 是公开演示的唯一入口。部署过程与依赖规则参考 [官方部署指南](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)和[依赖说明](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)。

> Community Cloud 不保证运行时生成的本地文件跨会话保留；它适合这里的临时演示，不适合作为个人求职记录的长期存储。见 [Streamlit 官方说明](https://docs.streamlit.io/develop/concepts/configuration/serving-static-files)。
