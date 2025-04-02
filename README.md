# 博客系统后端

本项目是基于Django和Django REST framework开发的博客系统后端。

## 环境要求

- Python 3.8+
- Django 5.1+
- Django REST Framework
- MySQL

## 安装与运行

1. 克隆代码仓库
```
git clone <仓库地址>
```

2. 安装依赖
```
pip install -r requirements.txt
```

3. 配置数据库
在 `blog/settings.py` 中配置数据库连接信息。

4. 执行数据库迁移
```
python manage.py migrate
```

5. 启动服务
```
python manage.py runserver
```

## API 文档

### 基础信息
- 基础路径: `/api`
- 请求方式: REST
- 数据格式: JSON
- 认证方式: Bearer Token

### 认证相关

#### 1. 用户注册
- 接口: `/api/auth/register`
- 方法: POST
- 描述: 用户注册接口
- 请求参数:
```json
{
  "username": "string", // 用户名
  "password": "string", // 密码
  "nickname": "string"  // 昵称
}
```
- 响应数据:
```json
{
  "code": 200,
  "data": {
    "token": "string",      // JWT token
    "userInfo": {
      "id": "number",       // 用户ID
      "username": "string", // 用户名
      "nickname": "string", // 昵称
      "avatar": "string"    // 头像URL
    }
  },
  "message": "string"
}
```

#### 2. 用户登录
- 接口: `/api/auth/login`
- 方法: POST
- 描述: 用户登录接口
- 请求参数:
```json
{
  "username": "string", // 用户名
  "password": "string"  // 密码
}
```
- 响应数据:
```json
{
  "code": 200,
  "data": {
    "token": "string",      // JWT token
    "userInfo": {
      "id": "number",       // 用户ID
      "username": "string", // 用户名
      "nickname": "string", // 昵称
      "avatar": "string"    // 头像URL
    }
  },
  "message": "string"
}
```

#### 3. 获取用户信息
- 接口: `/api/auth/info`
- 方法: GET
- 描述: 获取当前登录用户信息
- 请求头: `Authorization: Bearer {token}`
- 响应数据:
```json
{
  "code": 200,
  "data": {
    "id": "number",
    "username": "string",
    "nickname": "string",
    "avatar": "string"
  },
  "message": "string"
}
```

#### 4. 修改密码
- 接口: `/api/auth/password`
- 方法: PUT
- 描述: 修改用户密码
- 请求头: `Authorization: Bearer {token}`
- 请求参数:
```json
{
  "oldPassword": "string", // 旧密码
  "newPassword": "string"  // 新密码
}
```
- 响应数据:
```json
{
  "code": 200,
  "message": "string"
}
```

### 文章管理

#### 1. 获取文章列表
- 接口: `/api/posts`
- 方法: GET
- 描述: 获取文章列表，支持分页和筛选
- 请求头: `Authorization: Bearer {token}`
- 请求参数:
  - `page`: number (页码，默认1)
  - `pageSize`: number (每页数量，默认10)
  - `keyword`: string (搜索关键词)
  - `categoryId`: number (分类ID)
  - `tagId`: number (标签ID)
  - `status`: string (状态：draft/published)
- 响应数据:
```json
{
  "code": 200,
  "data": {
    "total": "number",
    "items": [{
      "id": "number",
      "title": "string",
      "content": "string",
      "summary": "string",
      "categoryId": "number",
      "categoryName": "string",
      "tags": [{
        "id": "number",
        "name": "string"
      }],
      "status": "string",
      "createTime": "string",
      "updateTime": "string"
    }]
  },
  "message": "string"
}
```

#### 2. 获取文章详情
- 接口: `/api/posts/{id}`
- 方法: GET
- 描述: 获取文章详情
- 请求头: `Authorization: Bearer {token}`
- 响应数据:
```json
{
  "code": 200,
  "data": {
    "id": "number",
    "title": "string",
    "content": "string",
    "summary": "string",
    "categoryId": "number",
    "categoryName": "string",
    "tags": [{
      "id": "number",
      "name": "string"
    }],
    "status": "string",
    "createTime": "string",
    "updateTime": "string"
  },
  "message": "string"
}
```

