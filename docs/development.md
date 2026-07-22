# 后端开发指南

## 1. 环境

- Python 3.10+
- MySQL 8+
- 推荐使用独立虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

最小开发配置：

```dotenv
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=local-development-secret
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DB_NAME=blog_db
DB_USER=blog_user
DB_PASSWORD=change-me
DB_HOST=127.0.0.1
DB_PORT=3306
```

## 2. 数据库与启动

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

不要在正常开发流程中执行 `makemigrations` 后直接忽略生成文件。每次模型变更都应检查迁移依赖，并在空数据库上执行完整 `migrate`。

## 3. 配置项

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DJANGO_DEBUG` | `True` | 生产必须为 `False` |
| `DJANGO_SECRET_KEY` | 仅开发回退值 | 生产必填 |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | 逗号分隔 |
| `DJANGO_LOG_LEVEL` | `INFO` | Django 日志级别 |
| `DJANGO_SQL_LOGGING` | `False` | 仅排查 SQL 时开启 |
| `DJANGO_USE_SQLITE` | `False` | 无 MySQL 的本地 UI 联调可设为 `True` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | 空 | 可信前端来源，包含协议 |
| `CORS_ALLOWED_ORIGINS` | 本地前端地址 | 必须包含协议 |
| `DB_*` | 见 `.env.example` | MySQL 连接参数 |

## 4. API 约定

- 管理端使用 `/api/`，默认要求 `Authorization: Bearer <access>`。
- 公开读取与评论使用 `/blog/`，只返回已发布内容。
- 响应统一包含 `code`、`message` 和 `data`。
- 客户端发送的 `X-Request-ID` 会写回响应；五分钟内重复的写请求返回 409。
- 未捕获异常由 `blog.exception_handler` 转换，生产环境不返回堆栈。

新增 ViewSet 时应显式设置 `permission_classes`，不要通过覆盖 `dispatch` 绕过认证。

## 5. 测试与检查

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

测试命令自动切换到内存 SQLite。新增接口至少覆盖：匿名权限、成功响应、非法输入和数据可见范围。

生产发布前额外运行：

```bash
DJANGO_DEBUG=False \
DJANGO_SECRET_KEY='replace-with-a-long-random-secret' \
DJANGO_ALLOWED_HOSTS='blog.example.com' \
python manage.py check --deploy
```

## 6. 依赖管理

`requirements.txt` 只保留运行时直接依赖。新增包前确认标准库或 Django 已有能力不能满足需求；更新依赖后执行完整测试和 `pip check`。
