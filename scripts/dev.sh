#!/usr/bin/env bash
# 本地开发一条命令：检查环境 → 装依赖 → 同时拉起前后端。
# 任何一步失败都会指明是「依赖缺失」还是「环境变量未配置」。
set -euo pipefail
cd "$(dirname "$0")/.."

fail() {
  echo "[启动失败] $1" >&2
  exit 1
}

# ---- 1. 工具链检查（依赖缺失类） ----
command -v python3 >/dev/null 2>&1 || fail "依赖缺失：未找到 python3，请安装 Python 3.11+。"
command -v node >/dev/null 2>&1    || fail "依赖缺失：未找到 node，请安装 Node.js 20+。"
command -v npm >/dev/null 2>&1     || fail "依赖缺失：未找到 npm，请安装 Node.js 20+（自带 npm）。"

# ---- 2. 环境变量检查（环境变量类） ----
if [ ! -f .env ]; then
  fail "环境变量未配置：未找到 .env。请执行 cp .env.example .env（或 make env）后重试。"
fi

# ---- 3. 后端：依赖 + 启动（run.sh 内部同样区分依赖/环境变量报错） ----
echo "==> 启动后端（依赖检查 + 灌入示例数据 + uvicorn）"
backend/run.sh &
BACKEND_PID=$!
cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 等后端就绪，确认示例数据可用
echo "==> 等待后端就绪…"
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    wait "$BACKEND_PID" || true
    fail "后端进程已退出，请查看上方日志定位是依赖缺失还是环境变量未配置。"
  fi
  sleep 1
done
curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1 \
  || fail "后端 30 秒内未就绪，请单独执行 make backend 查看详细报错。"

# ---- 4. 前端：按 lockfile 安装 + 启动 dev server ----
echo "==> 安装前端依赖（npm ci，严格按 package-lock.json）"
cd frontend
npm ci --no-audit --no-fund || fail "依赖缺失：npm ci 失败，请检查网络或 package-lock.json。"

echo ""
echo "=================================================="
echo "  后端  http://127.0.0.1:8000  (健康检查 /api/health)"
echo "  前端  http://127.0.0.1:5173  (手动打开，不会自动弹窗)"
echo "  另开一个终端执行 make check 可验证调度创建与派车接口"
echo "=================================================="
echo ""
npm run dev
