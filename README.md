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

#### 1. 用户登录
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

#### 2. 获取用户信息
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

#### 3. 修改密码
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