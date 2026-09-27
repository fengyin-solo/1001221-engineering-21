"""冷链物流运输管理平台 后端服务入口。

启动：uvicorn app.main:app --host 127.0.0.1 --port 8000
健康检查：GET /api/health
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import ROUTERS
from app.store import store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("dispatch")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 每次启动都重置内存仓库，保证从待派车到已完成的示例链路一定存在
    store.reset()
    dispatch_rows = store.rows("dispatch3")
    chain = "、".join(
        f"{row.get('调度编号')}({row.get('status')})" for row in dispatch_rows
    )
    logger.info("[env=%s] 示例数据已灌入：%d 个模块；派车链路：%s",
                settings.env, len(store.module_names()), chain)
    yield


app = FastAPI(title="冷链物流运输管理平台", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in ROUTERS:
    app.include_router(module.router)


@app.get("/api/health")
def health() -> dict[str, object]:
    """健康检查：确认服务已经监听、示例数据已经就绪。"""
    return {"ok": True, "app": settings.app_name, "env": settings.env,
            "modules": len(store.module_names())}


@app.get("/api/overview")
def overview() -> dict[str, object]:
    """运营概览：把各业务模块的待处理量汇总成看板卡片。"""
    return store.overview()


@app.post("/api/dev/reset")
def reset_seed() -> dict[str, object]:
    """把内存数据恢复成启动时的示例数据，方便反复演练派车链路（仅本地开发使用）。"""
    store.reset()
    return {"ok": True, "message": "示例数据已重置为初始状态"}
