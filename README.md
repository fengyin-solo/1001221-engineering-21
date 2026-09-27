# 冷链物流运输管理平台

面向冷链运输全程温控、车辆调度、门到门配送、温度异常处置、签收回单与运力结算的冷链运输管理后台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/            每个业务模块一个页面
│   ├── src/api/              统一请求封装
│   ├── src/stores/           会话与筛选状态
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/          每个业务模块一组接口
│   ├── app/services/         业务规则与状态流转
│   ├── app/seed.py           启动时自动灌入的示例数据
│   ├── app/store.py          内存数据仓库
│   └── requirements.txt      锁定到具体版本的后端依赖
├── scripts/
│   ├── dev.sh                make dev 的编排：检查环境→装依赖→拉起前后端
│   └── check.py              make check 的检查入口
├── Makefile                  env / install / build / dev / check
├── .env.example              必填环境变量样例（APP_ENV）
├── .gitignore
└── docker-compose.yml
```

## 从零到能用

前置要求：Python 3.11+、Node.js 20+（自带 npm）。依赖版本已全部锁定
（后端 `backend/requirements.txt`，前端 `frontend/package-lock.json`），
任何机器装出来的版本完全一致。

```bash
cp .env.example .env   # 或 make env，只需一次
make dev               # 一条命令：检查环境 → 装依赖 → 灌示例数据 → 拉起前后端
```

启动后：

- 后端 `http://127.0.0.1:8000`，健康检查 `curl http://127.0.0.1:8000/api/health`
- 前端 `http://127.0.0.1:5173`，dev server 不会自动打开浏览器，按终端地址手工访问；
  `/api` 由 vite 代理到后端 `http://127.0.0.1:8000`
- 后端启动日志会打印 `[seed] 示例数据已灌入 …`，其中运力调度是一条完整链路：
  待调度（待派车）→ 已调度 → 运输中 → 已抵达，指派车辆/指派司机与车辆档案、
  司机管理里的数据一一对应，可直接演示派车全流程

### 验证派车链路

另开一个终端执行：

```bash
make check
```

依次检查健康检查、示例数据链路完整性、调度创建（`POST /api/dispatch3`）、
指派车辆动作（`POST /api/dispatch3/{id}/actions`）与列表过滤，全部通过会打印
`全部通过：调度创建与指派车辆接口均可正常返回。`

### 启动失败怎么定位

启动脚本会把失败原因分成两类打在终端上：

- `依赖缺失：…` —— python3/node/npm 不存在、venv 创建失败、pip/npm 装依赖失败，
  按提示装对应工具或检查网络即可
- `环境变量未配置：…` —— 缺少 `.env` 或 `APP_ENV` 未设置，执行 `cp .env.example .env` 后重试

### 常用命令

| 命令 | 作用 |
| --- | --- |
| `make dev` | 从零到能用的一条命令（推荐） |
| `make check` | 检查调度创建与指派车辆接口 |
| `make install` | 只装依赖（锁定版本） |
| `make build` | 前端生产构建（含类型检查） |
| `make backend` / `make frontend` | 单独起后端 / 前端 |

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 车辆档案 | `fleet` | 冷链车 | 车辆编号、车牌号码、车型类别 |
| 司机管理 | `driver` | 驾驶员 | 驾驶员编号、驾驶员姓名、驾驶证号 |
| 运输委托 | `order` | 运输委托单 | 委托编号、委托方、起运地址 |
| 运力调度 | `dispatch3` | 调度任务 | 调度编号、关联委托、指派车辆 |
| 温控监测 | `temp` | 温度记录 | 记录编号、关联调度、温区编号 |
| 门到门配送 | `door` | 配送任务 | 任务编号、关联调度、配送站点 |
| 回单管理 | `returntrip` | 回执单 | 回单编号、关联任务、签收方 |
| 异常处置 | `abnormal2` | 异常记录 | 异常编号、异常类型、关联任务 |
| 续运中转 | `renew` | 中转记录 | 中转编号、关联任务、中转站点 |
| 制冷机组 | `refriger` | 制冷机组 | 机组编号、所属车辆、机组型号 |
| 温控箱体 | `box` | 温控箱体 | 箱体编号、箱体类型、内部容积 |
| 运输路线 | `route` | 路线方案 | 路线编号、出发地、目的地 |
| 温感器管理 | `sensor` | 温度传感器 | 传感器编号、所属车辆、传感器型号 |
| 运输费用 | `cost` | 费用记录 | 费用编号、关联任务、费用类别 |
| 委托方管理 | `client2` | 委托方 | 委托方编号、委托方名称、企业类别 |
| 出车检查 | `checkin` | 检查记录 | 检查编号、检查车辆、检查日期 |
| 事故记录 | `accident` | 事故记录 | 事故编号、关联任务、事故类型 |
| 途中核查 | `roadcheck` | 途中核查 | 核查编号、关联调度、核查时间 |
| 车厢清洗 | `clean2` | 清洗记录 | 清洗编号、清洗车辆、清洗方式 |
| 合作合同 | `contract2` | 运输合同 | 合同编号、签约双方、合同类型 |

## 约定

- 每个模块的前端页面在 `frontend/src/views/<模块>/index.vue`，后端接口在
  `backend/app/routers/<模块>.py`，业务规则在 `backend/app/services/<模块>.py`。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。
