# UI 改版交接文档

日期：2026-11-23　分支：`main`（未提交，改动都在工作区）

## 目标
把前端从"木纹手作风"改成"运动品牌海报风"：黑白灰为底，荧光黄绿 `#c8f23a` 只做点缀，大字排版，新增时间轴。为后续"运动视频集锦 AI 剪辑软件"定位铺路。

## 已完成
- `app/static/index.html`：整体改为顶栏 + 首屏大字块 + 预览/集锦双栏；新增时间轴容器 `#timeline` / `#tl-track` / `#tl-head`。所有原有元素 id 保留。
- `app/static/style.css`：改为入口，`@import` 下列模块。
- `app/static/css/`：`base`（变量/按钮/表单）、`layout`（顶栏/栅格）、`hero`（首屏与上传区）、`components`（预览/片段/导出）、`timeline`、`responsive`。
- `app/static/app.js`：新增 `renderTimeline()`、`movePlayhead()`、时间轴点击跳转；`render()`、片段输入、`timeupdate` 里挂了调用。业务逻辑未改。
- `app/static/img/`：`speedlines.svg`（速度线装饰）、`frisbee-lin.jpg`（Unsplash 免费授权，Jeffrey F Lin，页脚已署名）。
- `.claude/launch.json`：配置了一个静态预览服务（端口 8766，只预览前端）。

## 验证情况
- 只用静态服务器看过首屏（深色、大字、荧光色块、黑白题图上传区）渲染正常。
- **未验证**：真实视频加载、时间轴色块与播放头、片段列表样式、导出区。原因是本机没装 `fastapi`，后端起不来。
- 预览时控制台的两个 404 是静态服务器没有 `/api/*` 导致的，不是页面缺陷。

## 待办 / 已知问题
1. 装依赖（`pip install -r requirements.txt`）后用 `start.ps1` 起完整服务，上传一段视频，检查片段卡片、时间轴、导出区。
2. 视频空状态里的速度线偏块状，可再调淡或换成更细的线。
3. 窄屏下顶栏做了简化，需在真机或 650px 以下再看一遍。
4. 片段卡片按钮还比较密，可考虑把"预览后两秒/延长两秒/合并"收进更多菜单。
5. 字体用系统栈（Impact 做展示字），没有引入外部字体。想要更像参考图的窄粗体，可本地放字体文件再 `@font-face`。
6. 题图是彩色秋景照片转黑白，效果一般。有授权的黑白运动照片可直接替换 `img/frisbee-lin.jpg`（同名即可），并改页脚署名。
7. 时间轴目前只能点击跳转，后续可做拖动入点/出点、AI 精彩度标签。
8. 旧的 `README.md` / 文档若有截图或配色描述，需同步。

## 回滚
`git checkout -- app/static` 并删除 `app/static/css`、`app/static/img` 即可恢复原样。
