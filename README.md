# 开发文档

## 项目简介

本项目为基于 Django + DRF 的多角色内容管理系统，支持用户注册、登录、动态内容管理、评论、标签、分类、文件上传、统计等功能，采用 JWT 认证。

## 开发环境要求

- Python 3.8+
- Django 5.1+
- Django REST framework 3.14+
- MySQL 8.0+
- Redis (可选，用于缓存)

## 本地开发环境搭建

1. 克隆项目
```bash
git clone <项目地址>
cd blog_li
```

2. 创建并激活虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置数据库
- 创建 MySQL 数据库
- 修改 `blog/settings.py` 中的数据库配置：
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

5. 执行数据库迁移
```bash
python manage.py makemigrations
python manage.py migrate
```

6. 创建超级用户
```bash
python manage.py createsuperuser
```

7. 启动开发服务器
```bash
python manage.py runserver
```

## 生产环境部署

### 1. 服务器要求
- Linux 服务器（推荐 Ubuntu 20.04+）
- Nginx
- Gunicorn
- MySQL
- Redis（可选）

### 2. 部署步骤

1. 安装系统依赖
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx mysql-server
```

2. 配置项目
```bash
# 克隆项目
git clone <项目地址>
cd blog_li

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn

# 修改 settings.py
DEBUG = False
ALLOWED_HOSTS = ['your_domain.com', 'www.your_domain.com']
```

3. 配置 Gunicorn
创建 `/etc/systemd/system/gunicorn.service`：
```ini
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/blog_li
ExecStart=/path/to/blog_li/venv/bin/gunicorn --workers 3 --bind unix:/path/to/blog_li/gunicorn.sock blog.wsgi:application

[Install]
WantedBy=multi-user.target
```

4. 配置 Nginx
创建 `/etc/nginx/sites-available/blog_li`：
```nginx
server {
    listen 80;
    server_name your_domain.com www.your_domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /path/to/blog_li;
    }

    location /media/ {
        root /path/to/blog_li;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/path/to/blog_li/gunicorn.sock;
    }
}
```

5. 启动服务
```bash
# 收集静态文件
python manage.py collectstatic

# 启动 Gunicorn
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

# 配置 Nginx
sudo ln -s /etc/nginx/sites-available/blog_li /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### 3. 安全配置

1. 配置 SSL 证书（使用 Let's Encrypt）
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com -d www.your_domain.com
```

2. 配置防火墙
```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

### 4. 自动部署脚本

#### 4.1 部署脚本 (deploy.sh)

```bash
#!/bin/bash

# 设置环境变量
APP_NAME="blog_li"
APP_DIR="/var/www/$APP_NAME"
VENV_DIR="$APP_DIR/venv"
GIT_REPO="<your-git-repo-url>"
BRANCH="main"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        error "$1 未安装"
    fi
}

# 检查必要的命令
check_command git
check_command python3
check_command pip3
check_command nginx
check_command systemctl

# 创建应用目录
if [ ! -d "$APP_DIR" ]; then
    log "创建应用目录: $APP_DIR"
    sudo mkdir -p $APP_DIR
    sudo chown -R $USER:$USER $APP_DIR
fi

# 克隆或更新代码
if [ ! -d "$APP_DIR/.git" ]; then
    log "克隆代码仓库"
    git clone $GIT_REPO $APP_DIR || error "代码克隆失败"
else
    log "更新代码"
    cd $APP_DIR
    git fetch origin || error "代码更新失败"
    git checkout $BRANCH || error "分支切换失败"
    git pull origin $BRANCH || error "代码拉取失败"
fi

# 创建并激活虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    log "创建虚拟环境"
    python3 -m venv $VENV_DIR || error "虚拟环境创建失败"
fi

# 激活虚拟环境并安装依赖
log "安装/更新依赖"
source $VENV_DIR/bin/activate || error "虚拟环境激活失败"
pip install --upgrade pip || error "pip 更新失败"
pip install -r $APP_DIR/requirements.txt || error "依赖安装失败"
pip install gunicorn || error "gunicorn 安装失败"

# 收集静态文件
log "收集静态文件"
python $APP_DIR/manage.py collectstatic --noinput || error "静态文件收集失败"

# 执行数据库迁移
log "执行数据库迁移"
python $APP_DIR/manage.py migrate || error "数据库迁移失败"

# 重启 Gunicorn
log "重启 Gunicorn"
sudo systemctl restart gunicorn || error "Gunicorn 重启失败"

# 重启 Nginx
log "重启 Nginx"
sudo systemctl restart nginx || error "Nginx 重启失败"

log "部署完成！"
```

