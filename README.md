# 博客系统后端

本项目是基于 **Django** 和 **Django REST Framework** 开发的博客系统后端，支持用户认证、动态管理、分类管理、标签管理、评论管理以及仪表盘统计功能。

---

## 环境要求

- Python 3.8+
- Django 5.1+
- Django REST Framework
- MySQL

---

## 功能模块

### 1. 用户管理
- 用户注册、登录、获取用户信息、修改密码、更新个人资料。
- 使用 JWT 进行用户认证。

### 2. 动态管理
- 支持动态的增删改查。
- 支持分页、搜索、分类筛选、标签筛选。
- 提供热门动态、最新动态、相邻动态的获取接口。

### 3. 分类管理
- 支持分类的增删改查。
- 获取分类下的动态列表。

### 4. 标签管理
- 支持标签的增删改查。
- 获取标签下的动态列表。

### 5. 评论管理
- 支持评论的增删改查。
- 支持评论的审核（批准/拒绝）。

### 6. 文件上传
- 支持头像上传，验证文件大小和格式。

### 7. 仪表盘统计
- 提供博客统计数据，包括动态总数、分类总数、标签总数和评论总数。
- 提供最近 7 天动态发布趋势。
- 提供分类和标签的动态数量统计。

---

## 安装与运行

### 1. 克隆代码仓库
```bash
git clone <仓库地址>
cd blog_li
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置数据库
在 `blog/settings.py` 中配置数据库连接信息：
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'blog',
        'USER': 'root',
        'PASSWORD': 'your_password',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

### 4. 执行数据库迁移
```bash
python manage.py migrate
```

### 5. 启动开发服务器
```bash
python manage.py runserver
```

### 6. 访问项目
打开浏览器访问 `http://127.0.0.1:8000`。

---

## API 文档

### 基础信息
- **基础路径**: `/api` 和 `/blog`
- **请求方式**: REST
- **数据格式**: JSON
- **认证方式**: Bearer Token

---

### 示例接口

#### 1. 获取动态列表
- **接口**: `/blog/dynamics`
- **方法**: GET
- **请求参数**:
  - `page`: 页码，默认值为 `1`
  - `pageSize`: 每页数量，默认值为 `10`
  - `type`: 可选，动态类型：text/image/audio/video
- **响应数据**:
```json
{
  "code": 200,
  "data": {
    "total": "number",
    "list": [
      {
        "id": "string",
        "content": "string",
        "type": "string",
        "createdAt": "string",
        "images": [
          {
            "url": "string",
            "width": "number",
            "height": "number"
          }
        ],
        "audio": {
          "url": "string",
          "duration": "number"
        },
        "video": {
          "url": "string",
          "cover": "string",
          "duration": "number"
        }
      }
    ]
  },
  "message": "success"
}
```

---

#### 2. 获取动态详情
- **接口**: `/blog/dynamics/{id}`
- **方法**: GET
- **请求参数**:
  - `id`: 动态ID，路径参数
