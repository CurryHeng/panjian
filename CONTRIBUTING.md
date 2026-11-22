# 贡献文档

感谢参与盘见开发。盘见是一个本机运行的飞盘视频自动剪辑工作台，当前重点是验证上传、自动选段、人工调整和视频导出流程。

## 开发环境

- Windows 10/11
- Python 3.11 或更高版本
- Node.js，用于检查前端 JavaScript
- Git

在项目目录创建环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

启动本地服务：

```powershell
.\启动盘见.cmd
```

浏览器访问 `http://127.0.0.1:8765/`。服务只绑定本机地址，不要把它直接暴露到公网。

## 目录说明

- `app/main.py`：FastAPI 接口、项目保存、后台任务和文件下载
- `app/highlights.py`：人物检测、运动量评分和自动片段计划
- `app/backtrack.py`：起点回看、短间隔保留和片段合并
- `app/media.py`：视频探测、FFmpeg 编码和片段拼接
- `app/static/`：工作台页面、样式和浏览器交互
- `app/models/`：NanoDet 模型及许可文件
- `tests/`：后端和剪辑计划测试
- `docs/`：设计与验证文档
- `data/`：本地运行数据，不提交到 Git

## 修改流程

1. 从当前 `main` 分支开始修改。
2. 先阅读相关模块和测试，保持 API 数据结构兼容。
3. 功能修改完成后运行测试和语法检查。
4. 使用真实短视频或合成素材验证正常路径和失败路径。
5. 提交信息说明实际修改内容。

```powershell
python -m pytest -q --basetemp .pytest-temp-local
node --check app/static/app.js
git status
git add app docs tests README.md TODO.md requirements.txt requirements-dev.txt start.ps1 启动盘见.cmd
git commit -m "说明本次修改"
git push
```

## 视频和数据规则

不要提交原始视频、导出视频、`data/`、运行日志、测试缓存、浏览器登录信息或带鉴权参数的地址。视频素材应放在本地或已授权的数据源中。提交前用 `git status` 检查变更范围。

## 代码约定

后端使用清晰的中文用户错误信息和小范围函数。输入数据需要经过项目 ID、文件类型、文件大小、片段范围和字段长度校验。前端修改要保留现有元素 ID 和 API 路径，避免破坏上传、项目恢复、保存、导出和下载流程。

## 提交问题

报告问题时请提供复现步骤、操作系统、Python 版本、浏览器、素材容器和视频编码。说明问题发生在原片预览、自动计划、片段编辑还是导出阶段。不要上传未经授权的视频或隐私信息。

## 当前能力边界

自动推荐依据人物检测和画面运动量，不能确认每次传盘、接盘、得分、盘权或战术。起止点和片段价值仍允许用户人工调整。项目面向本机单用户使用，尚未提供多人账户、空间配额、断点续传和任务取消。
