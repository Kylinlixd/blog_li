# 后端部署指南

推荐拓扑：Nginx 提供 HTTPS、前端静态资源与媒体文件，反向代理 `/api/` 到 Gunicorn；Gunicorn 只监听本机。

## 1. 准备

```bash
git clone https://github.com/Kylinlixd/blog_li.git /srv/blog_li
cd /srv/blog_li
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

生产 `.env` 至少配置：

```dotenv
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=生成的长随机字符串
DJANGO_ALLOWED_HOSTS=blog.example.com
DJANGO_LOG_LEVEL=INFO
CORS_ALLOWED_ORIGINS=https://blog.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://blog.example.com
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DB_NAME=blog
DB_USER=blog
DB_PASSWORD=强密码
DB_HOST=127.0.0.1
DB_PORT=3306
```

限制 `.env` 权限：应用以独立的 `blog` 用户运行时，使用 root 所有、blog 组可读的权限，避免 Gunicorn 无法加载配置：

```bash
chown root:blog .env
chmod 640 .env
```

仅在所有子域都已永久启用 HTTPS 时使用 `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True`；确认无误后再考虑开启 HSTS preload。

### AstraStoreXion 双存储

新版本支持逐文件选择存储后端。历史记录和 `/media/` 文件默认保持 `local`，启用后只有新上传写入 Xion，无需批量迁移旧文件。

先保持关闭状态发布后端：

```dotenv
XION_STORAGE_ENABLED=False
XION_BASE_URL=http://127.0.0.1:8081
XION_SERVICE_TOKEN=
XION_CONNECT_TIMEOUT=5
XION_READ_TIMEOUT=1800
XION_MAX_RETRIES=2
BLOG_FILE_MAX_UPLOAD_BYTES=1073741824
```

安装 AstraStoreXion Python SDK，并确认 Xion 仅监听回环地址：

```bash
source .venv/bin/activate
pip install /path/to/AstraStoreXion/client/python
curl --fail http://127.0.0.1:8081/readyz
ss -ltnp | grep '127.0.0.1:8081'
```

把服务器端生成的同一服务密钥写入 Xion 和 Django 的 mode 0600 环境文件，再设置 `XION_STORAGE_ENABLED=True` 并重启 Gunicorn。不要在终端输出、Git、前端环境或截图中暴露密钥。

## 2. 发布命令

```bash
source .venv/bin/activate
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py test
```

迁移前备份数据库。用户上传的 `media/` 也必须独立备份，不能依赖 Git。

迁移 `upload.0003_uploadfile_storage_fields` 只增加后端、对象键、校验和与 MIME 字段；现有行默认 `storage_backend=local`。

### 存储冒烟测试

`ops/production-storage-smoke.py` 是分阶段的进程内持久性检查，用于在服务重启和功能开关切换前后验证同一批对象；它不会经过 Nginx、Gunicorn 或 JWT，不能替代公网检查。

部署完成后，从服务器执行真实 HTTPS、JWT、Nginx、Gunicorn、Django 与 Xion 全链路检查。命令会创建随机密码的临时用户，上传四类 fixture，逐一校验认证/公开下载并清理所有记录：

```bash
python ops/https-storage-smoke.py \
  --base-url https://leexd.top \
  --fixture-dir /path/to/generated-fixtures
```

## 3. systemd 示例

```ini
[Unit]
Description=Kylin Blog Gunicorn
After=network.target mysql.service

[Service]
User=blog
Group=blog
WorkingDirectory=/srv/blog_li
EnvironmentFile=/srv/blog_li/.env
ExecStart=/srv/blog_li/.venv/bin/gunicorn blog.wsgi:application --workers 3 --bind 127.0.0.1:8000 --timeout 330 --access-logfile - --error-logfile -
Restart=on-failure
TimeoutStopSec=30
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
ReadWritePaths=/srv/blog_li/media

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now kylin-blog
```

公开媒体目录需要让 Nginx 能够穿越目录并读取文件，但不需要写权限：

```bash
find /srv/blog_li/media -type d -exec chmod 755 {} +
find /srv/blog_li/media -type f -exec chmod 644 {} +
chown -R blog:blog /srv/blog_li/media
```

### SSH 远程维护边界

如果业务明确要求保留 root 密码登录，使用 `/etc/ssh/sshd_config.d/99-blog-hardening.conf` 管理配置，并在重载前执行 `sshd -t`。推荐同时保留以下限制：`MaxAuthTries 3`、`LoginGraceTime 20`、`X11Forwarding no`、`ClientAliveInterval 300`、`ClientAliveCountMax 2`。修改后使用一条新的密码 SSH 连接验证，不要只依赖当前会话。

## 4. Nginx 要点

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

# 公开 API 统一在 /api/blog/；/blog/ 由前端站点按 SPA 路由处理。

location /media/ {
    alias /srv/blog_li/media/;
}

location /static/ {
    alias /srv/blog_li/staticfiles/;
}
```

在 Nginx 层配置证书、上传大小限制、请求超时和日志轮转。不要让 Django 在生产环境直接提供媒体或静态文件。

## 5. 发布与回滚检查

- `python manage.py check --deploy` 无阻断问题
- 全量测试通过，迁移在预发布数据库验证
- 登录、刷新令牌、公开文章、评论、上传和仪表盘冒烟测试通过
- PNG、PDF、DOCX、TXT 通过博客 API 上传；下载 SHA-256 与本地一致
- 重启 Xion 和 Gunicorn 后新文件仍可下载，专用测试记录可完整删除
- 至少一个历史 `/media/` 链接仍返回 200
- 数据库与 `media/` 备份可恢复
- 监控 5xx、Gunicorn 重启、磁盘空间和数据库连接

回滚代码前先确认迁移是否可逆；不要在未备份时执行破坏性反向迁移。

若只回滚新写入，先设置 `XION_STORAGE_ENABLED=False` 并重启 Gunicorn。保留 Xion 服务与数据目录，以便读取已经标记为 `xion` 的历史记录；不要把关闭新写入误当成可以删除存储对象。
