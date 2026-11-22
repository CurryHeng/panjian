# 贡献指南

感谢参与盘见开发。盘见是一个本机运行的飞盘视频自动剪辑工作台，当前重点是验证视频上传、自动选段、人工调整和视频导出流程。

本指南适用于两种贡献方式：直接拥有主仓库写入权限的协作者，以及通过 Fork 提交 Pull Request 的外部贡献者。所有改动都应先进入独立分支，再通过 Pull Request 合并到 `main`。

## 贡献边界

- `main` 只保留已经检查过、可以作为稳定版本的代码。
- 每个功能、界面改动、问题修复和文档更新都使用独立分支。
- 原始视频、导出视频、运行数据和测试缓存只用于本地验证，不提交到仓库。
- `data/`、`runtime-logs/`、`.pytest-*`、视频文件和本地环境文件已经列入 `.gitignore`，提交前仍需用 `git status` 检查。
- 不要提交浏览器登录状态、访问令牌、带鉴权参数的地址或未经授权的视频。

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

## 选择贡献方式

### 已有主仓库写入权限

当前项目主仓库地址为：

```text
https://github.com/CurryHeng/panjian.git
```

如果你是仓库协作者并拥有写入权限，可以克隆主仓库：

```powershell
git clone https://github.com/CurryHeng/panjian.git
cd panjian
```

此时 `origin` 指向主仓库。仍然不要直接在 `main` 上开发，应先同步并创建功能分支。

### 没有主仓库写入权限时使用 Fork

在 GitHub 打开主仓库，点击 **Fork**，创建自己的副本，然后克隆自己的 Fork：

```powershell
git clone https://github.com/<你的用户名>/panjian.git
cd panjian
git remote add upstream https://github.com/CurryHeng/panjian.git
git remote -v
```

Fork 模式下：

- `origin` 指向你的个人 Fork，你可以向它推送分支。
- `upstream` 指向盘见主仓库，用来获取最新的 `main`。
- 贡献分支推送到 `origin`。
- Pull Request 的目标仓库选择 `CurryHeng/panjian`，目标分支选择 `main`。
- Fork 贡献者不能直接推送主仓库的 `main`，也不能仅凭提交 PR 获得主仓库写入权限。
- PR 是否合并由主仓库维护者或拥有合并权限的协作者决定。

如果 GitHub CLI 已登录，也可以使用：

```powershell
gh repo fork CurryHeng/panjian --clone
cd panjian
git remote add upstream https://github.com/CurryHeng/panjian.git
```

## 创建贡献分支

开始新功能或修复前，先同步最新的 `main`。已有主仓库写入权限时执行：

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/功能名称
```

使用 Fork 时执行：

```powershell
git fetch upstream
git switch main
git merge --ff-only upstream/main
git push origin main
git switch -c feature/功能名称
```

如果 `--ff-only` 失败，不要强制覆盖个人 Fork 的 `main`。先保存当前工作，再处理分支差异。

分支名称使用小写英文、数字和连字符，例如：

- `feature/download-location`：新增功能
- `feature/ui-polish`：界面改造
- `fix/hevc-preview`：问题修复
- `docs/editing-logic`：文档修改

## 修改和本地验证

1. 先阅读相关模块、文档和测试，保持已有 API 路径和数据结构兼容。
2. 只在当前贡献分支修改文件。
3. 使用真实短视频或合成素材验证正常路径和失败路径。
4. 不要把本地视频、项目数据和导出结果加入提交。
5. 提交前确认改动范围和差异内容。

运行检查：

```powershell
python -m pytest -q --basetemp .pytest-temp-local
node --check app/static/app.js
git diff --check
git status
```

如果只修改文档，只暂存计划内的文档文件。例如：

```powershell
git add CONTRIBUTING.md "剪辑逻辑.md" TODO.md
```

不要使用不加筛选的 `git add .`，除非已经确认工作区没有本地素材、缓存或临时文件。

## 提交分支和创建 Pull Request

有主仓库写入权限时：

```powershell
git add <本次需要提交的文件>
git commit -m "说明本次修改内容"
git push -u origin <分支名>
```

使用 Fork 时：

```powershell
git add <本次需要提交的文件>
git commit -m "说明本次修改内容"
git push -u origin <分支名>
```

推送后，在 GitHub 创建 Pull Request：

- **base repository** 选择 `CurryHeng/panjian`。
- **base branch** 选择 `main`。
- **head repository** 选择你的 Fork。
- **compare branch** 选择本次贡献分支。

PR 描述应说明：

- 修改了哪些文件和功能。
- 如何验证，使用了哪些测试命令。
- 是否涉及视频编码、导出、浏览器兼容或本地数据。
- 是否需要维护者特别检查某个边界情况。

当前仓库要求通过 Pull Request 进入 `main`。审批数暂设为 `0`，所以维护者检查通过后可以直接合并。若以后恢复审批要求，需要有其他具备相应权限的协作者审核，PR 作者不能用自己的审核满足要求。

Fork 贡献者可以继续修改自己的 PR，向同一个分支推送新提交，PR 会自动更新。Fork 贡献者不能因为创建了 PR 就直接合并到主仓库，合并仍由维护者或具有合并权限的协作者完成。

## Pull Request 合并和分支清理

维护者检查代码、测试和文件范围后，再合并 PR。合并完成后删除已经完成的贡献分支：

```powershell
git switch main
git pull --ff-only origin main
git branch -d <分支名>
```

个人 Fork 中的分支可以由贡献者自行删除。主仓库受保护分支的删除权限由仓库规则决定，启用限制删除时，只有管理员或规则绕过名单中的成员可以删除。

如果 PR 尚未合并但发现文档或代码有误，继续在原贡献分支修正并推送，PR 会自动更新。如果 PR 已经合并，则从最新 `main` 新建一个修复分支并创建新的 PR。

## 视频和数据规则

不要提交以下内容：

- 原始视频、导出视频和批量下载的网盘素材。
- `data/`、`runtime-logs/`、测试缓存和浏览器缓存。
- `.env`、登录状态、访问令牌和带鉴权参数的链接。
- 未经授权或含有个人隐私的视频和截图。

视频素材应放在本地或已授权的数据源中。提交前用 `git status` 和 `git diff --cached --stat` 检查暂存范围。

## 代码约定

- 后端使用清晰的中文用户错误信息和小范围函数。
- 输入数据需要经过项目 ID、文件类型、文件大小、片段范围和字段长度校验。
- 前端修改要保留现有元素 ID 和 API 路径，避免破坏上传、项目恢复、保存、导出和下载流程。
- 修改剪辑逻辑时同步更新相关测试和 `剪辑逻辑.md`，并在 `TODO.md` 记录完成情况。

## 提交问题

报告问题时请提供复现步骤、操作系统、Python 版本、浏览器、素材容器和视频编码。说明问题发生在原片预览、自动计划、片段编辑还是导出阶段。不要上传未经授权的视频或隐私信息。

## 当前能力边界

自动推荐依据人物检测和画面运动量，不能确认每次传盘、接盘、得分、盘权或战术。起止点和片段价值仍允许用户人工调整。项目面向本机单用户使用，尚未提供多人账户、空间配额、断点续传和任务取消。
