#!/usr/bin/env bash
# 一键本地开发：环境预检 -> 安装锁定依赖 -> 前端构建检查 -> 同时启动前后端。
#   ./dev.sh              完整流程（推荐第一次拉代码后执行）
#   SKIP_BUILD=1 ./dev.sh 跳过前端构建检查，直接起开发服务器
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\033[36m[dev]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[dev][启动失败]\033[0m %s\n' "$*" >&2; exit 1; }

# ---- 0) 基础依赖 ----
command -v python3 >/dev/null 2>&1 || fail "依赖缺失：未找到 python3（要求 3.10+），请先安装 Python。"
command -v node >/dev/null 2>&1 || fail "依赖缺失：未找到 node（要求 Node.js 18+），请先安装 Node.js。"
command -v npm >/dev/null 2>&1 || fail "依赖缺失：未找到 npm，请随 Node.js 一并安装。"
say "python3 $(python3 -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])') / node $(node --version)"

# ---- 1) 环境变量 ----
if [ ! -f .env ]; then
  fail "环境变量没配：仓库根目录缺少 .env。请执行 cp .env.example .env 后重新运行。"
fi
set -a
# shellcheck disable=SC1091
. ./.env
set +a
[ -n "${APP_ENV:-}" ] || fail "环境变量没配：.env 中缺少 APP_ENV。"

# ---- 2) 后端依赖（锁定版本），已能导入则跳过联网安装 ----
if [ ! -x backend/.venv/bin/python ] || ! backend/.venv/bin/python -c 'import sys' >/dev/null 2>&1; then
  say "创建后端虚拟环境 ..."
  rm -rf backend/.venv
  (cd backend && (python3 -m venv .venv || python3 -m virtualenv .venv)) \
    || fail "依赖缺失：无法创建虚拟环境。Debian/Ubuntu 请先 sudo apt-get install python3-venv。"
fi
if ! backend/.venv/bin/python -c 'import fastapi, uvicorn, pydantic' >/dev/null 2>&1; then
  say "同步后端依赖（backend/requirements.lock）..."
  (cd backend && .venv/bin/pip install --disable-pip-version-check -q -r requirements.lock) \
    || fail "依赖缺失：后端依赖安装失败，请检查网络或 pip 源。"
fi

# ---- 3) 前端依赖（package-lock.json 锁定版本，npm ci 严格按锁文件安装） ----
if [ ! -d frontend/node_modules ] || [ ! -f frontend/node_modules/.package-lock.json ]; then
  say "安装前端依赖（frontend/package-lock.json，npm ci）..."
  (cd frontend && npm ci) || fail "依赖缺失：前端 npm ci 失败，请检查网络或 npm 源配置。"
fi

# ---- 4) 构建检查：让"构建失败"在启动前就暴露 ----
if [ "${SKIP_BUILD:-0}" != "1" ]; then
  say "执行前端构建检查（vue-tsc 类型检查 + vite build）..."
  (cd frontend && npm run build) || fail "前端构建未通过，请先修复上面的类型/构建错误。"
  say "前端构建通过。"
fi

# ---- 5) 同时启动前后端 ----
say "启动后端 http://127.0.0.1:${APP_PORT:-8000} 与前端 http://127.0.0.1:5173 ..."
say "停止服务：Ctrl+C。启动后验证派车链路：make check"
(cd backend && ./run.sh) &
BACKEND_PID=$!
(cd frontend && npm run dev) &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
wait -n "$BACKEND_PID" "$FRONTEND_PID"
