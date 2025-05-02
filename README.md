# 车辆信息管理系统

## 项目简介
本项目是一个基于Golang和Angular的车辆信息管理系统，支持多角色（管理员、用户、公司）管理，使用JWT进行安全认证。

## 技术栈
- 后端：Golang (Gin/Fiber)
- 前端：Angular
- 数据库：MySQL/PostgreSQL
- 认证：JWT (JSON Web Token)

## 环境要求
- Go 1.20+
- Node.js 16+
- MySQL 5.7+/PostgreSQL 12+
- Angular CLI

## 项目结构
```
.
├── backend/          # Golang后端
├── frontend/         # Angular前端
├── docs/            # 文档
└── README.md        # 项目说明
```

## API接口文档

### 认证相关接口

#### 1. 用户注册
- **接口**：`POST /api/auth/register`
- **描述**：新用户注册
- **请求参数**：
  ```json
  {
    "username": "string",    // 用户名
    "password": "string",    // 密码
    "email": "string",       // 邮箱
    "role": "user|admin|company"  // 角色
  }
  ```
- **响应**：
  ```json
  {
    "code": 200,
    "data": {
      "token": "jwt-token",
      "userInfo": {
        "id": 1,
        "username": "string",
        "email": "string",
        "role": "string"
      }
    },
    "message": "注册成功"
  }
  ```

#### 2. 用户登录
- **接口**：`POST /api/auth/login`
- **描述**：用户登录获取token
- **请求参数**：
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **响应**：
  ```json
  {
    "code": 200,
    "data": {
      "token": "jwt-token",
      "userInfo": {
        "id": 1,
        "username": "string",
        "role": "string"
      }
    },
    "message": "登录成功"
  }
  ```

#### 3. 获取用户信息
- **接口**：`GET /api/auth/info`
- **描述**：获取当前登录用户信息
- **请求头**：`Authorization: Bearer <token>`
- **响应**：
  ```json
  {
    "code": 200,
    "data": {
      "id": 1,
      "username": "string",
      "email": "string",
      "role": "string",
      "permissions": []
    },
    "message": "获取用户信息成功"
  }
  ```

#### 4. 修改密码
- **接口**：`PUT /api/auth/password`
- **描述**：修改当前用户密码
- **请求头**：`Authorization: Bearer <token>`
- **请求参数**：
  ```json
  {
    "old_password": "string",
    "new_password": "string"
  }
  ```
- **响应**：
  ```json
  {
    "code": 200,
    "message": "密码修改成功"
  }
  ```

#### 5. 更新个人资料
- **接口**：`PUT /api/auth/profile`
- **描述**：更新用户个人资料
- **请求头**：`Authorization: Bearer <token>`
- **请求参数**：
  ```json
  {
    "nickname": "string",
    "email": "string",
    "bio": "string"
  }
  ```
- **响应**：
  ```json
  {
    "code": 200,
    "data": {
      "id": 1,
      "username": "string",
      "nickname": "string",
      "email": "string",
      "bio": "string"
    },
    "message": "个人资料更新成功"
  }
  ```

### 公司管理接口

#### 11. 获取公司列表
- **接口**：`GET /api/companies`
- **描述**：获取公司列表（仅管理员可见）
- **请求头**：`Authorization: Bearer <token>`
- **响应**：
  ```json
  {
    "code": 200,
    "data": {
      "total": 10,
      "items": [
        {
          "id": 1,
          "name": "string",
          "address": "string",
          "contact": "string",
          "phone": "string"
        }
      ]
    },
    "message": "获取公司列表成功"
  }
  ```

#### 12. 获取公司详情
- **接口**：`GET /api/companies/{id}`
- **描述**：获取指定公司详细信息
- **请求头**：`Authorization: Bearer <token>`
- **响应**：
  ```json
  {
    "code": 200,
    "data": {
      "id": 1,
      "name": "string",
      "address": "string",
      "contact": "string",
      "phone": "string",
      "vehicles": [
        {
          "id": 1,
          "plate_number": "string",
          "brand": "string",
          "model": "string"
        }
      ]
    },
    "message": "获取公司详情成功"
  }
  ```

### 统计接口

#### 13. 获取统计数据
- **接口**：`GET /api/stats`
- **描述**：获取系统统计数据
- **请求头**：`Authorization: Bearer <token>`
- **响应**：
  ```json
  {
    "code": 200,
    "data": {
      "total_vehicles": 100,
      "total_companies": 10,
      "total_users": 50,
      "recent_vehicles": [
        {
          "id": 1,
          "plate_number": "string",
          "brand": "string",
          "model": "string"
        }
      ]
    },
    "message": "获取统计数据成功"
  }
  ```

## 权限说明
- **管理员**：可以管理所有用户、车辆和公司信息
- **公司**：可以管理本公司下的车辆和用户
- **用户**：只能查看和修改自己的车辆信息

## 错误码说明
- 200：成功
- 400：请求参数错误
- 401：未授权
- 403：权限不足
- 404：资源不存在
- 500：服务器内部错误

## 开发指南

### 后端开发
1. 安装依赖
```bash
cd backend
go mod download
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件配置数据库等信息
```

3. 运行服务
```bash
go run main.go
```

### 前端开发
1. 安装依赖
```bash
cd frontend
npm install
```

2. 运行开发服务器
```bash
ng serve
```

## 部署说明
1. 编译后端
```bash
cd backend
go build -o main
```

2. 编译前端
```bash
cd frontend
ng build --prod
```

3. 配置Nginx
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 安全说明
1. 所有API请求都需要JWT认证（除登录和注册外）
2. 密码使用bcrypt加密存储
3. 敏感信息使用环境变量配置
4. 定期更新JWT密钥
5. 实现请求频率限制
6. 使用HTTPS传输

## 贡献指南
1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证
MIT License 