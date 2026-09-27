#!/usr/bin/env bash
# 派车链路检查入口：健康检查 + 调度创建 + 指派车辆/司机 + 发出 + 抵达，全绿才算通过。
# 用法（在 backend 目录）：bash scripts/check.sh [base_url]
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
  echo "[check][失败] 依赖缺失：未找到 .venv，请先执行 ./run.sh（会自动创建虚拟环境并安装依赖）。" >&2
  exit 1
fi

BASE_URL="${1:-${APP_BASE_URL:-http://127.0.0.1:${APP_PORT:-8000}}}"
exec .venv/bin/python scripts/check_dispatch.py --base-url "$BASE_URL"
