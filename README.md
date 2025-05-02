# 开发文档

## 项目简介

本项目为基于 Django + DRF 的多角色内容管理系统，支持用户注册、登录、动态内容管理、评论、标签、分类、文件上传、统计等功能，采用 JWT 认证。

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