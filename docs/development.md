# 开发指南

## 开发环境搭建

### 1. 环境要求
- Python 3.8+
- MySQL 5.7+
- Redis (可选，用于缓存)
- Git

### 2. 开发环境配置

#### 2.1 克隆项目
```bash
git clone [项目地址]
cd blog_li
```

#### 2.2 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

#### 2.3 安装依赖
```bash
pip install -r requirements/dev.txt
```

#### 2.4 配置环境变量
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

#### 2.5 初始化数据库
```bash
python manage.py makemigrations
python manage.py migrate
```

#### 2.6 创建超级用户
```bash
python manage.py createsuperuser
```

#### 2.7 运行开发服务器
```bash
python manage.py runserver
```

## 代码规范

### 1. Python 代码规范
- 遵循 PEP 8 规范
- 使用 Black 进行代码格式化
- 使用 isort 进行导入排序
- 使用 flake8 进行代码检查

### 2. 命名规范
- 类名：使用大驼峰命名法（CamelCase）
- 函数名：使用小写字母和下划线（snake_case）
- 变量名：使用小写字母和下划线（snake_case）
- 常量：使用大写字母和下划线（UPPER_CASE）

### 3. 注释规范
- 使用文档字符串（docstring）说明函数和类的用途
- 使用行内注释说明复杂的代码逻辑
- 保持注释的及时更新

### 4. 代码组织
- 每个应用模块保持独立
- 相关的功能放在同一个模块中
- 避免循环导入
- 使用相对导入

## 提交规范

### 1. Git 提交信息格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

### 2. 类型（type）
- feat: 新功能
- fix: 修复 bug
- docs: 文档更新
- style: 代码格式（不影响代码运行的变动）
- refactor: 重构（既不是新增功能，也不是修改 bug 的代码变动）
- test: 增加测试
- chore: 构建过程或辅助工具的变动

### 3. 范围（scope）
- 影响范围，如：user, article, comment 等

### 4. 主题（subject）
- 简短描述，不超过 50 个字符
- 以动词开头，使用第一人称现在时
- 第一个字母小写
- 结尾不加句号

## 测试规范

### 1. 单元测试
- 每个功能模块都要有对应的单元测试
- 测试覆盖率要求达到 80% 以上
- 使用 pytest 作为测试框架

### 2. 测试文件组织
- 测试文件放在 `tests/unit` 目录下
- 测试文件名以 `test_` 开头
- 测试类名以 `Test` 结尾
- 测试方法名以 `test_` 开头

### 3. 测试用例编写
```python
def test_function_name():
    # 准备测试数据
    # 执行被测试的功能
    # 断言结果
    assert result == expected
```

### 4. 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/test_user.py

# 运行特定测试用例
pytest tests/unit/test_user.py::test_user_login
```

## 开发流程

### 1. 功能开发流程
1. 从主分支创建功能分支
2. 在功能分支上进行开发
3. 编写测试用例
4. 提交代码并推送到远程
5. 创建 Pull Request
6. 代码审查
7. 合并到主分支

### 2. Bug 修复流程
1. 从主分支创建修复分支
2. 在修复分支上修复 bug
3. 编写测试用例
4. 提交代码并推送到远程
5. 创建 Pull Request
6. 代码审查
7. 合并到主分支

### 3. 版本发布流程
1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建发布分支
4. 运行测试
5. 构建发布包
6. 创建 Git 标签
7. 部署到生产环境 