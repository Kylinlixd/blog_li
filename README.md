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

### 用户注册
- **POST** `/api/auth/register/`
- **参数**：
  ```json
  {
    "username": "string",
    "password": "string",
    "email": "string",
    "role": "user|admin|company"
  }
  ```
- **返回**：
  ```json
  {
    "code": 200,
    "data": {
      "token": "jwt-token",
      "userInfo": { ... }
    },
    "message": "注册成功"
  }
  ```

### 用户登录
- **POST** `/api/auth/login/`
- **参数**：
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **返回**：
  ```json
  {
    "code": 200,
    "data": {
      "token": "jwt-token",
      "userInfo": { ... }
    },
    "message": "登录成功"
  }
  ```

### 获取当前用户信息
- **GET** `/api/auth/info/`
- **Header**: `Authorization: Bearer <token>`
- **返回**：
  ```json
  {
    "code": 200,
    "data": { ... },
    "message": "获取用户信息成功"
  }
  ```

### 修改密码
- **PUT** `/api/auth/password/`
- **参数**：
  ```json
  {
    "old_password": "string",
    "new_password": "string"
  }
  ```
- **返回**：
  ```json
  {
    "code": 200,
    "message": "密码修改成功"
  }
  ```

### 修改个人资料
- **PUT** `/api/auth/profile/`
- **参数**：部分或全部用户信息字段
- **返回**：
  ```json
  {
    "code": 200,
    "data": { ... },
    "message": "个人资料更新成功"
  }
  ```

### 刷新Token
- **POST** `/api/token/refresh/`
- **参数**：
  ```json
  {
    "refresh": "refresh-token"
  }
  ```
- **返回**：
  ```json
  {
    "access": "new-access-token"
  }
  ```

---

## 动态内容接口

### 动态列表/详情/增删改
- **GET** `/api/dynamics/` 获取动态列表
- **POST** `/api/dynamics/` 创建动态
- **GET** `/api/dynamics/{id}/` 获取动态详情
- **PUT** `/api/dynamics/{id}/` 更新动态
- **DELETE** `/api/dynamics/{id}/` 删除动态

### 动态扩展接口
- **GET** `/api/dynamics/{id}/adjacent/` 获取相邻动态
- **POST** `/api/dynamics/{id}/view/` 增加浏览量

### 前台热门/最新动态
- **GET** `/blog/dynamics/hot/` 热门动态
- **GET** `/blog/dynamics/recent/` 最新动态

---

## 分类与标签接口

### 分类
- **GET** `/api/categories/` 分类列表
- **POST** `/api/categories/` 创建分类
- **GET** `/api/categories/{id}/` 分类详情
- **PUT** `/api/categories/{id}/` 更新分类
- **DELETE** `/api/categories/{id}/` 删除分类
- **GET** `/blog/categories/` 前台分类列表

### 标签
- **GET** `/api/tags/` 标签列表
- **POST** `/api/tags/` 创建标签
- **GET** `/api/tags/{id}/` 标签详情
- **PUT** `/api/tags/{id}/` 更新标签
- **DELETE** `/api/tags/{id}/` 删除标签

---

## 评论接口

- **GET** `/api/comments/` 评论列表
- **POST** `/api/comments/` 创建评论
- **GET** `/api/comments/{id}/` 评论详情
- **PUT** `/api/comments/{id}/` 更新评论
- **DELETE** `/api/comments/{id}/` 删除评论
- **PUT** `/api/comments/{id}/approve/` 审核通过
- **PUT** `/api/comments/{id}/reject/` 审核拒绝

---

## 文件上传

- **POST** `/api/upload/file/` 文件上传

---

## 仪表盘统计

- **GET** `/api/stats/` 统计数据

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