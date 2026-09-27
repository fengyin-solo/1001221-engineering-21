"""运行配置：端口、跨域、运行环境。

配置全部来自环境变量，APP_ENV 必填且不设默认值——本地开发时由仓库根目录的
.env 提供；没配就直接报错并说明怎么配，避免起了一个"看似可用、其实是别的
环境"的服务。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


class ConfigError(RuntimeError):
    """缺少必要环境变量或取值非法时抛出，由 run.sh / 启动入口转成可读提示。"""


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"缺少必要环境变量 {name}。请在仓库根目录复制 .env.example 为 .env"
            f"（cp .env.example .env）后重新启动；或先执行 export {name}=local。"
        )
    return value


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {name} 必须是整数端口号，当前值：{raw!r}") from exc


def _origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if not raw:
        return ["http://127.0.0.1:5173", "http://localhost:5173"]
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str
    env: str
    port: int
    host: str = "127.0.0.1"
    allowed_origins: list[str] = field(default_factory=_origins)
    page_size_default: int = 20
    page_size_max: int = 200


def load_settings() -> Settings:
    return Settings(
        app_name=os.environ.get("APP_NAME", "冷链物流运输管理平台").strip() or "冷链物流运输管理平台",
        env=_required_env("APP_ENV"),
        port=_int_env("APP_PORT", 8000),
    )


settings = load_settings()