#### 4.2 使用说明

1. 将脚本保存为 `deploy.sh`
2. 修改脚本中的环境变量：
   - `APP_NAME`: 应用名称
   - `APP_DIR`: 应用部署目录
   - `GIT_REPO`: Git 仓库地址
   - `BRANCH`: 要部署的分支

3. 添加执行权限：
```bash
chmod +x deploy.sh
```

4. 执行部署：
```bash
./deploy.sh
```

#### 4.3 定时自动部署

1. 创建定时任务：
```bash
crontab -e
```

2. 添加定时任务（例如每天凌晨 2 点执行）：
```
0 2 * * * /path/to/deploy.sh >> /var/log/blog_li_deploy.log 2>&1
```

#### 4.4 回滚脚本 (rollback.sh)

```bash
#!/bin/bash

# 设置环境变量
APP_NAME="blog_li"
APP_DIR="/var/www/$APP_NAME"
BACKUP_DIR="$APP_DIR/backups"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# 检查备份目录
if [ ! -d "$BACKUP_DIR" ]; then
    error "备份目录不存在"
fi

# 获取最新的备份
LATEST_BACKUP=$(ls -t $BACKUP_DIR/*.tar.gz | head -n1)

if [ -z "$LATEST_BACKUP" ]; then
    error "没有找到备份文件"
fi

# 解压备份
log "解压备份文件: $LATEST_BACKUP"
tar -xzf $LATEST_BACKUP -C $APP_DIR || error "备份解压失败"

# 重启服务
log "重启服务"
sudo systemctl restart gunicorn || error "Gunicorn 重启失败"
sudo systemctl restart nginx || error "Nginx 重启失败"

log "回滚完成！"
```

#### 4.5 备份脚本 (backup.sh)

```bash
#!/bin/bash

# 设置环境变量
APP_NAME="blog_li"
APP_DIR="/var/www/$APP_NAME"
BACKUP_DIR="$APP_DIR/backups"
DB_NAME="your_db_name"
DB_USER="your_db_user"
DB_PASSWORD="your_db_password"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 生成备份文件名
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz"

# 备份数据库
mysqldump -u$DB_USER -p$DB_PASSWORD $DB_NAME > $APP_DIR/db_backup.sql

# 备份文件
tar -czf $BACKUP_FILE \
    $APP_DIR/db_backup.sql \
    $APP_DIR/media \
    $APP_DIR/static

# 删除临时文件
rm $APP_DIR/db_backup.sql

# 保留最近 7 天的备份
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +7 -delete
```

#### 4.6 监控脚本 (monitor.sh)

```bash
#!/bin/bash

# 设置环境变量
APP_NAME="blog_li"
APP_DIR="/var/www/$APP_NAME"
LOG_FILE="$APP_DIR/logs/monitor.log"

# 检查服务状态
check_service() {
    if ! systemctl is-active --quiet $1; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1 服务未运行，正在重启..." >> $LOG_FILE
        systemctl restart $1
    fi
}

# 检查磁盘空间
check_disk_space() {
    DISK_USAGE=$(df -h $APP_DIR | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $DISK_USAGE -gt 90 ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] 警告：磁盘使用率超过 90%" >> $LOG_FILE
    fi
}

# 检查内存使用
check_memory() {
    MEM_USAGE=$(free | grep Mem | awk '{print $3/$2 * 100.0}')
    if (( $(echo "$MEM_USAGE > 90" | bc -l) )); then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] 警告：内存使用率超过 90%" >> $LOG_FILE
    fi
}

# 主函数
main() {
    # 创建日志目录
    mkdir -p $(dirname $LOG_FILE)
    
    # 检查服务
    check_service gunicorn
    check_service nginx
    
    # 检查系统资源
    check_disk_space
    check_memory
}

# 执行主函数
main
```

#### 4.7 使用说明

1. 将所有脚本放在 `scripts` 目录下：
```bash
mkdir -p $APP_DIR/scripts
```

2. 设置定时任务：
```bash
# 每天凌晨 2 点执行备份
0 2 * * * /path/to/scripts/backup.sh

# 每 5 分钟执行一次监控
*/5 * * * * /path/to/scripts/monitor.sh
```

