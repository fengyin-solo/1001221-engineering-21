<template>
  <section class="page" data-module="dispatch3">
    <header class="page-head">
      <div>
        <h2>运力调度管理</h2>
        <p class="page-desc">维护调度任务，围绕调度编号、关联委托、指派车辆、指派司机做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记调度任务</button>
        <button class="btn" type="button" @click="exportRows">导出运力调度清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>当前状态</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] || '—' }}</td>
          <td>{{ row.status }}</td>
          <td class="row-actions">
            <button
              v-if="row.status === '待调度'"
              class="link"
              type="button"
              @click="openAssign(row)"
            >
              指派调度
            </button>
            <button
              v-if="row.status === '已调度'"
              class="link"
              type="button"
              @click="runAction('确认发出', row, {})"
            >
              确认发出
            </button>
            <button
              v-if="row.status === '运输中'"
              class="link"
              type="button"
              @click="runAction('确认抵达', row, {})"
            >
              确认抵达
            </button>
            <span v-if="row.status === '已抵达'" class="muted-text">已完成</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无运力调度数据，可先登记调度任务</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条运力调度记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <!-- 登记调度任务 -->
    <div v-if="showCreate" class="modal-mask" @click.self="closeCreate">
      <form class="modal" @submit.prevent="submitCreate">
        <h3>登记调度任务</h3>
        <p class="page-desc">只需选择已接收的运输委托；车辆与司机在「指派调度」时再确定。</p>
        <label class="modal-field">
          <span>调度编号 *</span>
          <input v-model="createForm.调度编号" placeholder="如 DISP-20260927-01" required />
        </label>
        <label class="modal-field">
          <span>关联委托 *</span>
          <select v-model="createForm.关联委托" required>
            <option value="" disabled>请选择已接收的委托单</option>
            <option v-for="order in receivableOrders" :key="String(order.id)" :value="order.委托编号">
              {{ order.委托编号 }}｜{{ order.委托方 }}
            </option>
          </select>
        </label>
        <label class="modal-field">
          <span>计划发出</span>
          <input v-model="createForm.计划发出" placeholder="2026-09-27 06:00" />
        </label>
        <label class="modal-field">
          <span>预计到达</span>
          <input v-model="createForm.预计到达" placeholder="2026-09-27 10:30" />
        </label>
        <div class="modal-actions">
          <button class="btn ghost" type="button" @click="closeCreate">取消</button>
          <button class="btn primary" type="submit">登记</button>
        </div>
      </form>
    </div>

    <!-- 指派车辆 / 指派司机 -->
    <div v-if="showAssign" class="modal-mask" @click.self="closeAssign">
      <form class="modal" @submit.prevent="submitAssign">
        <h3>指派调度</h3>
        <p class="page-desc">
          调度单 {{ assignTarget?.调度编号 }}（{{ assignTarget?.关联委托 }}）：
          选择空闲车辆与空闲司机，提交后进入「已调度」。
        </p>
        <label class="modal-field">
          <span>指派车辆 *</span>
          <select v-model="assignForm.指派车辆" required>
            <option value="" disabled>请选择空闲车辆</option>
            <option v-for="vehicle in idleVehicles" :key="String(vehicle.id)" :value="vehicle.车辆编号">
              {{ vehicle.车辆编号 }}｜{{ vehicle.车牌号码 }}｜{{ vehicle.车型类别 }}
            </option>
          </select>
        </label>
        <label class="modal-field">
          <span>指派司机 *</span>
          <select v-model="assignForm.指派司机" required>
            <option value="" disabled>请选择空闲司机</option>
            <option v-for="driver in idleDrivers" :key="String(driver.id)" :value="driver.驾驶员编号">
              {{ driver.驾驶员编号 }}｜{{ driver.驾驶员姓名 }}｜{{ driver.联系电话 }}
            </option>
          </select>
        </label>
        <label class="modal-field">
          <span>调度人员</span>
          <input v-model="assignForm.调度人员" placeholder="如 调度员-林敏" />
        </label>
        <div class="modal-actions">
          <button class="btn ghost" type="button" @click="closeAssign">取消</button>
          <button class="btn primary" type="submit">确认指派</button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/dispatch3'