#### 3. 创建文章
- 接口: `/api/posts`
- 方法: POST
- 描述: 创建新文章
- 请求头: `Authorization: Bearer {token}`
- 请求参数:
```json
{
  "title": "string",      // 文章标题
  "content": "string",    // 文章内容
  "summary": "string",    // 文章摘要
  "categoryId": "number", // 分类ID
  "tagIds": ["number"],   // 标签ID列表
  "status": "string"      // 状态：draft/published
}
```
- 响应数据:
```json
{
  "code": 200,
  "data": {
    "id": "number"
  },
  "message": "string"
}
```

#### 4. 更新文章
- 接口: `/api/posts/{id}`
- 方法: PUT
- 描述: 更新文章信息
- 请求头: `Authorization: Bearer {token}`
- 请求参数:
```json
{
  "title": "string",
  "content": "string",
  "summary": "string",
  "categoryId": "number",
  "tagIds": ["number"],
  "status": "string"
}
```
- 响应数据:
```json
{
  "code": 200,
  "message": "string"
}
```

#### 5. 删除文章
- 接口: `/api/posts/{id}`
- 方法: DELETE
- 描述: 删除文章
- 请求头: `Authorization: Bearer {token}`
- 响应数据:
```json
{
  "code": 200,
  "message": "string"
}
```

### 分类管理

#### 1. 获取分类列表
- 接口: `/api/categories`
- 方法: GET
- 描述: 获取分类列表
- 请求头: `Authorization: Bearer {token}`
- 响应数据:
```json
{
  "code": 200,
  "data": [{
    "id": "number",
    "name": "string",
    "description": "string",
    "createTime": "string",
    "updateTime": "string"
  }],
  "message": "string"
}
```

#### 2. 创建分类
- 接口: `/api/categories`
- 方法: POST
- 描述: 创建新分类
- 请求头: `Authorization: Bearer {token}`
- 请求参数:
```json
{
  "name": "string",        // 分类名称
  "description": "string"  // 分类描述
}
```
- 响应数据:
```json
{
  "code": 200,
  "data": {
    "id": "number"
  },
  "message": "string"
}
```

### 标签管理

#### 1. 获取标签列表
- 接口: `/api/tags`
- 方法: GET
- 描述: 获取标签列表
- 请求头: `Authorization: Bearer {token}`
- 响应数据:
```json
{
  "code": 200,
  "data": [{
    "id": "number",
    "name": "string",
    "createTime": "string",
    "updateTime": "string"
  }],
  "message": "string"
}
```

#### 2. 创建标签
- 接口: `/api/tags`
- 方法: POST
- 描述: 创建新标签
- 请求头: `Authorization: Bearer {token}`
- 请求参数:
```json
{
  "name": "string"  // 标签名称
}
```
- 响应数据:
```json
{
  "code": 200,
  "data": {
    "id": "number"
  },
  "message": "string"
}
```

### 仪表盘统计

#### 1. 获取统计数据
- 接口: `/api/stats`
- 方法: GET
- 描述: 获取博客统计数据，包括文章、分类、标签数量和总浏览量
- 请求头: `Authorization: Bearer {token}`
- 响应数据:
```json
{
  "code": 200,
  "message": "获取统计数据成功",
  "data": {
    "postCount": 24,       // 文章总数
    "categoryCount": 6,    // 分类总数
    "tagCount": 18,        // 标签总数
    "totalViews": 4328     // 总浏览量
  }
}
```

### 前台API接口

前台API接口不需要认证，可直接访问。

#### 1. 获取文章列表
- 接口: `/blog/posts/`
- 方法: GET
- 描述: 获取已发布的文章列表，支持分页和搜索
- 请求参数:
  - `page`: number (页码，默认1)
  - `pageSize`: number (每页数量，默认10)
  - `keyword`: string (搜索关键词)
- 响应数据:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": "number",
    "items": [{
      "id": "number",
      "title": "string",
      "summary": "string",
      "categoryId": "number",
      "categoryName": "string",
      "viewCount": "number",
      "tags": [{
        "id": "number",
        "name": "string"
      }],
      "createTime": "string",
      "updateTime": "string"
    }]
  }
}
```

#### 2. 获取文章详情
- 接口: `/blog/posts/{id}/`
- 方法: GET
- 描述: 获取文章详情
- 响应数据:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "number",
    "title": "string",
    "content": "string",
    "summary": "string",
    "categoryId": "number",
    "categoryName": "string",
    "viewCount": "number",
    "tags": [{
      "id": "number",
      "name": "string"
    }],
    "createTime": "string",
    "updateTime": "string"
  }
}
```

