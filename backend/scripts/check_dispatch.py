#!/usr/bin/env python3
"""派车链路检查入口：启动后跑一遍，确认「创建调度 → 指派车辆/司机 → 发出 → 抵达」整条链路可用。

用法（在 backend 目录下）：
    .venv/bin/python scripts/check_dispatch.py
    .venv/bin/python scripts/check_dispatch.py --base-url http://127.0.0.1:8000

全部通过退出码为 0；任何一步不通过退出码为 1 并打印原因。
只依赖标准库，不需要额外安装测试框架。
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
ORDER_CODE = "ORDE-0001"  # 种子数据里「已接收待派车」的委托
DISPATCH_CODE = "DISP-CHECK-0001"

passed = 0
failed = 0


def report(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    mark = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
        print(f"  [{mark}] {name}")
    else:
        failed += 1
        print(f"  [{mark}] {name} -- {detail}")


def request(base_url: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"_raw": raw}
    except urllib.error.URLError as exc:
        print(f"\n连不上后端 {base_url}：{exc.reason}")
        print("请先在 backend 目录执行 ./run.sh 把服务启动，再运行本检查脚本。")
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="检查派车链路接口是否可用")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="后端地址，默认 %(default)s")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"== 派车链路检查（{base}） ==")

    # 0) 健康检查
    status, health = request(base, "GET", "/api/health")
    report("健康检查 GET /api/health 返回 200",
           status == 200 and health.get("ok") is True,
           f"HTTP {status}: {health}")

    # 每次检查前重置，保证能稳定复现；检查完再恢复，避免污染页面上的示例数据
    request(base, "POST", "/api/dev/reset")

    # 1) 从种子数据里挑空闲车辆与空闲司机（模拟调度员选车选人）
    _, fleet_page = request(base, "GET", "/api/fleet?status=%E7%A9%BA%E9%97%B2")
    _, driver_page = request(base, "GET", "/api/driver?status=%E7%A9%BA%E9%97%B2")
    idle_vehicles = fleet_page.get("items", [])
    idle_drivers = driver_page.get("items", [])
    report("种子数据中存在空闲车辆与空闲司机",
           bool(idle_vehicles) and bool(idle_drivers),
           f"空闲车辆 {len(idle_vehicles)} 台、空闲司机 {len(idle_drivers)} 名")
    if not idle_vehicles or not idle_drivers:
        return finish(skip_reset=False, base=base)

    vehicle_code = idle_vehicles[0]["车辆编号"]
    driver_code = idle_drivers[0]["驾驶员编号"]

    # 2) 创建调度（调度创建接口）
    status, created = request(base, "POST", "/api/dispatch3", {
        "values": {
            "调度编号": DISPATCH_CODE,
            "关联委托": ORDER_CODE,
            "计划发出": "2026-09-27 06:00",
            "预计到达": "2026-09-27 10:30",
        }
    })
    create_ok = (
        status == 200
        and created.get("ok") is True
        and (created.get("entry") or {}).get("status") == "待调度"
    )
    report(f"调度创建接口 POST /api/dispatch3（{DISPATCH_CODE} → 待调度）",
           create_ok, f"HTTP {status}: {created}")
    if not create_ok:
        return finish(skip_reset=False, base=base)
    entry_id = created["entry"]["id"]

    # 3) 指派车辆 + 指派司机（指派接口，同一步完成资源占用）
    status, assigned = request(base, "POST", f"/api/dispatch3/{entry_id}/actions", {
        "values": {
            "action": "指派调度",
            "指派车辆": vehicle_code,
            "指派司机": driver_code,
            "调度人员": "检查脚本",
        }
    })
    assign_entry = assigned.get("entry") or {}
    assign_ok = (
        status == 200
        and assigned.get("ok") is True
        and assign_entry.get("status") == "已调度"
        and assign_entry.get("指派车辆") == vehicle_code
        and assign_entry.get("指派司机") == driver_code
    )
    report(f"指派车辆/司机接口（{vehicle_code} + {driver_code} → 已调度）",
           assign_ok, f"HTTP {status}: {assigned}")

    # 指派后车辆/司机应被占用为出车中
    _, fleet_after = request(base, "GET", f"/api/fleet?keyword={vehicle_code}")
    _, driver_after = request(base, "GET", f"/api/driver?keyword={driver_code}")
    vehicle_used = next(
        (r for r in fleet_after.get("items", []) if r.get("车辆编号") == vehicle_code), {}
    )
    driver_used = next(
        (r for r in driver_after.get("items", []) if r.get("驾驶员编号") == driver_code), {}
    )
    report("指派后车辆与司机状态变为「出车中」",
           vehicle_used.get("status") == "出车中" and driver_used.get("status") == "出车中",
           f"车辆={vehicle_used.get('status')}，司机={driver_used.get('status')}")

    # 4) 确认发出
    status, departed = request(base, "POST", f"/api/dispatch3/{entry_id}/actions",
                               {"values": {"action": "确认发出"}})
    report("确认发出 → 运输中",
           status == 200 and departed.get("ok") is True
           and (departed.get("entry") or {}).get("status") == "运输中",
           f"HTTP {status}: {departed}")

    # 5) 确认抵达，链路闭环，车辆/司机释放
    status, arrived = request(base, "POST", f"/api/dispatch3/{entry_id}/actions",
                              {"values": {"action": "确认抵达"}})
    report("确认抵达 → 已抵达（链路闭环）",
           status == 200 and arrived.get("ok") is True
           and (arrived.get("entry") or {}).get("status") == "已抵达",
           f"HTTP {status}: {arrived}")

    _, fleet_end = request(base, "GET", f"/api/fleet?keyword={vehicle_code}")
    _, driver_end = request(base, "GET", f"/api/driver?keyword={driver_code}")
    vehicle_free = next(
        (r for r in fleet_end.get("items", []) if r.get("车辆编号") == vehicle_code), {}
    )
    driver_free = next(
        (r for r in driver_end.get("items", []) if r.get("驾驶员编号") == driver_code), {}
    )
    report("抵达后车辆与司机释放回「空闲」",
           vehicle_free.get("status") == "空闲" and driver_free.get("status") == "空闲",
           f"车辆={vehicle_free.get('status')}，司机={driver_free.get('status')}")

    # 6) 状态机不能跳步/回退：直接对新单「确认发出」应被拒绝
    _, second = request(base, "POST", "/api/dispatch3", {
        "values": {"调度编号": f"{DISPATCH_CODE}-B", "关联委托": ORDER_CODE}
    })
    second_id = (second.get("entry") or {}).get("id")
    rejected = False
    if second_id is not None:
        _, jump = request(base, "POST", f"/api/dispatch3/{second_id}/actions",
                          {"values": {"action": "确认发出"}})
        rejected = jump.get("ok") is False
    report("未指派车辆直接「确认发出」被状态机拒绝", rejected, "未返回 ok=false")

    return finish(skip_reset=True, base=base)


def finish(*, skip_reset: bool, base: str) -> int:
    # 恢复初始示例数据，让页面保持「启动即灌入」的那条链路
    if skip_reset:
        request(base, "POST", "/api/dev/reset")
    print(f"\n结果：{passed} 通过，{failed} 失败")
    if failed:
        print("派车链路存在不可用环节，请根据上面的 FAIL 明细排查。")
        return 1
    print("派车链路全部可用：调度创建、指派车辆/司机、发出、抵达接口均正常。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
