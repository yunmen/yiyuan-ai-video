<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import api from '@/api'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ pageNum: 1, pageSize: 10, status: null })

const statusMap = {
  1: { label: '待支付', type: 'warning' },
  2: { label: '已支付', type: 'primary' },
  3: { label: '已完成', type: 'success' },
  4: { label: '已取消', type: 'info' },
  5: { label: '退款中', type: 'warning' },
  6: { label: '已退款', type: 'info' },
}
const filters = [
  { label: '全部', value: null },
  { label: '待支付', value: 1 },
  { label: '已完成', value: 3 },
  { label: '已退款', value: 6 },
]
const activeFilter = ref(null)

const countText = computed(() => `${total.value} 笔订单`)

async function loadList() {
  loading.value = true
  try {
    const params = { ...query }
    if (!params.status) delete params.status
    const res = await api.payment.orderList.post(params)
    if (res.code === 1) {
      list.value = res.data || []
      total.value = res.total || 0
    }
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
}

function onFilter(value) {
  if (activeFilter.value === value) return
  activeFilter.value = value
  query.status = value
  query.pageNum = 1
  loadList()
}

function onPageChange(page) {
  query.pageNum = page
  loadList()
}

function onView(item) {
  const taskId = (item.response || {}).task_id
  if (taskId) router.push(`/generate/${taskId}`)
}

onMounted(() => {
  if (!userStore.isLoggedIn) {
    userStore.openLogin()
    return
  }
  loadList()
})
</script>

<template>
  <div class="orders-page">
    <div class="wrap">
      <div class="orders-head">
        <div>
          <h2>我的订单</h2>
          <span class="sub">{{ countText }}</span>
        </div>
        <button class="back-btn" @click="router.push('/user')">返回个人中心</button>
      </div>

      <div class="filters">
        <div
          v-for="f in filters"
          :key="f.label"
          class="ftab"
          :class="{ on: activeFilter === f.value }"
          @click="onFilter(f.value)"
        >{{ f.label }}</div>
      </div>

      <n-spin :show="loading">
        <div v-if="!loading && !list.length" class="empty">
          <div class="empty-text">暂无订单记录</div>
          <div class="go-btn" @click="router.push('/studio')">去制作视频</div>
        </div>

        <template v-else>
          <div class="list">
            <div v-for="item in list" :key="item.id" class="ocard" @click="onView(item)">
              <div class="o-main">
                <div class="o-name">{{ item.package_name }}</div>
                <div class="o-no">{{ item.order_no }}</div>
                <div class="o-time">{{ item.create_time }}</div>
              </div>
              <div class="o-right">
                <div class="o-amount">¥{{ item.amount }}</div>
                <span class="o-status" :class="`s${item.status}`">
                  {{ (statusMap[item.status] || {}).label || item.status }}
                </span>
              </div>
            </div>
          </div>
          <div v-if="total > query.pageSize" class="pagination-wrap">
            <n-pagination
              v-model:page="query.pageNum"
              :item-count="total"
              :page-size="query.pageSize"
              :show-size-picker="false"
              @update:page="onPageChange"
            />
          </div>
        </template>
      </n-spin>
    </div>
  </div>
</template>

<style scoped>
.orders-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding-bottom: 80px; }
.wrap { max-width: 860px; margin: 0 auto; padding: 16px; }

.orders-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.orders-head h2 { margin: 0; font-size: 20px; font-weight: 700; }
.orders-head .sub { font-size: 12px; color: var(--weak); }
.back-btn {
  height: 34px; padding: 0 16px; border: 1px solid var(--line); border-radius: 17px;
  background: #fff; color: var(--body-c); font-size: 13px; cursor: pointer;
}
.back-btn:hover { color: var(--brand); border-color: var(--brand); }

.filters { display: flex; gap: 8px; margin: 16px 0; overflow-x: auto; }
.ftab {
  height: 32px; padding: 0 16px; border-radius: var(--radius-lg); background: #fff;
  color: var(--body-c); font-size: 13px; display: flex; align-items: center;
  white-space: nowrap; cursor: pointer; transition: background .15s, color .15s;
}
.ftab:hover { color: var(--brand); }
.ftab.on { background: var(--brand); color: #fff; font-weight: 600; }

.empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 18px; padding: 70px 20px; background: #fff; border-radius: var(--radius-lg);
}
.empty-text { font-size: 14px; color: var(--weak); }
.go-btn {
  width: 160px; height: 44px; border-radius: 22px; background: var(--brand);
  color: #fff; font-size: 15px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}

.list { display: flex; flex-direction: column; gap: 12px; }
.ocard {
  background: #fff; border-radius: var(--radius); padding: 14px 16px;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  box-shadow: var(--shadow-sm); cursor: pointer;
  transition: transform .18s, box-shadow .18s;
}
.ocard:hover { transform: translateY(-2px); box-shadow: var(--shadow); }
.o-main { min-width: 0; }
.o-name { font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.o-no { font-size: 11px; color: var(--weak); margin-top: 4px; }
.o-time { font-size: 11px; color: var(--weak); margin-top: 2px; }
.o-right { text-align: right; flex: 0 0 auto; }
.o-amount { font-size: 16px; font-weight: 700; color: var(--brand); }
.o-status { display: inline-block; margin-top: 6px; font-size: 12px; padding: 2px 10px; border-radius: var(--radius-sm); }
.o-status.s1, .o-status.s5 { background: var(--warning-bg); color: var(--warning); }
.o-status.s2 { background: var(--info-bg); color: var(--info); }
.o-status.s3 { background: var(--success-bg); color: var(--success); }
.o-status.s4, .o-status.s6 { background: var(--bg); color: var(--weak); }
.pagination-wrap { display: flex; justify-content: center; padding: 20px 0 8px; }

@media (min-width: 768px) {
  .wrap { padding: 24px; }
  .filters { overflow-x: visible; }
}
</style>
