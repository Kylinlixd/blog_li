<div align="center">

# ☕ LiXD Studio · Kylin Blog API

个人博客的 Django REST API —— 内容管理、合集专栏、SEO 输出、访问风控，一站式后端。

[![Django](https://img.shields.io/badge/Django-5.1-44B78B?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.16-A30000)](https://www.django-rest-framework.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![CI](https://img.shields.io/badge/CI-Deploy%20on%20push-2088FF?logo=githubactions&logoColor=white)](.github/workflows/deploy.yml)
[![License](https://img.shields.io/badge/License-MIT-C86F37)](#license)

**线上 API**：[https://leexd.top/api/](https://leexd.top/api/)

</div>

---

## ✨ 主要能力

| 模块 | 能力 |
| --- | --- |
| 🔐 认证 | JWT access/refresh 与令牌黑名单；用户名 / 邮箱 / 昵称 + 密码登录 |
| 📝 内容 | 文章（动态）增删改查、分类、标签、评论审核与敏感内容过滤 |
| 📚 合集 | 按系列组织的有序阅读路径（专栏），由发布器按文章系列**自动维护** |
| 🔍 SEO | `/sitemap.xml`、`/feed.xml`、`/robots.txt` 三件套 |
| 🛡 风控 | 访问日志、设备识别、IP 安全规则 |
| 📊 仪表盘 | 管理端统计与定期日志清理 |
| 📎 附件 | 文件/图片上传、公开脱敏下载链接 |

> 💡 合集公开接口：`GET /api/blog/collections/` 与 `GET /api/blog/collections/{id}/`，
> 条目按章节序号排列，只收录已发布文章。

## 🚀 快速开始

```bash
git clone https://github.com/Kylinlixd/blog_li.git
cd blog_li
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填好数据库等配置
```

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver      # http://127.0.0.1:8000
```

> ⚠️ 公开注册默认关闭。生产环境请通过服务器初始化管理员，不要把密钥与数据库密码提交进 Git。

## 🧪 验证

```bash
python manage.py check
python manage.py test                          # 自动使用内存 SQLite，无需 MySQL
python manage.py check --deploy               # 生产配置体检
python manage.py makemigrations --check       # 确认迁移已提交
```

## 📂 项目结构

```text
apps/
├── user/        # 用户、JWT 与令牌黑名单
├── dynamic/     # 博客内容
├── category/    # 分类
├── tag/         # 标签
├── comment/     # 评论与审核
├── upload/      # 文件管理
├── dashboard/   # 管理统计
├── access_log/  # 访问日志与 IP 风控
└── collection/  # 合集（专栏），发布器按系列自动维护
blog/            # settings、URL、中间件、异常处理、SEO 视图
ops/             # 部署与回滚脚本（含数据库迁移步骤）
docs/            # 开发、API 与部署文档
media/           # 用户上传文件（不进入 Git）
```

## 🚢 部署

生产环境：`/opt/blog_li`，Gunicorn（`blog-li.service`）+ Nginx。

| 方式 | 命令 / 触发 | 流程 |
| --- | --- | --- |
| 手动 | `bash ops/deploy.sh blog-server` | 备份 → 同步 → check → migrate → 回归测试 → 重启 → 健康检查 |
| 回滚 | `ops/rollback.sh <备份包> blog-server` | 用部署时生成的代码备份包恢复 |
| **CI** | push 到 `main` 自动触发 | GitHub Actions 执行同一套流程（`deploy.yml`） |

> ⚠️ rsync 以仓库为准（含 `--delete`）：临时在服务器上热改的代码，
> 一定要先收编回仓库再推送，否则会被覆盖。

<details>
<summary><b>CI 所需仓库 Secrets</b></summary>

| Secret | 说明 |
| --- | --- |
| `SERVER_HOST` | 服务器地址 |
| `SERVER_USERNAME` | SSH 用户 |
| `SERVER_SSH_KEY` | 部署专用私钥（公钥放服务器 `authorized_keys`） |

</details>

## 🔗 配套系统

- 🖥 前端仓库：[Kylinlixd/myblog-admin](https://github.com/Kylinlixd/myblog-admin)
- 🤖 自动发布器（`/opt/blog_autopilot`，稿件在 myblog-admin 的 `output/articles/`）：
  按随机节奏发文、自动维护合集与配图、回填相关推荐为站内真实链接

## 📚 文档

| 文档 | 内容 |
| --- | --- |
| [开发指南](docs/development.md) | 本地开发约定 |
| [API 文档](docs/api.md) | 接口清单与契约 |
| [部署指南](docs/deployment.md) | 服务器与环境 |
| [交付记录](docs/DELIVERY_2026-07-27.md) | 历史交付说明 |

## License

MIT
