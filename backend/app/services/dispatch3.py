"""运力调度业务规则：状态流转、字段校验与筛选口径都收在这里。

派车链路：
  待调度 --指派调度(指派车辆+指派司机)--> 已调度 --确认发出--> 运输中 --确认抵达--> 已抵达
- 创建调度单只需调度编号与关联委托；车辆/司机在「指派调度」动作里落库，
  会校验车辆、司机确实存在且当前空闲，指派后车辆/司机变为「出车中」。
- 状态只能按顺序前进，不能跳步、不能回退。
- 「确认抵达」后车辆与司机释放回「空闲」，派车链路闭环。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "dispatch3"
CREATE_FIELDS = ["调度编号", "关联委托"]
OPTIONAL_FIELDS = ["指派车辆", "指派司机", "计划发出", "预计到达", "调度人员"]
REQUIRED_FIELDS = ["调度编号", "关联委托", "指派车辆"]
STATUS_ORDER = ["待调度", "已调度", "运输中", "已抵达"]
ACTION_RULES = {"指派调度": "已调度", "确认发出": "运输中", "确认抵达": "已抵达"}
NEGATIVE_ACTIONS: list[str] = []

# 指派动作需要校验的资源：(调度字段, 模块, 编号字段, 不可用状态集合)
RESOURCE_SPECS = [
    ("指派车辆", "fleet", "车辆编号", {"出车中", "维修中", "已报废"}),
    ("指派司机", "driver", "驾驶员编号", {"出车中", "休假", "已离职"}),
]


class Dispatch3Service:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("调度编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in CREATE_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        code = str(values["调度编号"]).strip()
        if any(str(row.get("调度编号", "")).strip() == code for row in rows):
            return None, ["调度编号重复"]
        order = store.find_by_field("order", "委托编号", str(values["关联委托"]).strip())
        if order is None:
            return None, ["关联委托不存在"]
        entry: dict[str, Any] = {
            "id": max((int(row.get("id", 0)) for row in rows), default=0) + 1,
            "status": STATUS_ORDER[0],
            "pending": True,
            "abnormal": False,
            "指派车辆": "",
            "指派司机": "",
            "计划发出": "",
            "预计到达": "",
            "调度人员": "",
            "调度状态": "待调度",
        }
        for field in CREATE_FIELDS + OPTIONAL_FIELDS:
            if values.get(field) is not None:
                entry[field] = str(values.get(field)).strip()
        rows.append(entry)
        return entry, []

    def _assign_resources(
        self, entry: dict[str, Any], values: dict[str, Any]
    ) -> str | None:
        """校验并写入指派车辆 / 指派司机；返回 None 表示通过，否则返回错误说明。"""
        chosen: dict[str, str] = {}
        for dispatch_field, module, code_field, blocked in RESOURCE_SPECS:
            code = str(
                values.get(dispatch_field)
                or entry.get(dispatch_field)
                or ""
            ).strip()
            if not code:
                return f"缺少{dispatch_field}：请先选择可用的{code_field}再指派"
            resource = store.find_by_field(module, code_field, code)
            if resource is None:
                return f"{dispatch_field} {code} 在资源档案里不存在，请核对编号"
            if resource.get("status") in blocked:
                return (
                    f"{dispatch_field} {code} 当前状态为「{resource.get('status')}」，"
                    f"不可参与派车"
                )
            chosen[dispatch_field] = code
        entry["指派车辆"] = chosen["指派车辆"]
        entry["指派司机"] = chosen["指派司机"]
        dispatcher = str(values.get("调度人员") or entry.get("调度人员") or "").strip()
        if dispatcher:
            entry["调度人员"] = dispatcher
        # 资源占用：车辆 / 司机标记为出车中，防止同一条资源被重复指派
        store.find_by_field("fleet", "车辆编号", chosen["指派车辆"])["status"] = "出车中"
        store.find_by_field("driver", "驾驶员编号", chosen["指派司机"])["status"] = "出车中"
        return None

    def run_action(
        self, entry_id: int, action: str, values: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"调度任务 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于运力调度可执行范围"
        target = ACTION_RULES[action]
        current_index = STATUS_ORDER.index(entry["status"]) if entry["status"] in STATUS_ORDER else -1
        target_index = STATUS_ORDER.index(target)
        if current_index < 0:
            return None, f"当前状态「{entry['status']}」不在允许的状态序列里"
        if target_index <= current_index:
            return None, f"调度任务当前为「{entry['status']}」，不能重复执行「{action}」"
        if target_index != current_index + 1:
            return (
                None,
                f"调度任务当前为「{entry['status']}」，需先完成"
                f"「{self._action_for_status(STATUS_ORDER[current_index + 1])}」",
            )

        if action == "指派调度":
            error = self._assign_resources(entry, values or {})
            if error:
                return None, error
        elif action == "确认抵达":
            # 链路闭环：释放车辆与司机
            vehicle = store.find_by_field("fleet", "车辆编号", str(entry.get("指派车辆", "")))
            driver = store.find_by_field("driver", "驾驶员编号", str(entry.get("指派司机", "")))
            if vehicle is not None:
                vehicle["status"] = "空闲"
            if driver is not None:
                driver["status"] = "空闲"

        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        entry["调度状态"] = {
            "已调度": "已调度待发车",
            "运输中": "在途",
            "已抵达": "已抵达已签收",
        }[target]
        return entry, f"调度任务已{action}"

    @staticmethod
    def _action_for_status(status: str) -> str:
        for action, target in ACTION_RULES.items():
            if target == status:
                return action
        return status