- **响应数据**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "string",
    "content": "string",
    "type": "string",
    "createdAt": "string",
    "images": [
      {
        "url": "string",
        "width": "number",
        "height": "number"
      }
    ],
    "audio": {
      "url": "string",
      "duration": "number"
    },
    "video": {
      "url": "string",
      "cover": "string",
      "duration": "number"
    }
  }
}
```

---

#### 3. 分类动态列表
- **接口**: `/blog/categories/{categoryId}/dynamics`
- **方法**: GET
- **请求参数**:
  - `categoryId`: 分类 ID
  - `page`: 页码，默认值为 `1`
  - `pageSize`: 每页数量，默认值为 `10`
- **响应数据**:
```json
{
  "code": 200,
  "data": {
    "total": "number",
    "items": [
      {
        "id": "number",
        "title": "string",
        "content": "string",
        "author": "object",
        "category": "object",
        "tags": "array",
        "status": "string",
        "views": "number",
        "create_time": "string",
        "update_time": "string"
      }
    ]
  },
  "message": "success"
}
```

---

#### 4. 标签动态列表
- **接口**: `/blog/tags/{tagId}/dynamics`
- **方法**: GET
- **请求参数**:
  - `tagId`: 标签 ID
  - `page`: 页码，默认值为 `1`
  - `pageSize`: 每页数量，默认值为 `10`
- **响应数据**:
```json
{
  "code": 200,
  "data": {
    "total": "number",
    "items": [
      {
        "id": "number",
        "title": "string",
        "content": "string",
        "author": "object",
        "category": "object",
        "tags": "array",
        "status": "string",
        "views": "number",
        "create_time": "string",
        "update_time": "string"
      }
    ]
  },
  "message": "success"
}
```

---

#### 5. 热门动态
- **接口**: `/blog/dynamics/hot`
- **方法**: GET
- **请求参数**:
  - `limit`: 返回的动态数量，默认值为 `5`，最大值为 `20`
- **响应数据**:
```json
{
  "code": 200,
  "data": [
    {
      "id": "number",
      "title": "string",
      "views": "number",
      "create_time": "string"
    }
  ],
  "message": "success"
}
```

---

#### 6. 最近动态
- **接口**: `/blog/dynamics/recent`
- **方法**: GET
- **请求参数**:
  - `limit`: 返回的动态数量，默认值为 `5`，最大值为 `20`
- **响应数据**:
```json
{
  "code": 200,
  "data": [
    {
      "id": "number",
      "title": "string",
      "create_time": "string"
    }
  ],
  "message": "success"
}
```

#### 7. 相邻动态
- **接口**: `/blog/dynamics/{id}/adjacent`
- **方法**: GET
- **响应数据**:
```json
{
  "code": 200,
  "data": {
    "prev": {
      "id": "number",
      "title": "string"
    },
    "next": {
      "id": "number",
      "title": "string"
    }
  },
  "message": "success"
}
```

#### 8. 增加浏览量
- **接口**: `/blog/dynamics/{id}/view`
- **方法**: POST
- **响应数据**:
```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

#### 9. 统计数据
- **接口**: `/blog/stats`
- **方法**: GET
- **响应数据**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": {
      "dynamics": "number",
      "categories": "number",
      "tags": "number",
      "comments": "number"
    },
    "daily": [
      {
        "day": "string",
        "count": "number"
      }
    ],
    "categories": [
      {
        "name": "string",
        "dynamic_count": "number"
      }
    ],
    "tags": [
      {
        "name": "string",
        "dynamic_count": "number"
      }
    ]
  }
}
```

---

## 测试

### 运行测试
```bash
python manage.py test
```

---

## 部署建议

1. **使用 WSGI 服务**: 推荐使用 `gunicorn` 或 `uwsgi` 部署。
2. **静态文件服务**: 配置 Nginx 或其他 Web 服务器提供静态文件服务。
3. **环境变量管理**: 使用 `.env` 文件管理敏感信息（如 `SECRET_KEY`、数据库密码）。
4. **启用 HTTPS**: 配置 SSL 证书，确保数据传输安全。

---

## 项目结构

```
blog_li/
├── apps/                   # 自定义应用
│   ├── category/           # 分类管理模块
│   ├── comment/            # 评论管理模块
│   ├── dashboard/          # 仪表盘统计模块
│   ├── post/               # 文章管理模块
│   ├── tag/                # 标签管理模块
│   ├── upload/             # 文件上传模块
│   └── user/               # 用户管理模块
├── blog/                   # 项目配置
├── templates/              # HTML 模板
├── static/                 # 静态文件
├── manage.py               # Django 管理脚本
├── requirements.txt        # 项目依赖
└── README.md               # 项目说明
```

---

## 贡献

欢迎提交 Issue 或 Pull Request 来改进本项目。

---

## 许可证

本项目基于 MIT 许可证开源。