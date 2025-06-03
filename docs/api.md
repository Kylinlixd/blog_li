# API 文档

## 通用说明

### 1. 基础信息
- 基础URL: `http://your-domain.com/api`
- 所有请求和响应均使用 JSON 格式
- 时间格式: ISO 8601 (YYYY-MM-DDTHH:mm:ssZ)

### 2. 认证方式
- 使用 JWT (JSON Web Token) 认证
- 在请求头中添加 `Authorization: Bearer <token>`
- Token 有效期为 15 分钟
- 支持 Token 刷新

### 3. 响应格式
```json
{
    "code": 200,           // 状态码
    "data": {},           // 响应数据
    "message": "success"  // 响应消息
}
```

### 4. 错误码说明
- 200: 成功
- 400: 请求参数错误
- 401: 未认证
- 403: 无权限
- 404: 资源不存在
- 500: 服务器错误

### 5. 分页参数
- page: 页码（从1开始）
- pageSize: 每页数量
- 响应格式：
```json
{
    "code": 200,
    "data": {
        "count": 100,      // 总数量
        "next": "下一页URL",
        "previous": "上一页URL",
        "results": []      // 数据列表
    },
    "message": "success"
}
```

## 用户认证

### 1. 用户注册
```http
POST /users/register/

请求体：
{
    "username": "string",     // 用户名
    "password": "string",     // 密码
    "email": "string",        // 邮箱
    "nickname": "string"      // 昵称（可选）
}

响应：
{
    "code": 200,
    "data": {
        "access": "string",   // 访问令牌
        "refresh": "string"   // 刷新令牌
    },
    "message": "注册成功"
}
```

### 2. 用户登录
```http
POST /users/login/

请求体：
{
    "username": "string",     // 用户名
    "password": "string"      // 密码
}

响应：
{
    "code": 200,
    "data": {
        "access": "string",   // 访问令牌
        "refresh": "string"   // 刷新令牌
    },
    "message": "登录成功"
}
```

### 3. 刷新令牌
```http
POST /users/token/refresh/

请求体：
{
    "refresh": "string"       // 刷新令牌
}

响应：
{
    "access": "string"        // 新的访问令牌
}
```

### 4. 退出登录
```http
POST /users/logout/

请求头：
Authorization: Bearer <token>

响应：
{
    "code": 200,
    "message": "退出登录成功"
}
```

### 5. 获取用户信息
```http
GET /users/info/

请求头：
Authorization: Bearer <token>

响应：
{
    "code": 200,
    "data": {
        "id": 1,
        "username": "string",
        "email": "string",
        "nickname": "string",
        "avatar": "string",
        "created_at": "string"
    },
    "message": "success"
}
```

## 文章管理

### 1. 获取文章列表
```http
GET /articles/

请求参数：
- page: 页码
- pageSize: 每页数量
- category: 分类ID（可选）
- tag: 标签ID（可选）
- search: 搜索关键词（可选）
- sort: 排序字段（可选，如：created_at, updated_at）

响应：
{
    "code": 200,
    "data": {
        "count": 100,
        "next": "string",
        "previous": "string",
        "results": [
            {
                "id": 1,
                "title": "string",
                "content": "string",
                "category": {
                    "id": 1,
                    "name": "string"
                },
                "tags": [
                    {
                        "id": 1,
                        "name": "string"
                    }
                ],
                "created_at": "string",
                "updated_at": "string"
            }
        ]
    },
    "message": "success"
}
```

### 2. 创建文章
```http
POST /articles/

请求头：
Authorization: Bearer <token>

请求体：
{
    "title": "string",        // 标题
    "content": "string",      // 内容
    "category": 1,            // 分类ID
    "tags": [1, 2]           // 标签ID列表
}

响应：
{
    "code": 200,
    "data": {
        "id": 1,
        "title": "string",
        "content": "string",
        "category": {
            "id": 1,
            "name": "string"
        },
        "tags": [
            {
                "id": 1,
                "name": "string"
            }
        ],
        "created_at": "string",
        "updated_at": "string"
    },
    "message": "文章创建成功"
}
```

### 3. 获取文章详情
```http
GET /articles/{id}/

响应：
{
    "code": 200,
    "data": {
        "id": 1,
        "title": "string",
        "content": "string",
        "category": {
            "id": 1,
            "name": "string"
        },
        "tags": [
            {
                "id": 1,
                "name": "string"
            }
        ],
        "created_at": "string",
        "updated_at": "string"
    },
    "message": "success"
}
```

### 4. 更新文章
```http
PUT /articles/{id}/

请求头：
Authorization: Bearer <token>

请求体：
{
    "title": "string",        // 标题
    "content": "string",      // 内容
    "category": 1,            // 分类ID
    "tags": [1, 2]           // 标签ID列表
}

响应：
{
    "code": 200,
    "data": {
        "id": 1,
        "title": "string",
        "content": "string",
        "category": {
            "id": 1,
            "name": "string"
        },
        "tags": [
            {
                "id": 1,
                "name": "string"
            }
        ],
        "created_at": "string",
        "updated_at": "string"
    },
    "message": "文章更新成功"
}
```

