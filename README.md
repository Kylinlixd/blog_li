# 博客系统后端

基于 Django + DRF 开发的博客系统后端，提供完整的博客功能，包括动态管理、分类管理、标签管理、评论系统、用户认证等。

## 系统架构

### 技术栈
- 后端框架：Django 5.1.7
- REST API：Django REST Framework 3.16.0
- 认证：JWT (djangorestframework-simplejwt 5.5.0)
- 数据库：MySQL
- 图片处理：Pillow
- 环境变量：python-dotenv

### 项目结构
```
blog_li/
├── apps/                    # 应用目录
│   ├── core/               # 核心功能模块
│   │   ├── middleware/     # 中间件
│   │   ├── permissions/    # 权限类
│   │   └── utils/         # 通用工具
│   ├── article/           # 文章管理
│   ├── category/          # 分类管理
│   ├── comment/           # 评论系统
│   ├── dynamic/           # 动态管理
│   ├── media/             # 媒体文件
│   ├── tag/               # 标签管理
│   └── user/              # 用户管理
├── config/                 # 配置文件目录
│   ├── settings/          # 分环境配置
│   │   ├── base.py       # 基础配置
│   │   ├── dev.py        # 开发环境
│   │   └── prod.py       # 生产环境
│   ├── urls.py           # URL配置
│   └── wsgi.py           # WSGI配置
├── docs/                  # 文档目录
│   ├── api/              # API文档
│   └── deploy/           # 部署文档
├── scripts/              # 脚本目录
│   ├── deploy.sh         # 部署脚本
│   └── backup.sh         # 备份脚本
├── tests/                # 测试目录
│   ├── unit/            # 单元测试
│   └── integration/     # 集成测试
├── media/                # 上传文件存储
├── static/               # 静态文件
├── templates/            # 模板文件
├── .env                  # 环境变量
├── .env.example          # 环境变量示例
├── .gitignore           # Git忽略文件
├── manage.py            # Django管理脚本
├── requirements/        # 依赖管理
│   ├── base.txt        # 基础依赖
│   ├── dev.txt         # 开发依赖
│   └── prod.txt        # 生产依赖
└── README.md           # 项目说明
```

### 目录说明

#### 1. 应用目录 (apps/)
- `core/`: 核心功能模块，包含中间件、权限类和通用工具
- `article/`: 文章管理模块
- `category/`: 分类管理模块
- `comment/`: 评论系统模块
- `dynamic/`: 动态管理模块
- `media/`: 媒体文件管理模块
- `tag/`: 标签管理模块
- `user/`: 用户管理模块

#### 2. 配置目录 (config/)
- `settings/`: 分环境配置文件
  - `base.py`: 基础配置
  - `dev.py`: 开发环境配置
  - `prod.py`: 生产环境配置
- `urls.py`: URL 路由配置
- `wsgi.py`: WSGI 应用配置

#### 3. 文档目录 (docs/)
- `api/`: API 接口文档
- `deploy/`: 部署相关文档

#### 4. 脚本目录 (scripts/)
- `deploy.sh`: 部署脚本
- `backup.sh`: 备份脚本

#### 5. 测试目录 (tests/)
- `unit/`: 单元测试
- `integration/`: 集成测试

#### 6. 依赖管理 (requirements/)
- `base.txt`: 基础依赖
- `dev.txt`: 开发环境依赖
- `prod.txt`: 生产环境依赖

## 本地部署

### 环境要求
- Python 3.8+
- MySQL 5.7+
- pip

### 安装步骤

1. 克隆项目
```bash
git clone [项目地址]
cd blog_li
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
复制 `.env.example` 为 `.env`，并修改相关配置：
```env
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=blog_db
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=3306
```

5. 初始化数据库
```bash
python manage.py makemigrations
python manage.py migrate
```

6. 创建超级用户
```bash
python manage.py createsuperuser
```

7. 运行开发服务器
```bash
python manage.py runserver
```

## Docker 部署

### 构建镜像
```bash
docker build -t blog-backend .
```

### 运行容器
```bash
docker run -d \
  --name blog-backend \
  -p 8000:8000 \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/static:/app/static \
  --env-file .env \
  blog-backend
