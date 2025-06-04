# 开发指南

## 开发环境搭建

### 1. 环境要求
- Python 3.8+
- MySQL 5.7+
- Redis 6.0+ (可选，用于缓存)
- Git 2.30+

### 2. 开发工具
- IDE 推荐：
  - PyCharm Professional/Community
  - Visual Studio Code + Python 插件
  - Sublime Text + Python 插件
- 代码格式化工具：
  - Black 22.3.0+
  - isort 5.10.1+
  - flake8 4.0.1+
- 数据库工具：
  - MySQL Workbench
  - Navicat
  - DBeaver
- API 测试工具：
  - Postman
  - Insomnia

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

# 安装开发工具
pip install black isort flake8 pytest pytest-cov
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

# Redis配置（可选）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password
```

#### 2.5 初始化数据库
```