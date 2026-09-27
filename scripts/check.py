#!/usr/bin/env python3
"""运力调度链路检查入口：确认服务在跑、示例数据已灌入、调度创建与指派车辆接口都能返回。

用法：
    python3 scripts/check.py            # 默认打 http://127.0.0.1:8000
    BASE_URL=http://127.0.0.1:8000 python3 scripts/check.py

退出码：全部通过为 0，任何一步失败为 1。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

FAILURES: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - 检查脚本要把所有失败原因打出来
        FAILURES.append(f"✗ {name}：{exc}")
        print(FAILURES[-1])
    else:
        print(f"✓ {name}")


def request(path: str, *, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_health() -> None:
    payload = request("/api/health")
    assert payload.get("ok"), f"健康检查返回异常：{payload}"


def check_seed_chain() -> None:
    """启动后应已自动灌入 待调度→已调度→运输中→已抵达 的完整链路。"""
    payload = request("/api/dispatch3?size=200")
    statuses = {row.get("status") for row in payload.get("items", [])}
    missing = {"待调度", "已调度", "运输中", "已抵达"} - statuses
    assert not missing, f"示例数据缺少状态：{'、'.join(sorted(missing))}"


def check_create_dispatch() -> None:
    """调度创建接口：登记一条待调度任务。"""
    payload = request(
        "/api/dispatch3",
        method="POST",
        body={"values": {"调度编号": "DISP-CHECK", "关联委托": "ORDE-0001", "指派车辆": "沪A·D8301"}},
    )
    assert payload.get("ok"), f"调度创建失败：{payload.get('message')}"
    entry = payload.get("entry") or {}
    check_create_dispatch.entry_id = entry.get("id")
    assert check_create_dispatch.entry_id, "创建成功但未返回 entry.id"


def check_assign_vehicle() -> None:
    """指派车辆链路：对刚创建的任务执行「指派调度」。"""
    entry_id = getattr(check_create_dispatch, "entry_id", None)
    assert entry_id, "上一步未创建调度任务，无法执行指派"
    payload = request(
        f"/api/dispatch3/{entry_id}/actions",
        method="POST",
        body={"values": {"action": "指派调度"}},
    )
    assert payload.get("ok"), f"指派调度失败：{payload.get('message')}"
    assert (payload.get("entry") or {}).get("status") == "已调度", "指派后状态未流转为已调度"


def check_frontend_proxy_hint() -> None:
    """列表接口按状态过滤也要能返回（前端页面走的同一路径）。"""
    query = urllib.parse.urlencode({"status": "已抵达"})
    payload = request(f"/api/dispatch3?{query}")
    assert payload.get("total", 0) >= 1, "按状态过滤已抵达任务无结果"


def main() -> int:
    print(f"检查目标：{BASE_URL}\n")
    check("健康检查 /api/health", check_health)
    check("示例数据覆盖完整调度链路", check_seed_chain)
    check("调度创建接口 POST /api/dispatch3", check_create_dispatch)
    check("指派车辆动作 POST /api/dispatch3/{id}/actions", check_assign_vehicle)
    check("调度列表按状态过滤", check_frontend_proxy_hint)
    print()
    if FAILURES:
        print(f"共 {len(FAILURES)} 项未通过。")
        return 1
    print("全部通过：调度创建与指派车辆接口均可正常返回。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