```

## API 接口文档

### 用户认证

#### 1. 用户注册
```http
POST /api/users/register/
Content-Type: application/json

{
    "username": "testuser",
    "password": "password123",
    "email": "test@example.com"
}
```

响应：
```json
{
    "code": 200,
    "data": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    },
    "message": "注册成功"
}
```

#### 2. 用户登录
```http
POST /api/users/login/
Content-Type: application/json

{
    "username": "admin",
    "password": "password123"
}
```

响应：
```json
{
    "code": 200,
    "data": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    },
    "message": "登录成功"
}
```

#### 3. 刷新令牌
```http
POST /api/users/token/refresh/
Content-Type: application/json

{
    "refresh": "your-refresh-token"
}
```

响应：
```json
{
    "access": "new-access-token"
}
```

#### 4. 退出登录
```http
POST /api/users/logout/
Authorization: Bearer <access_token>
```

响应：
```json
{
    "code": 200,
    "message": "退出登录成功"
}
```

#### 5. 获取用户信息
```http
GET /api/users/info/
Authorization: Bearer <access_token>
```

响应：
```json
{
    "code": 200,
    "data": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "nickname": "管理员",
        "avatar": "http://example.com/avatar.jpg",
        "created_at": "2024-03-20T10:00:00Z"
    },
    "message": "success"
}
```

### 文章管理

#### 1. 获取文章列表
```http
GET /api/articles/?page=1&pageSize=10
Authorization: Bearer <access_token>
```

响应：
```json
{
    "code": 200,
    "data": {
        "count": 100,
        "next": "http://localhost:8000/api/articles/?page=2",
        "previous": null,
        "results": [
            {
                "id": 1,
                "title": "文章标题",
                "content": "文章内容",
                "category": {
                    "id": 1,
                    "name": "分类名称"
                },
                "tags": [
                    {
                        "id": 1,
                        "name": "标签名称"
                    }
                ],
                "created_at": "2024-03-20T10:00:00Z",
                "updated_at": "2024-03-20T10:00:00Z"
            }
        ]
    },
    "message": "success"
}
```

#### 2. 创建文章
```http
POST /api/articles/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "title": "新文章标题",
    "content": "文章内容",
    "category": 1,
    "tags": [1, 2]
}
```

响应：
```json
{
    "code": 200,
    "data": {
        "id": 2,
        "title": "新文章标题",
        "content": "文章内容",
        "category": {
            "id": 1,
            "name": "分类名称"
        },
        "tags": [
            {
                "id": 1,
                "name": "标签1"
            },
            {
                "id": 2,
                "name": "标签2"
            }
        ],
        "created_at": "2024-03-20T10:00:00Z",
        "updated_at": "2024-03-20T10:00:00Z"
    },
    "message": "文章创建成功"
}
```

#### 3. 获取文章详情
```http
GET /api/articles/{id}/
Authorization: Bearer <access_token>
```

响应：
```json
{
    "code": 200,
    "data": {
        "id": 1,
        "title": "文章标题",
        "content": "文章内容",
        "category": {
            "id": 1,
            "name": "分类名称"
        },
        "tags": [
            {
                "id": 1,
                "name": "标签名称"
            }
        ],
        "created_at": "2024-03-20T10:00:00Z",
        "updated_at": "2024-03-20T10:00:00Z"
    },
    "message": "success"
}
```

#### 4. 更新文章
```http
PUT /api/articles/{id}/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "title": "更新后的标题",
    "content": "更新后的内容",
    "category": 2,
    "tags": [1, 3]
}
```

响应：
```json
{
    "code": 200,
    "data": {
        "id": 1,
        "title": "更新后的标题",
        "content": "更新后的内容",
        "category": {
            "id": 2,
            "name": "新分类"
        },
        "tags": [
            {
                "id": 1,
                "name": "标签1"
            },
            {
                "id": 3,
                "name": "标签3"
            }
        ],
        "created_at": "2024-03-20T10:00:00Z",
        "updated_at": "2024-03-20T11:00:00Z"
    },
    "message": "文章更新成功"
}
```

#### 5. 删除文章
```http
DELETE /api/articles/{id}/
Authorization: Bearer <access_token>
```

响应：
```json
{
    "code": 200,
    "message": "文章删除成功"
}
```

### 分类管理

#### 1. 获取分类列表
```http
GET /api/categories/
Authorization: Bearer <access_token>
```

响应：
```json
{
    "code": 200,
    "data": [
        {
            "id": 1,
            "name": "分类名称",
            "description": "分类描述",
            "created_at": "2024-03-20T10:00:00Z"
        }
    ],
    "message": "success"
}
```

#### 2. 创建分类
```http
POST /api/categories/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "name": "新分类",
    "description": "分类描述"
}
```

响应：
```json
{
    "code": 200,
    "data": {
        "id": 2,
        "name": "新分类",
        "description": "分类描述",
        "created_at": "2024-03-20T10:00:00Z"
    },
    "message": "分类创建成功"
}
```

### 标签管理

#### 1. 获取标签列表
```http
GET /api/tags/
Authorization: Bearer <access_token>
```

响应：
```json
{
    "code": 200,
    "data": [
        {
            "id": 1,
            "name": "标签名称",
            "created_at": "2024-03-20T10:00:00Z"
        }
    ],
    "message": "success"
}
```

#### 2. 创建标签
```http
POST /api/tags/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "name": "新标签"
}
```

响应：
```json
{
    "code": 200,
    "data": {
        "id": 2,
        "name": "新标签",
        "created_at": "2024-03-20T10:00:00Z"
    },
    "message": "标签创建成功"
}
```

### 评论系统

#### 1. 获取评论列表
```http
GET /api/comments/?article=1&page=1&pageSize=10
Authorization: Bearer <access_token>
```

响应：
```json
{
    "code": 200,
    "data": {
        "count": 50,
        "next": "http://localhost:8000/api/comments/?article=1&page=2",
        "previous": null,
        "results": [
            {
                "id": 1,
                "content": "评论内容",
                "user": {
                    "id": 1,
                    "username": "user1"
                },
                "article": 1,
                "parent": null,
                "created_at": "2024-03-20T10:00:00Z"
            }
        ]
    },
    "message": "success"
}
```

#### 2. 发表评论
```http
POST /api/comments/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "content": "评论内容",
    "article": 1,
    "parent": null
}
```

响应：
```json
{
    "code": 200,
    "data": {
        "id": 1,
        "content": "评论内容",
        "user": {
            "id": 1,
            "username": "user1"
        },
        "article": 1,
        "parent": null,
        "created_at": "2024-03-20T10:00:00Z"
    },
    "message": "评论成功"
}
```

#### 3. 删除评论
```http
DELETE /api/comments/{id}/
Authorization: Bearer <access_token>
```

响应：
```json
{
    "code": 200,
    "message": "评论删除成功"
}
```

### 文件上传

#### 1. 上传文件
```http
POST /api/upload/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: [文件]
```

响应：
```json
{
    "code": 200,
    "data": {
        "id": 1,
        "name": "文件名.jpg",
        "url": "http://localhost:8000/media/files/文件名.jpg",
        "size": 1024,
        "type": "image/jpeg",
        "created_at": "2024-03-20T10:00:00Z"
    },
    "message": "文件上传成功"
}
```

## 开发团队

- 开发者：[你的名字]
- 联系方式：[你的邮箱]

## 许可证

MIT License 
