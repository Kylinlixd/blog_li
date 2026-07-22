# Kylin Blog API

个人博客的 Django REST API，提供 JWT 认证、内容/分类/标签/评论管理、公开博客读取、文件上传和仪表盘统计。

## 技术栈

- Python 3.10+
- Django 5.1 / Django REST Framework 3.16
- Simple JWT
- MySQL 8（测试自动使用内存 SQLite）
- Gunicorn + Nginx（生产）

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

## 验证

```bash
python manage.py check
python manage.py test
```

测试环境无需 MySQL；当命令参数包含 `test` 时自动使用内存 SQLite。

## 项目结构

```text
apps/
├── user/       # 用户、JWT 与令牌黑名单
├── dynamic/    # 博客内容
├── category/   # 分类
├── tag/        # 标签
├── comment/    # 评论与审核
├── upload/     # 文件管理
└── dashboard/  # 管理统计
blog/           # settings、URL、中间件、异常处理
docs/           # 开发、API 与部署文档
media/          # 用户上传文件（不进入 Git）
```

## 文档

- [开发指南](docs/development.md)
- [API 文档](docs/api.md)
- [部署指南](docs/deployment.md)

前端仓库：[Kylinlixd/myblog-admin](https://github.com/Kylinlixd/myblog-admin)

## License

MIT
