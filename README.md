# LiXD Studio · Kylin Blog API

个人博客的 Django REST API，提供 JWT 认证、内容/分类/标签/评论管理、合集（专栏）、公开博客读取、SEO 输出、文件上传、访问日志和仪表盘统计。

线上 API：`https://leexd.top/api/`

## 技术栈

- Python 3.10+
- Django 5.1 / Django REST Framework 3.16
- Simple JWT
- MySQL 8（连接字符集 utf8mb4，测试自动使用内存 SQLite）
- Gunicorn + Nginx（生产）

## 主要能力

- JWT access/refresh 会话与令牌黑名单
- 用户资料、用户名和密码修改
- 登录支持当前用户名、邮箱或昵称（配合原密码）
- 内容分类、标签、评论审核和访问设备记录
- **合集（专栏）**：按系列组织的有序阅读路径，公开接口
  `GET /api/blog/collections/`、`GET /api/blog/collections/{id}/`，
  数据由发布器按文章系列自动维护
- **SEO 三件套**：`/sitemap.xml`、`/feed.xml`、`/robots.txt`
- 评论敏感内容过滤与自动审核策略
- 管理端统计、访问日志和定期日志清理

## 快速开始

```bash
git clone https://github.com/Kylinlixd/blog_li.git
cd blog_li
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

创建 MySQL 数据库并修改 `.env` 后：

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

服务默认运行在 `http://127.0.0.1:8000`。

公开注册默认关闭。生产环境请通过服务器初始化管理员或受保护的管理接口创建账号，不要把生产密钥、数据库密码提交到 Git。

## 验证

```bash
python manage.py check
python manage.py test
```

提交前建议执行完整检查：

```bash
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test
```

测试环境无需 MySQL；当命令参数包含 `test` 时自动使用内存 SQLite。

## 项目结构

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
└── collection/  # 合集（专栏），发布器按文章系列自动维护
blog/            # settings、URL、中间件、异常处理、SEO 视图
ops/             # 部署与回滚脚本（含数据库迁移步骤）
docs/            # 开发、API 与部署文档
media/           # 用户上传文件（不进入 Git）
```

## 部署

生产服务器：`/opt/blog_li`（Gunicorn `blog-li.service` + Nginx）。

```bash
# 手动部署：备份 → 同步 → check → migrate → 回归测试 → 重启 → 健康检查
bash ops/deploy.sh blog-server

# 回滚
ops/rollback.sh <备份包路径> blog-server
```

**CI 自动部署**：push 到 `main` 触发 GitHub Actions（`.github/workflows/deploy.yml`），
自动执行与上面相同的流程。所需仓库 Secrets：`SERVER_HOST`、`SERVER_USERNAME`、`SERVER_SSH_KEY`。

注意：rsync 以仓库为准（含 `--delete`），临时在服务器上热改的代码要先收编回仓库再推送，否则会被覆盖。

## 配套系统

- 前端仓库：[Kylinlixd/myblog-admin](https://github.com/Kylinlixd/myblog-admin)
- 自动发布器（`/opt/blog_autopilot`，稿件仓库在 myblog-admin 的 `output/articles/`）：
  按随机节奏发布文章、自动维护合集与配图，并把相关推荐回填为站内真实链接

## 文档

- [开发指南](docs/development.md)
- [API 文档](docs/api.md)
- [部署指南](docs/deployment.md)
- [交付记录](docs/DELIVERY_2026-07-27.md)

## License

MIT