3. 手动执行回滚：
```bash
./scripts/rollback.sh
```

这些脚本提供了完整的自动化部署、备份、回滚和监控功能。根据实际需求，您可以修改脚本中的配置参数。

## 开发规范

1. 代码风格
- 遵循 PEP 8 规范
- 使用 Black 进行代码格式化
- 使用 isort 进行导入排序

2. Git 提交规范
- feat: 新功能
- fix: 修复 bug
- docs: 文档更新
- style: 代码格式（不影响代码运行的变动）
- refactor: 重构（既不是新增功能，也不是修改 bug 的代码变动）
- test: 增加测试
- chore: 构建过程或辅助工具的变动

3. 分支管理
- main: 主分支，用于生产环境
- develop: 开发分支，用于开发环境
- feature/*: 功能分支，用于开发新功能
- hotfix/*: 修复分支，用于修复生产环境的 bug

## 常见问题

1. 数据库连接问题
- 检查数据库配置是否正确
- 确保数据库服务正在运行
- 检查数据库用户权限

2. 静态文件问题
- 确保已执行 `python manage.py collectstatic`
- 检查 Nginx 配置中的静态文件路径
- 检查文件权限

3. 权限问题
- 检查文件系统权限
- 检查数据库用户权限
- 检查 Nginx 和 Gunicorn 用户权限

---

## API接口总览

### 认证与用户相关

- `POST   /api/auth/register/`      用户注册
- `POST   /api/auth/login/`         用户登录
- `POST   /api/token/refresh/`      刷新JWT
- `GET    /api/auth/info/`          获取当前用户信息
- `PUT    /api/auth/password/`      修改密码
- `PUT    /api/auth/profile/`       修改个人资料
- `GET    /api/users/`              用户列表
- `POST   /api/users/`              创建用户
- `GET    /api/users/{id}/`         用户详情
- `PUT    /api/users/{id}/`         更新用户
- `DELETE /api/users/{id}/`         删除用户

### 动态内容（Dynamic）

- `GET    /api/dynamics/`           动态列表
- `POST   /api/dynamics/`           创建动态
- `GET    /api/dynamics/{id}/`      动态详情
- `PUT    /api/dynamics/{id}/`      更新动态
- `DELETE /api/dynamics/{id}/`      删除动态
- `GET    /api/dynamics/{id}/adjacent/` 获取相邻动态
- `POST   /api/dynamics/{id}/view/`     增加浏览量

#### 前台动态
- `GET    /blog/dynamics/hot/`      热门动态（limit可选）
- `GET    /blog/dynamics/recent/`   最新动态（limit可选）

### 分类（Category）

- `GET    /api/categories/`         分类列表
- `POST   /api/categories/`         创建分类
- `GET    /api/categories/{id}/`    分类详情
- `PUT    /api/categories/{id}/`    更新分类
- `DELETE /api/categories/{id}/`    删除分类
- `GET    /blog/categories/`        前台分类列表

### 标签（Tag）

- `GET    /api/tags/`               标签列表
- `POST   /api/tags/`               创建标签
- `GET    /api/tags/{id}/`          标签详情
- `PUT    /api/tags/{id}/`          更新标签
- `DELETE /api/tags/{id}/`          删除标签

### 评论（Comment）

- `GET    /api/comments/`           评论列表
- `POST   /api/comments/`           创建评论
- `GET    /api/comments/{id}/`      评论详情
- `PUT    /api/comments/{id}/`      更新评论
- `DELETE /api/comments/{id}/`      删除评论
- `PUT    /api/comments/{id}/approve/` 审核通过
- `PUT    /api/comments/{id}/reject/`  审核拒绝

### 文件上传

- `POST   /api/upload/file/`        文件上传

### 仪表盘统计

- `GET    /api/stats/`              统计数据

---

## 认证与用户相关接口

### 1. 用户注册

- **POST** `/api/auth/register/`
- **参数说明**：

| 字段      | 类型   | 必填 | 说明         |
|-----------|--------|------|--------------|
| username  | string | 是   | 用户名       |
| password  | string | 是   | 密码         |
| email     | string | 是   | 邮箱         |
| role      | string | 否   | 角色(user/admin/company) |

- **请求示例**：
```json
{
  "username": "testuser",
  "password": "123456",
  "email": "test@example.com",
  "role": "user"
}
```
- **响应示例**：
```json
{
  "code": 200,
  "data": {
    "token": "jwt-token-string",
    "userInfo": {
      "id": 1,
      "username": "testuser",
      "email": "test@example.com",
      "role": "user",
      "nickname": "",
      "avatar": "",
      "bio": "",
      "permissions": [],
      "created_at": "2024-06-01T12:00:00Z",
      "updated_at": "2024-06-01T12:00:00Z"
    }
  },
  "message": "注册成功"
}
```

---

### 2. 用户登录

- **POST** `/api/auth/login/`
- **参数说明**：

| 字段      | 类型   | 必填 | 说明   |
|-----------|--------|------|--------|
| username  | string | 是   | 用户名 |
| password  | string | 是   | 密码   |

- **请求示例**：
```json
{
  "username": "testuser",
  "password": "123456"
}
```
- **响应示例**：
```json
{
  "code": 200,
  "data": {
    "token": "jwt-token-string",
    "userInfo": {
      "id": 1,
      "username": "testuser",
      "email": "test@example.com",
      "role": "user",
      "nickname": "",
      "avatar": "",
      "bio": "",
      "permissions": [],
      "created_at": "2024-06-01T12:00:00Z",
      "updated_at": "2024-06-01T12:00:00Z"
    }
  },
  "message": "登录成功"
}
```

---

### 3. 获取当前用户信息

- **GET** `/api/auth/info/`
- **Header**: `Authorization: Bearer <token>`
- **响应示例**：
```json
{
  "code": 200,
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "role": "user",
    "nickname": "",
    "avatar": "",
    "bio": "",
    "permissions": [],
    "created_at": "2024-06-01T12:00:00Z",
    "updated_at": "2024-06-01T12:00:00Z"
  },
  "message": "获取用户信息成功"
}
```

---

### 4. 修改密码

- **PUT** `/api/auth/password/`
- **参数说明**：

| 字段         | 类型   | 必填 | 说明     |
|--------------|--------|------|----------|
| old_password | string | 是   | 旧密码   |
| new_password | string | 是   | 新密码   |

- **请求示例**：
```json
{
  "old_password": "123456",
  "new_password": "654321"
}
```
- **响应示例**：
```json
{
  "code": 200,
  "message": "密码修改成功"
}
```

---

### 5. 修改个人资料

- **PUT** `/api/auth/profile/`
- **参数说明**：

| 字段     | 类型   | 必填 | 说明         |
|----------|--------|------|--------------|
| nickname | string | 否   | 昵称         |
| email    | string | 否   | 邮箱         |
| bio      | string | 否   | 个人简介     |
| avatar   | string | 否   | 头像URL      |

- **请求示例**：
```json
{
  "nickname": "小明",
  "bio": "热爱编程"
}
```
- **响应示例**：
```json
{
  "code": 200,
  "data": {
    "id": 1,
    "username": "testuser",
    "nickname": "小明",
    "email": "test@example.com",
    "bio": "热爱编程",
    "avatar": "",
    "role": "user",
    "permissions": [],
    "created_at": "2024-06-01T12:00:00Z",
    "updated_at": "2024-06-01T12:10:00Z"
  },
  "message": "个人资料更新成功"
}
```

---

### 6. 刷新Token

- **POST** `/api/token/refresh/`
- **参数说明**：

| 字段    | 类型   | 必填 | 说明         |
|---------|--------|------|--------------|
| refresh | string | 是   | 刷新token    |

- **请求示例**：
```json
{
  "refresh": "refresh-token-string"
}
```
- **响应示例**：
```json
{
  "access": "new-access-token"
}
```

---

## 动态内容接口

### 1. 动态列表

- **GET** `/api/dynamics/`
- **查询参数**：

| 字段    | 类型   | 必填 | 说明         |
|---------|--------|------|--------------|
| type    | string | 否   | 动态类型     |
| status  | string | 否   | 状态         |
| page    | int    | 否   | 页码         |
| pageSize| int    | 否   | 每页数量     |

- **响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 2,
    "items": [
      {
        "id": 1,
        "content": "第一条动态内容",
        "type": "text",
        "status": "published",
        "media_urls": [],
        "category": null,
        "tags": [],
        "view_count": 10,
        "created_at": "2024-06-01T12:00:00Z",
        "updated_at": "2024-06-01T12:00:00Z",
        "author": {
          "id": 1,
          "username": "testuser"
        }
      }
    ]
  }
}
```

### 2. 创建动态

- **POST** `/api/dynamics/`
- **参数说明**：

| 字段       | 类型     | 必填 | 说明         |
|------------|----------|------|--------------|
| content    | string   | 是   | 动态内容     |
| type       | string   | 否   | 类型(text/image/audio/video) |
| status     | string   | 否   | 状态(draft/published) |
| media_urls | array    | 否   | 媒体文件URL  |
| category   | int      | 否   | 分类ID       |
| tags       | array    | 否   | 标签ID列表   |

- **请求示例**：
```json
{
  "content": "新动态内容",
  "type": "text",
  "status": "published"
}
```
- **响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 2,
    "content": "新动态内容",
    "type": "text",
    "status": "published",
    "media_urls": [],
    "category": null,
    "tags": [],
    "view_count": 0,
    "created_at": "2024-06-01T13:00:00Z",
    "updated_at": "2024-06-01T13:00:00Z",
    "author": {
      "id": 1,
      "username": "testuser"
    }
  }
}
```

### 3. 动态详情

- **GET** `/api/dynamics/{id}/`
- **响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "content": "第一条动态内容",
    "type": "text",
    "status": "published",
    "media_urls": [],
    "category": null,
    "tags": [],
    "view_count": 10,
    "created_at": "2024-06-01T12:00:00Z",
    "updated_at": "2024-06-01T12:00:00Z",
    "author": {
      "id": 1,
      "username": "testuser"
    }
  }
}
```

### 4. 更新/删除动态

- **PUT** `/api/dynamics/{id}/`
- **DELETE** `/api/dynamics/{id}/`
- **请求参数**：同创建动态
- **响应**：
```json
{
  "code": 200,
  "message": "更新动态成功"
}
```
或
```json
{
  "code": 200,
  "message": "删除动态成功"
}
```

### 5. 获取相邻动态

- **GET** `/api/dynamics/{id}/adjacent/`
- **响应示例**：
```json
{
  "code": 200,
  "data": {
    "prev": { ... },  // 上一条动态
    "next": { ... }   // 下一条动态
  },
  "message": "获取相邻动态成功"
}
```

### 6. 增加浏览量

- **POST** `/api/dynamics/{id}/view/`
- **响应**：
```json
{
  "code": 200,
  "message": "浏览量增加成功"
}
```

### 7. 热门/最新动态

- **GET** `/blog/dynamics/hot/`
- **GET** `/blog/dynamics/recent/`
- **查询参数**：limit（可选，默认5）
- **响应**：
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "content": "热门动态内容",
      "view_count": 100
    }
  ],
  "message": "获取热门动态成功"
}
```

---

## 分类与标签接口

### 分类

- **GET** `/api/categories/`
- **POST** `/api/categories/`
- **GET** `/api/categories/{id}/`
- **PUT** `/api/categories/{id}/`
- **DELETE** `/api/categories/{id}/`
- **GET** `/blog/categories/`

- **参数说明**（创建/更新）：

| 字段     | 类型   | 必填 | 说明     |
|----------|--------|------|----------|
| name     | string | 是   | 分类名称 |
| parent   | int    | 否   | 父级ID  |

- **响应示例**（列表）：
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "技术",
      "parent": null
    }
  ],
  "message": "success"
}
```

### 标签

- **GET** `/api/tags/`
- **POST** `/api/tags/`
- **GET** `/api/tags/{id}/`
- **PUT** `/api/tags/{id}/`
- **DELETE** `/api/tags/{id}/`

- **参数说明**（创建/更新）：

| 字段     | 类型   | 必填 | 说明     |
|----------|--------|------|----------|
| name     | string | 是   | 标签名称 |

- **响应示例**（列表）：
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "Python"
      }
    ],
    "total": 1
  },
  "message": "success"
}
```

---

## 评论接口

- **GET** `/api/comments/`
- **POST** `/api/comments/`
- **GET** `/api/comments/{id}/`
- **PUT** `/api/comments/{id}/`
- **DELETE** `/api/comments/{id}/`
- **PUT** `/api/comments/{id}/approve/`
- **PUT** `/api/comments/{id}/reject/`

- **参数说明**（创建/更新）：

| 字段     | 类型   | 必填 | 说明         |
|----------|--------|------|--------------|
| content  | string | 是   | 评论内容     |
| dynamic  | int    | 是   | 动态ID       |
| parent   | int    | 否   | 父评论ID     |

- **响应示例**（列表）：
```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "id": 1,
        "content": "很棒的内容！",
        "author": {
          "id": 1,
          "username": "testuser"
        },
        "dynamic": 1,
        "parent": null,
        "status": "approved",
        "created_at": "2024-06-01T12:00:00Z",
        "updated_at": "2024-06-01T12:00:00Z",
        "replies": []
      }
    ],
    "total": 1
  },
  "message": "获取评论列表成功"
}
```

---

## 文件上传

- **POST** `/api/upload/file/`
- **参数说明**：

| 字段      | 类型   | 必填 | 说明         |
|-----------|--------|------|--------------|
| file      | file   | 是   | 文件         |
| file_type | string | 是   | 文件类型     |

- **响应示例**：
```json
{
  "code": 200,
  "data": {
    "id": 1,
    "name": "test.png",
    "file_type": "image",
    "file_size": 12345,
    "file_url": "/media/image/xxx.png",
    "uploader": 1
  },
  "message": "文件上传成功"
}
```

---

## 仪表盘统计

- **GET** `/api/stats/`
- **响应示例**：
```json
{
  "code": 200,
  "data": {
    "total": {
      "dynamics": 10,
      "categories": 3,
      "tags": 5,
      "comments": 20
    },
    "daily": [
      {"day": "2024-06-01", "count": 2}
    ],
    "categories": [
      {"name": "技术", "dynamic_count": 5}
    ],
    "tags": [
      {"name": "Python", "dynamic_count": 3}
    ]
  },
  "message": "success"
}
```

---

## 说明

- 除注册、登录、部分GET外，所有`/api/`接口均需JWT认证（`Authorization: Bearer <token>`）。
- 返回格式统一为：
  ```json
  {
    "code": 200,
    "data": { ... },
    "message": "success"
  }
  ```
- 详细字段和参数请参考各模块序列化器（serializers.py）定义。

如需补充具体请求/响应示例或参数说明，请告知！

# 博客系统 API 文档

## 文件管理模块

### 1. 文件上传

**请求地址**：`/api/upload/upload/`

**请求方法**：`POST`

**请求头**：
```
Content-Type: multipart/form-data
Authorization: Token <your_token>
```

**请求参数**：
```json
{
    "file": "文件对象",
    "file_type": "文件类型(image/video/audio/document/other)",
    "dynamic_id": "动态ID（可选）",
    "category_id": "分类ID（可选）",
    "tag_ids": ["标签ID数组（可选）"],
    "description": "文件描述（可选）",
    "is_public": "是否公开（可选，默认true）"
}
```

**响应数据**：
```json
{
    "code": 200,
    "data": {
        "id": "文件ID",
        "name": "文件名",
        "file_type": "文件类型",
        "file_size": "文件大小",
        "file_url": "文件URL",
        "category": {
            "id": "分类ID",
            "name": "分类名称",
            "description": "分类描述",
            "sort": "排序",
            "status": "状态",
            "created_at": "创建时间",
            "updated_at": "更新时间"
        },
        "tags": [
            {
                "id": "标签ID",
                "name": "标签名称",
                "description": "标签描述",
                "sort": "排序",
                "status": "状态",
                "created_at": "创建时间",
                "updated_at": "更新时间"
            }
        ],
        "uploader": {
            "id": "上传者ID",
            "username": "用户名",
            "nickname": "昵称",
            "avatar": "头像URL"
        },
        "description": "文件描述",
        "is_public": "是否公开",
        "download_count": "下载次数",
        "created_at": "创建时间",
        "updated_at": "更新时间"
    },
    "message": "文件上传成功"
}
```

### 2. 文件列表

**请求地址**：`/api/upload/files/`

**请求方法**：`GET`

**请求头**：
```
Authorization: Token <your_token>
```

**请求参数**：
```
page: 页码（可选，默认1）
pageSize: 每页数量（可选，默认10）
```

**响应数据**：
```json
{
    "code": 200,
    "data": {
        "items": [
            {
                "id": "文件ID",
                "name": "文件名",
                "file_type": "文件类型",
                "file_size": "文件大小",
                "file_url": "文件URL",
                "category": {
                    "id": "分类ID",
                    "name": "分类名称",
                    "description": "分类描述",
                    "sort": "排序",
                    "status": "状态",
                    "created_at": "创建时间",
                    "updated_at": "更新时间"
                },
                "tags": [
                    {
                        "id": "标签ID",
                        "name": "标签名称",
                        "description": "标签描述",
                        "sort": "排序",
                        "status": "状态",
                        "created_at": "创建时间",
                        "updated_at": "更新时间"
                    }
                ],
                "uploader": {
                    "id": "上传者ID",
                    "username": "用户名",
                    "nickname": "昵称",
                    "avatar": "头像URL"
                },
                "description": "文件描述",
                "is_public": "是否公开",
                "download_count": "下载次数",
                "created_at": "创建时间",
                "updated_at": "更新时间"
            }
        ],
        "total": "总数"
    },
    "message": "获取成功"
}
```

### 3. 文件搜索

**请求地址**：`/api/upload/files/search/`

**请求方法**：`GET`

**请求头**：
```
Authorization: Token <your_token>
```

**请求参数**：
```
q: 搜索关键词（可选）
type: 文件类型（可选）
category: 分类ID（可选）
tags: 标签ID数组（可选）
page: 页码（可选，默认1）
pageSize: 每页数量（可选，默认10）
```

**响应数据**：同文件列表

### 4. 文件下载

**请求地址**：`/api/upload/files/{file_id}/download/`

**请求方法**：`POST`

**请求头**：
```
Authorization: Token <your_token>
```

**响应数据**：文件流

### 5. 分类管理

#### 5.1 获取分类列表

**请求地址**：`/api/upload/categories/`

**请求方法**：`GET`

**请求头**：
```
Authorization: Token <your_token>
```

**响应数据**：
```json
{
    "code": 200,
    "data": [
        {
            "id": "分类ID",
            "name": "分类名称",
            "description": "分类描述",
            "sort": "排序",
            "status": "状态",
            "created_at": "创建时间",
            "updated_at": "更新时间"
        }
    ],
    "message": "获取成功"
}
```

#### 5.2 创建分类

**请求地址**：`/api/upload/categories/`

**请求方法**：`POST`

**请求头**：
```
Content-Type: application/json
Authorization: Token <your_token>
```

**请求参数**：
```json
{
    "name": "分类名称",
    "description": "分类描述（可选）",
    "sort": "排序（可选，默认0）",
    "status": "状态（可选，默认true）"
}
```

**响应数据**：
```json
{
    "code": 200,
    "data": {
        "id": "分类ID",
        "name": "分类名称",
        "description": "分类描述",
        "sort": "排序",
        "status": "状态",
        "created_at": "创建时间",
        "updated_at": "更新时间"
    },
    "message": "创建成功"
}
```

### 6. 标签管理

#### 6.1 获取标签列表

**请求地址**：`/api/upload/tags/`

**请求方法**：`GET`

**请求头**：
```
Authorization: Token <your_token>
```

**响应数据**：
```json
{
    "code": 200,
    "data": [
        {
            "id": "标签ID",
            "name": "标签名称",
            "description": "标签描述",
            "sort": "排序",
            "status": "状态",
            "created_at": "创建时间",
            "updated_at": "更新时间"
        }
    ],
    "message": "获取成功"
}
```

#### 6.2 创建标签

**请求地址**：`/api/upload/tags/`

**请求方法**：`POST`

**请求头**：
```
Content-Type: application/json
Authorization: Token <your_token>
```

**请求参数**：
```json
{
    "name": "标签名称",
    "description": "标签描述（可选）",
    "sort": "排序（可选，默认0）",
    "status": "状态（可选，默认true）"
}
```

**响应数据**：
```json
{
    "code": 200,
    "data": {
        "id": "标签ID",
        "name": "标签名称",
        "description": "标签描述",
        "sort": "排序",
        "status": "状态",
        "created_at": "创建时间",
        "updated_at": "更新时间"
    },
    "message": "创建成功"
}
```

### 7. 文件类型限制

- 图片：支持 jpg、jpeg、png、gif 格式，大小限制 5MB
- 视频：支持 mp4、mov、avi 格式，大小限制 100MB
- 音频：支持 mp3、wav 格式，大小限制 20MB
- 文档：支持 pdf、doc、docx、xls、xlsx 格式，大小限制 10MB
- 其他：大小限制 10MB

### 8. 权限说明

- 所有接口都需要登录认证
- 普通用户只能看到自己的文件和公开文件
- 管理员可以看到所有文件
- 文件上传者可以修改和删除自己的文件
- 管理员可以修改和删除所有文件 