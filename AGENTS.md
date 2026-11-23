# 盘见 PANJIAN — 协作说明

运动视频集锦 AI 剪辑工具。当前只有本机运行的单页工作台。
本文件是本仓库所有编码助手（Codex / Claude / Cursor 等）的入口，**改界面前必须先读完
[docs/ui-design.md](docs/ui-design.md)**。

## 运行

```bash
pip install -r requirements.txt
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765
```

只看界面、不跑后端：`python -m http.server 8766 --bind 127.0.0.1 --directory app`
，访问 http://127.0.0.1:8766/static/index.html 。

## 目录

- `app/main.py` FastAPI 路由；`app/media.py` ffmpeg 探测与导出；`app/highlights.py` AI 选段
- `app/static/index.html` 唯一页面；`app/static/app.js` 前端逻辑（原生 JS，无构建）
- `app/static/style.css` 只是入口，真实样式在 `app/static/css/` 下按模块拆分
- `docs/ui-design.md` **视觉规范，改动前必读**

## 界面规则（硬约束，不是建议）

1. 只用 `app/static/css/base.css` 里的 CSS 变量取色，禁止写死新颜色。
2. 强调色只有 `--lime` 一个，整页占比不超过 10%，只用于：主按钮、选中态、播放头、大号序号。
3. `border-radius` 只能是 0 或 2px。禁止胶囊按钮、禁止圆角卡片。
4. 禁止装饰性 `box-shadow`、禁止渐变按钮、禁止玻璃拟态、禁止 emoji 当图标。
5. 禁止"卡片套卡片"。同级模块不能用同一种容器样式区分，用留白和 1px 分割线。
6. 正文字号 ≥ 12px。展示字用 `var(--display)`，正文用 `var(--body)`。
7. 不确定时**扩展已有结构**（`section-heading`、`.button`、`.clip`），不要新造一个平行组件。
8. 不引入构建工具、CSS 框架、UI 组件库、外部字体 CDN。

## 判断是否"AI 味"的三条

- 每个模块长得一样 → 没层级。
- 强调色满地都是 → 没有焦点。
- 圆角 + 阴影 + 渐变同时出现 → 模板感。

## 改完必须自检

1. 起服务，1440px 宽截图看过，不只看代码。
2. 对照 `docs/ui-design.md` 的检查清单逐条打勾。
3. 改动涉及交互时，用真实视频走一遍：上传 → 标记片段 → 时间轴 → 导出。
4. 在提交信息里写清改了哪几个 CSS 模块。

## 不要做的事

- 不要重写整个前端（不迁移 Vue/React，除非用户明确要求）。
- 不要改 `app.js` 里的业务逻辑和元素 id；只加，不删。
- 不要用图库照片换掉现有题图以外的位置，新增图片必须写明授权和作者。