### 5. 删除文章
```http
DELETE /articles/{id}/

请求头：
Authorization: Bearer <token>

响应：
{
    "code": 200,
    "message": "文章删除成功"
}
```

## 分类管理

### 1. 获取分类列表
```http
GET /categories/

响应：
{
    "code": 200,
    "data": [
        {
            "id": 1,
            "name": "string",
            "description": "string",
            "created_at": "string"
        }
    ],
    "message": "success"
}
```

### 2. 创建分类
```http
POST /categories/

请求头：
Authorization: Bearer <token>

请求体：
{
    "name": "string",         // 分类名称
    "description": "string"   // 分类描述
}

响应：
{
    "code": 200,
    "data": {
        "id": 1,
        "name": "string",
        "description": "string",
        "created_at": "string"
    },
    "message": "分类创建成功"
}
```

## 标签管理

### 1. 获取标签列表
```http
GET /tags/

响应：
{
    "code": 200,
    "data": [
        {
            "id": 1,
            "name": "string",
            "created_at": "string"
        }
    ],
    "message": "success"
}
```

### 2. 创建标签
```http
POST /tags/

请求头：
Authorization: Bearer <token>

请求体：
{
    "name": "string"          // 标签名称
}

响应：
{
    "code": 200,
    "data": {
        "id": 1,
        "name": "string",
        "created_at": "string"
    },
    "message": "标签创建成功"
}
```

## 评论系统

### 1. 获取评论列表
```http
GET /comments/

请求参数：
- article: 文章ID
- page: 页码
- pageSize: 每页数量

响应：
{
    "code": 200,
    "data": {
        "count": 100,
        "next": "string",
        "previous": "string",
        "results": [
            {
                "id": 1,
                "content": "string",
                "user": {
                    "id": 1,
                    "username": "string"
                },
                "article": 1,
                "parent": null,
                "created_at": "string"
            }
        ]
    },
    "message": "success"
}
```

### 2. 发表评论
```http
POST /comments/

请求头：
Authorization: Bearer <token>

请求体：
{
    "content": "string",      // 评论内容
    "article": 1,            // 文章ID
    "parent": null           // 父评论ID（可选）
}

响应：
{
    "code": 200,
    "data": {
        "id": 1,
        "content": "string",
        "user": {
            "id": 1,
            "username": "string"
        },
        "article": 1,
        "parent": null,
        "created_at": "string"
    },
    "message": "评论成功"
}
```

### 3. 删除评论
```http
DELETE /comments/{id}/

请求头：
Authorization: Bearer <token>

响应：
{
    "code": 200,
    "message": "评论删除成功"
}
```

## 文件上传

### 1. 上传文件
```http
POST /upload/

请求头：
Authorization: Bearer <token>
Content-Type: multipart/form-data

请求体：
file: [文件]

响应：
{
    "code": 200,
    "data": {
        "id": 1,
        "name": "string",
        "url": "string",
        "size": 1024,
        "type": "string",
        "created_at": "string"
    },
    "message": "文件上传成功"
}
```

## 动态管理

### 1. 获取动态列表
```http
GET /dynamics/

请求参数：
- page: 页码
- pageSize: 每页数量
- type: 动态类型（可选）
- status: 状态（可选）
- search: 搜索关键词（可选）
- sort: 排序字段（可选）

响应：
{
    "code": 200,
    "data": {
        "count": 100,
        "next": "string",
        "previous": "string",
        "results": [
            {
                "id": 1,
                "title": "string",
                "content": "string",
                "type": "string",
                "status": "string",
                "created_at": "string",
                "updated_at": "string"
            }
        ]
    },
    "message": "success"
}
```

### 2. 创建动态
```http
POST /dynamics/

请求头：
Authorization: Bearer <token>

请求体：
{
    "title": "string",        // 标题
    "content": "string",      // 内容
    "type": "string",         // 类型
    "status": "string"        // 状态
}

响应：
{
    "code": 200,
    "data": {
        "id": 1,
        "title": "string",
        "content": "string",
        "type": "string",
        "status": "string",
        "created_at": "string",
        "updated_at": "string"
    },
    "message": "动态创建成功"
}
```

### 3. 更新动态
```http
PUT /dynamics/{id}/

请求头：
Authorization: Bearer <token>

请求体：
{
    "title": "string",        // 标题
    "content": "string",      // 内容
    "type": "string",         // 类型
    "status": "string"        // 状态
}

响应：
{
    "code": 200,
    "data": {
        "id": 1,
        "title": "string",
        "content": "string",
        "type": "string",
        "status": "string",
        "created_at": "string",
        "updated_at": "string"
    },
    "message": "动态更新成功"
}
```

### 4. 删除动态
```http
DELETE /dynamics/{id}/

请求头：
Authorization: Bearer <token>

响应：
{
    "code": 200,
    "message": "动态删除成功"
}
``` 