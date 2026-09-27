.PHONY: env install build dev backend frontend check

# 生成本地环境变量文件（只需一次）
env:
	cp -n .env.example .env && echo "已生成 .env，可按需修改"

# 只装依赖：后端按 requirements.txt 锁定版本，前端按 package-lock.json
install:
	cd backend && ./run.sh --install-only
	cd frontend && npm ci

# 前端生产构建（含类型检查）
build:
	cd frontend && npm ci && npm run build

# 从零到能用的一条命令：检查环境 → 装依赖 → 灌示例数据 → 同时拉起前后端
dev:
	./scripts/dev.sh

backend:
	cd backend && ./run.sh

frontend:
	cd frontend && npm ci && npm run dev

# 检查入口：确认调度创建与指派车辆接口都能返回
check:
	python3 scripts/check.py