const columns = ["调度编号", "关联委托", "指派车辆", "指派司机", "计划发出", "预计到达", "调度人员"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

const showCreate = ref(false)
const showAssign = ref(false)
const createForm = reactive<Record<string, string>>({
  调度编号: '',
  关联委托: '',
  计划发出: '',
  预计到达: '',
})
const assignForm = reactive<Record<string, string>>({
  指派车辆: '',
  指派司机: '',
  调度人员: '',
})
const assignTarget = ref<Row | null>(null)
const idleVehicles = ref<Row[]>([])
const idleDrivers = ref<Row[]>([])
const receivableOrders = ref<Row[]>([])

const stats = computed(() => {
  const count = (status: string) => rows.value.filter((row) => row.status === status).length
  return [
    { label: '待调度任务', value: count('待调度') },
    { label: '已调度待发车', value: count('已调度') },
    { label: '运输中任务', value: count('运输中') },
    { label: '已抵达任务', value: count('已抵达') },
  ]
})

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

async function fetchJson(path: string): Promise<any> {
  const response = await request(path)
  if (!response.ok) {
    throw new Error(`接口返回 ${response.status}`)
  }
  return response.json()
}

function openCreate() {
  errorMessage.value = ''
  Object.assign(createForm, { 调度编号: '', 关联委托: '', 计划发出: '', 预计到达: '' })
  showCreate.value = true
  // 只允许给「已接收、尚未派车」的委托建调度单
  void fetchJson('/api/order?status=%E5%B7%B2%E6%8E%A5%E6%94%B6')
    .then((payload) => { receivableOrders.value = payload.items ?? [] })
    .catch(() => { errorMessage.value = '可派委托列表读取失败' })
}

function closeCreate() {
  showCreate.value = false
}

async function submitCreate() {
  errorMessage.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({
        values: Object.fromEntries(Object.entries(createForm).filter(([, value]) => value)),
      }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message ?? '调度任务登记失败')
    }
    showCreate.value = false
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '调度任务登记失败'
  }
}

async function openAssign(row: Row) {
  errorMessage.value = ''
  assignTarget.value = row
  Object.assign(assignForm, {
    指派车辆: String(row.指派车辆 ?? ''),
    指派司机: String(row.指派司机 ?? ''),
    调度人员: String(row.调度人员 ?? ''),
  })
  showAssign.value = true
  try {
    const [fleetPage, driverPage] = await Promise.all([
      fetchJson('/api/fleet?status=%E7%A9%BA%E9%97%B2'),
      fetchJson('/api/driver?status=%E7%A9%BA%E9%97%B2'),
    ])
    idleVehicles.value = fleetPage.items ?? []
    idleDrivers.value = driverPage.items ?? []
  } catch {
    errorMessage.value = '空闲车辆/司机列表读取失败'
  }
}

function closeAssign() {
  showAssign.value = false
  assignTarget.value = null
}

async function submitAssign() {
  if (!assignTarget.value) return
  await runAction('指派调度', assignTarget.value, { ...assignForm })
  if (!errorMessage.value) {
    showAssign.value = false
  }
}

async function runAction(action: string, row: Row, extra: Record<string, string>) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action, ...extra } }),
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.message ?? '运力调度动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '运力调度操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const payload = await fetchJson(`${ENDPOINT}?${query}`)
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '运力调度列表读取失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.muted-text { color: var(--muted); font-size: 12px; }
.modal-mask {
  position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45);
  display: flex; align-items: center; justify-content: center; z-index: 20;
}
.modal {
  width: 420px; background: #fff; border-radius: 10px; padding: 20px 22px;
  display: flex; flex-direction: column; gap: 12px;
}
.modal h3 { margin: 0; }
.modal-field { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.modal-field span { color: var(--muted); }
.modal-field input, .modal-field select {
  border: 1px solid var(--border); border-radius: 6px; padding: 7px 9px; font: inherit;
}
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
</style>
