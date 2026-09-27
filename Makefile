.PHONY: dev install build check backend frontend

# 构建与启动合成一条命令：装依赖 -> 前端构建检查 -> 启动前后端
dev:
	./dev.sh

# 只安装两边的锁定依赖，不启动
install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
	cd frontend && npm ci

# 只做前端构建检查（vue-tsc + vite build）
build:
	cd frontend && npm ci && npm run build

# 派车链路检查：调度创建 + 指派车辆/司机 + 发出 + 抵达
check:
	./check.sh

backend:
	cd backend && ./run.sh

frontend:
	cd frontend && npm run dev
