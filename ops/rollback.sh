#!/usr/bin/env bash
#
# 后端回滚：用备份包覆盖远端代码 → 校验 → 重启
#
# 用法：
#   ops/rollback.sh <远端备份包路径> [server]
#   ops/rollback.sh /opt/blog_li-backups/deploy-20260928-101500/code-before-20260928-101500.tgz
set -euo pipefail

ARCHIVE="${1:?用法: ops/rollback.sh <备份包路径> [server]}"
SERVER="${2:-blog-server}"
REMOTE_DIR=/opt/blog_li

echo "==> 1/3 先把当前代码另存一份（回滚也可以再回滚）"
ssh "$SERVER" "set -e; cd '${REMOTE_DIR}'; ts=\$(date +%Y%m%d-%H%M%S); \
  mkdir -p /opt/blog_li-backups/pre-rollback-\$ts; \
  tar czf /opt/blog_li-backups/pre-rollback-\$ts/code.tgz --exclude='__pycache__' blog apps manage.py requirements.txt ops; \
  echo saved /opt/blog_li-backups/pre-rollback-\$ts/code.tgz"

echo "==> 2/3 解包 ${ARCHIVE}"
ssh "$SERVER" "set -e; test -f '${ARCHIVE}'; tar xzf '${ARCHIVE}' -C '${REMOTE_DIR}'; \
  cd '${REMOTE_DIR}' && set -a && . ./.env && set +a && .venv/bin/python manage.py check"

echo "==> 3/3 重启并检查"
ssh "$SERVER" "systemctl restart blog-li && sleep 4 && echo -n 'blog-li: ' && systemctl is-active blog-li; \
  curl -s -o /dev/null -w 'api: %{http_code}\n' -H 'Host: leexd.top' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/api/blog/dynamics/"

echo "回滚完成"