#### 3. 获取相邻文章
- 接口: `/blog/posts/{id}/adjacent/`
- 方法: GET
- 描述: 获取当前文章的上一篇和下一篇
- 响应数据:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "prev": {
      "id": "number",
      "title": "string"
    },
    "next": {
      "id": "number",
      "title": "string"
    }
  }
}
```

#### 4. 增加文章浏览量
- 接口: `/blog/posts/{id}/view/`
- 方法: POST
- 描述: 增加文章浏览量
- 响应数据:
```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

#### 5. 获取最新文章
- 接口: `/blog/posts/recent`
- 方法: GET
- 描述: 获取最新发布的文章列表
- 请求参数:
  - `limit`: number (返回数量，默认5，最大20)
- 响应数据:
```json
{
  "code": 200,
  "message": "success",
  "data": [{
    "id": "number",
    "title": "string",
    "createTime": "string"
  }]
}
```

#### 6. 获取热门文章
- 接口: `/blog/posts/hot`
- 方法: GET
- 描述: 获取浏览量最高的文章列表
- 请求参数:
  - `limit`: number (返回数量，默认5，最大20)
- 响应数据:
```json
{
  "code": 200,
  "message": "success",
  "data": [{
    "id": "number",
    "title": "string",
    "viewCount": "number",
    "createTime": "string"
  }]
}
```

#### 7. 获取分类下的文章
- 接口: `/blog/categories/{categoryId}/posts`
- 方法: GET
- 描述: 获取指定分类下的文章列表
- 请求参数:
  - `page`: number (页码，默认1)
  - `pageSize`: number (每页数量，默认10)
- 响应数据:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": "number",
    "items": [{
      "id": "number",
      "title": "string",
      "summary": "string",
      "categoryId": "number",
      "categoryName": "string",
      "viewCount": "number",
      "tags": [{
        "id": "number",
        "name": "string"
      }],
      "createTime": "string",
      "updateTime": "string"
    }]
  }
}
```

#### 8. 获取标签下的文章
- 接口: `/blog/tags/{tagId}/posts`
- 方法: GET
- 描述: 获取指定标签下的文章列表
- 请求参数:
  - `page`: number (页码，默认1)
  - `pageSize`: number (每页数量，默认10)
- 响应数据:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": "number",
    "items": [{
      "id": "number",
      "title": "string",
      "summary": "string",
      "categoryId": "number",
      "categoryName": "string",
      "viewCount": "number",
      "tags": [{
        "id": "number",
        "name": "string"
      }],
      "createTime": "string",
      "updateTime": "string"
    }]
  }
}
```

#### 9. 获取统计信息
- 接口: `/blog/stats`
- 方法: GET
- 描述: 获取博客统计信息（文章总数、分类总数、标签总数等）
- 响应数据:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "postCount": "number",
    "categoryCount": "number",
    "tagCount": "number",
    "commentCount": "number",
    "viewCount": "number"
  }
}
```

#### 10. 获取分类列表
- 接口: `/api/categories`
- 方法: GET
- 描述: 获取所有分类列表
- 响应数据:
```json
{
  "code": 200,
  "data": [{
    "id": "number",
    "name": "string",
    "description": "string",
    "postCount": "number"
  }],
  "message": "获取分类列表成功"
}
```

#### 11. 获取标签列表
- 接口: `/api/tags`
- 方法: GET
- 描述: 获取所有标签列表
- 响应数据:
```json
{
  "code": 200,
  "data": [{
    "id": "number",
    "name": "string"
  }],
  "message": "获取标签列表成功"
}
```

#### 12. 评论相关接口
- 获取评论列表: `/api/comments` (GET)
- 提交评论: `/api/comments` (POST)
- 响应数据格式与后台API一致

> 注意：前台接口不需要认证，所有用户都可以访问。 