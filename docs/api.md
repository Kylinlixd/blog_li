# API 文档

基础地址：`http://127.0.0.1:8000`。除登录、注册和 `/blog/` 公共接口外，请求头需包含：

```http
Authorization: Bearer <access_token>
X-Request-ID: <uuid>
```

## 统一响应

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

验证错误使用对应 HTTP 4xx 状态；未处理异常为 500。写请求在五分钟内重复使用同一 `X-Request-ID` 时返回 409。

## 认证

### 登录

```http
POST /api/auth/login/
Content-Type: application/json

{"username":"admin","password":"your-password"}
```

成功响应的 `data` 包含 `access` 与 `refresh`。

### 其他认证接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register/` | 注册 |
| POST | `/api/token/refresh/` | 请求体传 `refresh` |
| POST | `/api/auth/logout/` | 拉黑当前 access token |
| GET | `/api/auth/info/` | 当前用户 |
| PUT | `/api/auth/password/` | `old_password`、`new_password` |
| PUT | `/api/auth/profile/` | 部分更新资料 |

## 内容管理（需登录）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST | `/api/dynamics/` | 列表、创建 |
| GET/PUT/PATCH/DELETE | `/api/dynamics/{id}/` | 详情、更新、删除 |
| GET/POST | `/api/categories/` | 分类列表、创建 |
| PUT/PATCH/DELETE | `/api/categories/{id}/` | 分类更新、删除 |
| GET/POST | `/api/tags/` | 标签列表、创建 |
| PUT/PATCH/DELETE | `/api/tags/{id}/` | 标签更新、删除 |
| GET/POST | `/api/comments/` | 评论列表、创建 |
| PUT | `/api/comments/{id}/approve/` | 审核通过 |
| PUT | `/api/comments/{id}/reject/` | 审核拒绝 |
| GET | `/api/stats/` | 总量、近七天趋势、分类/标签统计 |

内容列表查询支持 `page`、`pageSize`、`title`、`content`、`type`、`status`、`categoryId`、`tagIds` 和 `sort`。

创建/更新内容示例：

```json
{
  "title": "Vue 请求层重构",
  "content": "正文内容",
  "type": "text",
  "status": "published",
  "mediaUrls": [],
  "categoryId": 1,
  "tags": [1, 2]
}
```

## 公开博客

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/blog/dynamics/` | 已发布内容分页 |
| GET | `/blog/dynamics/{id}/` | 已发布内容详情 |
| GET | `/blog/dynamics/hot/?limit=6` | 热门内容，`limit` 为 1–100 |
| GET | `/blog/dynamics/recent/?limit=6` | 最近内容 |
| PUT | `/blog/dynamics/{id}/view/` | 增加阅读量 |
| POST | `/blog/dynamics/{id}/like/` | 按访问 IP 点赞 |
| GET/POST | `/blog/comments/` | `dynamic_id` 查询或提交评论 |
| GET | `/blog/categories/` | 分类及已发布内容数 |
| GET | `/blog/categories/{id}/dynamics/` | 分类内容 |
| GET | `/blog/tags/` | 标签列表 |
| GET | `/blog/tags/{id}/dynamics/` | 标签内容 |
| GET | `/blog/search/?keyword=vue` | 搜索 |

内容分页响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {"total": 1, "items": []}
}
```

## 文件

文件接口以 `/api/upload/` 为前缀且需要登录：

- `POST /api/upload/upload/`：通用文件上传
- `POST /api/upload/avatar/`：头像上传
- `/api/upload/files/`：文件管理
- `/api/upload/categories/`：文件分类
- `/api/upload/tags/`：文件标签
