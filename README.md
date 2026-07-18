# 垚博企管官网 — 企业级售后交付平台

> 东莞市垚博企业管理咨询有限公司官方网站
> **线上地址：[https://ybqg.work](https://ybqg.work)**

一个从零独立开发并部署上线的全栈 Web 应用，服务于真实企业的日常业务：证书查询、在线考试、在线课程与权限管理。

---

## 功能特性

### 面向客户
- **证书查询** — 姓名 + 身份证号即可公开查询已颁发的资质证书
- **在线考试** — 10 种体系认证考试（内审员等），随机抽取 50 题、自动评分、成绩记录
- **在线课程** — 视频课程学习，章节导航、免费试看
- **用户系统** — 手机号注册登录，个人中心查看我的课程与考试记录

### 面向管理员
- **证书 OCR 上传** — 上传证书照片，Tesseract OCR 自动识别姓名/证书编号/日期等字段，确认后入库
- **用户权限管理** — 可视化勾选每个用户的课程/考试权限，即时生效

### 权限模型
```
未登录  → 仅浏览公开页面
已登录  → 可见课程/考试列表，无权限时弹出联系二维码
已授权  → 观看指定课程 / 参加指定考试
管理员  → 权限管理 + 证书上传
```
用户不能自助购买，全部权限由管理员手动授予——贴合公司"先线下签约、网站做交付"的业务模式。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3 + Flask 3.0 + Gunicorn |
| 数据库 | SQLite（9 张表，参数化查询） |
| 前端 | Jinja2 模板 + 原生 CSS（2200+ 行，CSS 变量 + 响应式）+ 原生 JS（无框架） |
| OCR | Tesseract + pytesseract + Pillow（中英文混合识别） |
| 部署 | Ubuntu VPS + Nginx 反向代理 + systemd + HTTPS (Let's Encrypt) |
| SEO | robots.txt / sitemap.xml / JSON-LD 结构化数据 / 百度主动推送 |

## 项目结构

```
company-website/
├── app.py                  # Flask 主应用（所有路由 + API）
├── database/               # 建表 / 种子数据 / 迁移脚本（均幂等）
├── templates/              # Jinja2 模板（20+ 页面）
├── static/
│   ├── css/style.css       # 全局样式
│   ├── js/main.js          # 全局脚本
│   └── images/             # 静态资源
├── utils/ocr.py            # 证书 OCR 识别模块
├── deploy.sh               # 服务器初始化脚本（Nginx + systemd + 依赖）
└── requirements.txt
```

## 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库（建表 + 示例数据）
python database/init_db.py
python database/init_courses.py
python database/seed_courses.py
python database/seed_exam_types.py

# 3. 启动
python app.py
# 访问 http://127.0.0.1:5000
```

> OCR 功能需额外安装 [Tesseract](https://github.com/tesseract-ocr/tesseract) 及中文语言包（`tesseract-ocr-chi-sim`）。

## 安全设计

- 密码使用 Werkzeug `generate_password_hash` 哈希存储，不存明文
- SQL 全部参数化查询，无字符串拼接
- 前端输出统一经过 `escapeHtml` / `escapeJs` 转义，防 XSS
- `SECRET_KEY` 通过环境变量注入
- 数据库文件、用户上传内容、部署凭据均不入库版本控制

## License

版权所有 © 东莞市垚博企业管理咨询有限公司。代码仅作展示用途。
