# 部署文档

## 环境要求

### 1. 服务器要求
- CPU: 2核+
- 内存: 4GB+
- 硬盘: 50GB+
- 操作系统: Ubuntu 20.04 LTS 或 CentOS 8

### 2. 软件要求
- Python 3.8+
- MySQL 5.7+
- Nginx 1.18+
- Redis (可选，用于缓存)
- Git

## 部署方式

### 1. 传统部署

#### 1.1 安装依赖
```bash
# 安装系统依赖
sudo apt update
sudo apt install -y python3.8 python3.8-venv python3.8-dev
sudo apt install -y mysql-server nginx
sudo apt install -y build-essential libssl-dev libffi-dev

# 安装 Redis（可选）
sudo apt install -y redis-server
```

#### 1.2 配置 MySQL
```bash
# 登录 MySQL
sudo mysql

# 创建数据库和用户
CREATE DATABASE blog_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'blog_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON blog_db.* TO 'blog_user'@'localhost';
FLUSH PRIVILEGES;
```

#### 1.3 部署应用
```bash
# 克隆项目
git clone [项目地址]
cd blog_li

# 创建虚拟环境
python3.8 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements/prod.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置生产环境配置

# 收集静态文件
python manage.py collectstatic

# 数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser
```

#### 1.4 配置 Gunicorn
```bash
# 安装 Gunicorn
pip install gunicorn

# 创建 Gunicorn 配置文件
cat > gunicorn_config.py << EOF
bind = "127.0.0.1:8000"
workers = 4
worker_class = "gevent"
timeout = 120
keepalive = 5
errorlog = "logs/gunicorn_error.log"
accesslog = "logs/gunicorn_access.log"
loglevel = "info"
EOF

# 创建日志目录
mkdir -p logs
```

#### 1.5 配置 Nginx
```bash
# 创建 Nginx 配置文件
sudo nano /etc/nginx/sites-available/blog

# 添加以下配置
server {
    listen 80;
    server_name your_domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your_domain.com;

    ssl_certificate /etc/letsencrypt/live/your_domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your_domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /static/ {
        alias /var/www/blog/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        alias /var/www/blog/media/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 1.6 配置 Supervisor
```bash
# 安装 Supervisor
sudo apt install -y supervisor

# 创建配置文件
sudo nano /etc/supervisor/conf.d/blog.conf

# 添加以下配置
[program:blog]
command=/path/to/venv/bin/gunicorn -c gunicorn_config.py blog.wsgi:application
directory=/path/to/blog_li
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/blog.err.log
stdout_logfile=/var/log/supervisor/blog.out.log

# 更新 Supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start blog
```

#### 1.7 配置 SSL 证书
```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取 SSL 证书
sudo certbot --nginx -d your_domain.com

# 设置自动续期
sudo certbot renew --dry-run
```

### 2. Docker 部署

#### 2.1 安装 Docker 和 Docker Compose
```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.5.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2.2 创建 Docker 配置文件
```bash
# 创建 docker-compose.yml
cat > docker-compose.yml << EOF
version: '3'

services:
  web:
    build: .
    command: gunicorn blog.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - static_volume:/app/static
      - media_volume:/app/media
    expose:
      - 8000
    env_file:
      - .env
    depends_on:
      - db
      - redis

  db:
    image: mysql:5.7
    volumes:
      - mysql_data:/var/lib/mysql
    environment:
      - MYSQL_DATABASE=blog_db
      - MYSQL_USER=blog_user
      - MYSQL_PASSWORD=your_password
      - MYSQL_ROOT_PASSWORD=your_root_password

  redis:
    image: redis:6
    volumes:
      - redis_data:/data

  nginx:
    build: ./nginx
    volumes:
      - static_volume:/app/static
      - media_volume:/app/media
    ports:
      - "80:80"
    depends_on:
      - web

volumes:
  mysql_data:
  redis_data:
  static_volume:
  media_volume:
EOF

# 创建 Dockerfile
cat > Dockerfile << EOF
FROM python:3.8

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app

COPY requirements/prod.txt /app/
RUN pip install -r prod.txt

COPY . /app/

RUN python manage.py collectstatic --noinput
EOF

# 创建 Nginx 配置
mkdir -p nginx
cat > nginx/Dockerfile << EOF
FROM nginx:1.18

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d
EOF

cat > nginx/nginx.conf << EOF
upstream blog {
    server web:8000;
}

server {
    listen 80;
    server_name your_domain.com;

    location /static/ {
        alias /app/static/;
    }

    location /media/ {
        alias /app/media/;
    }

    location / {
        proxy_pass http://blog;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
```

