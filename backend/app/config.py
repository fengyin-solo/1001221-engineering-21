"""运行配置：端口、跨域、运行环境。

环境变量从仓库根目录的 .env 读取（不存在时退回进程环境）。
APP_ENV 是必填项：缺失时直接拒绝启动，并说明是环境变量没配，
避免服务以半配置状态跑起来。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]

# 依次尝试仓库根目录与当前工作目录，找到第一个 .env 就停
for _candidate in (REPO_ROOT / ".env", Path.cwd() / ".env"):
    if _candidate.is_file():
        load_dotenv(_candidate)
        break

VALID_ENVS = {"local", "dev", "test", "prod"}


def _require_app_env() -> str:
    value = os.environ.get("APP_ENV", "").strip()
    if not value:
        raise RuntimeError(
            "环境变量未配置：缺少 APP_ENV。"
            "请在仓库根目录执行 cp .env.example .env（或 export APP_ENV=local）后重新启动。"
        )
    if value not in VALID_ENVS:
        raise RuntimeError(
            f"环境变量配置有误：APP_ENV={value!r} 不在允许值 {sorted(VALID_ENVS)} 内，请检查 .env。"
        )
    return value


@dataclass(frozen=True)
class Settings:
    app_name: str = "冷链物流运输管理平台"
    env: str = field(default_factory=_require_app_env)
    port: int = 8000
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
    )
    page_size_default: int = 20
    page_size_max: int = 200


settings = Settings()
