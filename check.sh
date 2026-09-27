#!/usr/bin/env bash
# 派车链路检查：等待后端就绪后，验证调度创建、指派车辆/司机、发出、抵达接口全部可用。
# 用法：make check   或   ./check.sh
set -euo pipefail
cd "$(dirname "$0")"

BASE_URL="${APP_BASE_URL:-http://127.0.0.1:${APP_PORT:-8000}}"

if [ ! -x backend/.venv/bin/python ]; then
  echo "[check][失败] 依赖缺失：backend/.venv 不存在，请先执行 ./dev.sh 或 make dev。" >&2
  exit 1
fi

echo "[check] 等待后端 $BASE_URL 就绪 ..."
for i in $(seq 1 30); do
  if backend/.venv/bin/python - "$BASE_URL" <<'PY'
import sys, urllib.request, urllib.error
try:
    with urllib.request.urlopen(sys.argv[1] + "/api/health", timeout=2) as resp:
        sys.exit(0 if resp.status == 200 else 1)
except Exception:
    sys.exit(1)
PY
  then
    break
  fi
  sleep 1
  [ "$i" = "30" ] && { echo "[check][失败] 后端 30 秒内未启动，请查看 ./dev.sh 的后端日志。" >&2; exit 1; }
done

exec bash backend/scripts/check.sh "$BASE_URL"
