#!/usr/bin/env bash
#
# 后端部署：备份 → 同步 → 校验 → 跑回归测试 → 重启 → 健康检查
#
# 用法（在仓库根目录执行）：
#   ops/deploy.sh [server]        # server 默认 blog-server（见 ~/.ssh/config）
#
# 说明：
#   - 同步使用 --delete，让远端与仓库保持一致；执行前一定先备份（本脚本会做）
#   - 不同步 .env / .venv / media / .cache / 数据库，避免覆盖服务器上的环境配置
#   - 校验或测试失败会直接中断，不会重启服务
set -euo pipefail

SERVER="${1:-blog-server}"
REMOTE_DIR=/opt/blog_li
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/opt/blog_li-backups/deploy-${STAMP}"

echo "==> 1/6 备份远端代码到 ${BACKUP_DIR}"
ssh "$SERVER" "set -e; mkdir -p '${BACKUP_DIR}'; cd '${REMOTE_DIR}'; \
  tar czf '${BACKUP_DIR}/code-before-${STAMP}.tgz' --exclude='__pycache__' blog apps manage.py requirements.txt ops; \
  ls -lh '${BACKUP_DIR}/code-before-${STAMP}.tgz'"

echo "==> 2/6 同步代码"
rsync -az --delete \
  --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.env' --exclude='.venv' --exclude='media' --exclude='.cache' --exclude='db.sqlite3' \
  blog apps manage.py requirements.txt ops \
  "${SERVER}:${REMOTE_DIR}/"

echo "==> 3/6 远端 Django 检查"
ssh "$SERVER" "cd '${REMOTE_DIR}' && set -a && . ./.env && set +a && .venv/bin/python manage.py check"

echo "==> 4/6 远端回归测试"
ssh "$SERVER" "cd '${REMOTE_DIR}' && set -a && . ./.env && set +a && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py test apps.dynamic.tests_audit_fixes 2>&1 | tail -4"

echo "==> 5/6 重启服务"
ssh "$SERVER" "systemctl restart blog-li && sleep 4 && echo -n 'blog-li: ' && systemctl is-active blog-li"

echo "==> 6/6 健康检查（服务器本地）"
ssh "$SERVER" "curl -s -o /dev/null -w 'api: %{http_code}\n' -H 'Host: leexd.top' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/api/blog/dynamics/; curl -s -o /dev/null -w 'search: %{http_code}\n' -H 'Host: leexd.top' -H 'X-Forwarded-Proto: https' 'http://127.0.0.1:8000/api/blog/search/?keyword=blog&pageSize=1'"

echo
echo "部署完成。回滚命令："
echo "  ops/rollback.sh ${BACKUP_DIR}/code-before-${STAMP}.tgz ${SERVER}"
