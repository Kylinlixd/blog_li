# 后端部署指南

推荐拓扑：Nginx 提供 HTTPS、前端静态资源与媒体文件，反向代理 `/api/` 和 `/blog/` 到 Gunicorn；Gunicorn 只监听本机。

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

限制 `.env` 权限：`chmod 600 .env`。

仅在所有子域都已永久启用 HTTPS 时使用 `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True`；确认无误后再考虑开启 HSTS preload。

## 2. 发布命令

```bash
source .venv/bin/activate
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py test
```

迁移前备份数据库。用户上传的 `media/` 也必须独立备份，不能依赖 Git。

## 3. systemd 示例

```ini
[Unit]
Description=Kylin Blog Gunicorn
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/blog_li
EnvironmentFile=/srv/blog_li/.env
ExecStart=/srv/blog_li/.venv/bin/gunicorn blog.wsgi:application --workers 3 --bind 127.0.0.1:8000 --access-logfile - --error-logfile -
Restart=on-failure
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now kylin-blog
```

## 4. Nginx 要点

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

location /blog/ {
    # HTML 页面由前端站点处理，其余请求进入公开 API。
    if ($http_accept ~* "text/html") {
        rewrite ^ /index.html last;
    }
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

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
- 数据库与 `media/` 备份可恢复
- 监控 5xx、Gunicorn 重启、磁盘空间和数据库连接

回滚代码前先确认迁移是否可逆；不要在未备份时执行破坏性反向迁移。