#### 2.3 部署应用
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 执行数据库迁移
docker-compose exec web python manage.py migrate

# 创建超级用户
docker-compose exec web python manage.py createsuperuser
```

## 维护指南

### 1. 日志管理
- 应用日志：`logs/gunicorn_error.log` 和 `logs/gunicorn_access.log`
- Nginx 日志：`/var/log/nginx/access.log` 和 `/var/log/nginx/error.log`
- Supervisor 日志：`/var/log/supervisor/blog.err.log` 和 `/var/log/supervisor/blog.out.log`

### 2. 备份策略
```bash
# 创建备份目录
mkdir -p /var/backups/blog

# 数据库备份脚本
cat > /usr/local/bin/backup_blog.sh << EOF
#!/bin/bash
BACKUP_DIR="/var/backups/blog"
DATE=\$(date +%Y%m%d_%H%M%S)

# 数据库备份
mysqldump -u blog_user -p blog_db > \$BACKUP_DIR/db_\$DATE.sql

# 文件备份
tar -czf \$BACKUP_DIR/media_\$DATE.tar.gz /var/www/blog/media/

# 保留最近30天的备份
find \$BACKUP_DIR -name "db_*.sql" -mtime +30 -delete
find \$BACKUP_DIR -name "media_*.tar.gz" -mtime +30 -delete
EOF

chmod +x /usr/local/bin/backup_blog.sh

# 添加到 crontab
echo "0 2 * * * /usr/local/bin/backup_blog.sh" | sudo tee -a /var/spool/cron/crontabs/root
```

### 3. 数据库恢复
```bash
# 恢复数据库
mysql -u blog_user -p blog_db < /var/backups/blog/db_20240320_120000.sql

# 恢复媒体文件
tar -xzf /var/backups/blog/media_20240320_120000.tar.gz -C /var/www/blog/
```

### 4. 监控
- 使用 Supervisor 监控应用进程
- 使用 Nginx 状态监控
- 使用 MySQL 监控工具
- 使用 Redis 监控工具（如果使用）

### 5. 更新部署
```bash
# 拉取最新代码
git pull

# 安装依赖
pip install -r requirements/prod.txt

# 收集静态文件
python manage.py collectstatic --noinput

# 数据库迁移
python manage.py migrate

# 重启服务
sudo supervisorctl restart blog
```

## 故障排除

### 1. 常见问题
1. 502 Bad Gateway
   - 检查 Gunicorn 是否运行
   - 检查 Nginx 配置
   - 检查日志文件

2. 数据库连接错误
   - 检查数据库服务是否运行
   - 检查数据库配置
   - 检查数据库用户权限

3. 静态文件 404
   - 检查静态文件目录权限
   - 检查 Nginx 配置
   - 检查 collectstatic 是否执行

### 2. 性能优化
1. 数据库优化
   - 添加适当的索引
   - 优化查询语句
   - 配置数据库缓存

2. 应用优化
   - 使用 Redis 缓存
   - 配置 Gunicorn 工作进程
   - 优化静态文件服务

3. Nginx 优化
   - 启用 gzip 压缩
   - 配置缓存
   - 优化 SSL 配置 