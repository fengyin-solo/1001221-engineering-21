#!/usr/bin/env bash
# 后端一键启动：环境预检 -> 准备虚拟环境 -> 安装锁定依赖 -> 灌入示例数据并启动。
# 任何一步失败都会明确指出是「依赖缺失」还是「环境变量没配」，而不是抛一串堆栈。
set -euo pipefail

cd "$(dirname "$0")"
ROOT_DIR="$(cd .. && pwd)"

say() { printf '\033[36m[run]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[run][启动失败]\033[0m %s\n' "$*" >&2; exit 1; }

# ---- 1) 环境变量：优先沿用当前 shell，其次读仓库根目录 .env ----
if [ -z "${APP_ENV:-}" ] && [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT_DIR/.env"
  set +a
fi
if [ -z "${APP_ENV:-}" ]; then
  fail "环境变量没配：缺少 APP_ENV。
        请执行：cp $ROOT_DIR/.env.example $ROOT_DIR/.env
        然后重新运行本脚本；或临时执行 export APP_ENV=local"
fi
APP_PORT="${APP_PORT:-8000}"
APP_HOST="${APP_HOST:-127.0.0.1}"

# ---- 2) 基础依赖：必须有 Python 3 ----
if ! command -v python3 >/dev/null 2>&1; then
  fail "依赖缺失：未找到 python3（要求 Python 3.10+）。请先安装 Python 后重试。"
fi
PY_VER="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
say "使用系统 Python $PY_VER"

# ---- 3) 虚拟环境：坏软链（换机器克隆）会被识别并重建 ----
if [ ! -x .venv/bin/python ] || ! .venv/bin/python -c 'import sys' >/dev/null 2>&1; then
  say "未发现可用虚拟环境，开始创建 .venv ..."
  rm -rf .venv
  if python3 -m venv .venv >/tmp/venv-create.log 2>&1; then
    :
  elif python3 -m virtualenv .venv >>/tmp/venv-create.log 2>&1; then
    :
  else
    fail "依赖缺失：创建虚拟环境失败（venv 模块不可用）。
        Debian/Ubuntu 请执行：sudo apt-get install python3-venv
        或先安装 virtualenv：python3 -m pip install --user virtualenv
        详细日志见 /tmp/venv-create.log"
  fi
fi

# ---- 4) 安装锁定依赖（requirements.lock 锁定全部传递依赖） ----
# 依赖已能导入则默认跳过联网安装；需要强制同步时设置 FORCE_PIP_INSTALL=1
if [ "${FORCE_PIP_INSTALL:-0}" = "1" ] || ! .venv/bin/python -c "import fastapi, uvicorn, pydantic" >/dev/null 2>&1; then
  say "安装锁定依赖（requirements.lock）..."
  .venv/bin/pip install --disable-pip-version-check -q -r requirements.lock \
    || fail "依赖缺失：pip 安装依赖失败，请检查网络或 pip 源配置后重试。"
fi
if ! .venv/bin/python -c "import fastapi, uvicorn, pydantic" >/dev/null 2>&1; then
  fail "依赖缺失：fastapi / uvicorn / pydantic 未能导入，虚拟环境可能已损坏，请删除 .venv 后重试。"
fi

# ---- 5) 配置自检：由 config.py 统一校验，失败信息直接透传 ----
.venv/bin/python -c "from app.config import settings" 2>/tmp/config-check.log \
  || fail "$(sed 's/^/        /' /tmp/config-check.log | tail -n 1)"

say "环境：APP_ENV=$APP_ENV，监听 $APP_HOST:$APP_PORT"
say "示例数据将在启动时自动灌入（待调度 → 已调度 → 运输中 → 已抵达）"
say "启动后检查入口：bash scripts/check.sh    或    .venv/bin/python scripts/check_dispatch.py"

exec .venv/bin/uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
