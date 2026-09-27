#!/usr/bin/env bash
# 后端启动脚本：先分清「依赖缺失」还是「环境变量没配」，再拉起服务。
set -euo pipefail
cd "$(dirname "$0")"

fail() {
  echo "[启动失败] $1" >&2
  exit 1
}

# ---- 1. 环境变量检查（先查环境，再装依赖，报错才能对号入座） ----
if [ -f ../.env ]; then
  set -a
  # shellcheck disable=SC1091
  . ../.env
  set +a
fi
if [ -z "${APP_ENV:-}" ]; then
  fail "环境变量未配置：缺少 APP_ENV。请在仓库根目录执行 cp .env.example .env 后重试（或 export APP_ENV=local）。"
fi

# ---- 2. 依赖检查与安装 ----
command -v python3 >/dev/null 2>&1 || fail "依赖缺失：未找到 python3，请先安装 Python 3.11+。"

# .venv 目录存在不代表可用（比如在别的系统上创建过），要真的跑得起来才算数
if [ ! -x .venv/bin/python ] || ! .venv/bin/python --version >/dev/null 2>&1; then
  echo "[依赖] 未发现可用的 .venv，正在重建…"
  rm -rf .venv
  python3 -m venv .venv 2>/dev/null || python3 -m venv --without-pip .venv \
    || fail "依赖缺失：python3 venv 创建失败，Debian/Ubuntu 请先执行 sudo apt install python3-venv。"
  if [ ! -x .venv/bin/pip ]; then
    .venv/bin/python -m ensurepip -q 2>/dev/null || {
      echo "[依赖] ensurepip 不可用，改用 get-pip 引导…"
      curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py \
        || fail "依赖缺失：无法下载 get-pip.py，请检查网络。"
      .venv/bin/python /tmp/get-pip.py -q || fail "依赖缺失：pip 引导失败。"
    }
  fi
fi

.venv/bin/pip install -q -r requirements.txt \
  || fail "依赖缺失：pip install -r requirements.txt 失败，请检查网络或锁定版本是否仍可用。"

# make install 只装依赖不起服务：./run.sh --install-only
if [ "${1:-}" = "--install-only" ]; then
  echo "[依赖] 后端依赖安装完成。"
  exit 0
fi

# ---- 3. 启动 ----
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}"
