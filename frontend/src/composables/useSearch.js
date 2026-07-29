import { ref, computed, watch } from 'vue'
import { useLanguage } from '../utils/language'

const mockData = {
  zh: {
    users: [
      { id: 'u1', name: '张明', role: '运营经理', department: '运营部', email: 'zhangming@example.com', phone: '138****6789' },
      { id: 'u2', name: '李红', role: '数据分析师', department: '数据部', email: 'lihong@example.com', phone: '139****8901' },
      { id: 'u3', name: '王磊', role: '门店店长', department: '门店管理', email: 'wanglei@example.com', phone: '136****0123' },
      { id: 'u4', name: '陈静', role: '市场营销', department: '市场部', email: 'chenjing@example.com', phone: '137****4567' },
      { id: 'u5', name: '赵伟', role: '财务主管', department: '财务部', email: 'zhaowei@example.com', phone: '135****7890' },
      { id: 'u6', name: '孙莉', role: '产品经理', department: '产品部', email: 'sunli@example.com', phone: '133****2345' },
    ],
    products: [
      { id: 'p1', name: '经典拿铁', category: '饮品', price: 28.0, sku: 'DRK-001', stock: 156, sales: 2340 },
      { id: 'p2', name: '抹茶蛋糕', category: '甜点', price: 35.0, sku: 'DST-002', stock: 42, sales: 890 },
      { id: 'p3', name: '牛肉汉堡', category: '主食', price: 45.0, sku: 'FOD-003', stock: 78, sales: 1567 },
      { id: 'p4', name: '芒果冰沙', category: '饮品', price: 32.0, sku: 'DRK-004', stock: 23, sales: 2100 },
      { id: 'p5', name: '提拉米苏', category: '甜点', price: 38.0, sku: 'DST-005', stock: 15, sales: 654 },
      { id: 'p6', name: '鸡肉沙拉', category: '轻食', price: 36.0, sku: 'LGT-006', stock: 90, sales: 1120 },
      { id: 'p7', name: '冰美式', category: '饮品', price: 22.0, sku: 'DRK-007', stock: 200, sales: 3450 },
    ],
    stores: [
      { id: 's1', name: '朝阳旗舰店', address: '北京市朝阳区建国路88号', manager: '王磊', area: '华北', dailyRevenue: 28500 },
      { id: 's2', name: '浦东新城店', address: '上海市浦东新区张杨路168号', manager: '刘洋', area: '华东', dailyRevenue: 32100 },
      { id: 's3', name: '天河城店', address: '广州市天河区天河路230号', manager: '陈斌', area: '华南', dailyRevenue: 19800 },
      { id: 's4', name: '春熙路店', address: '成都市锦江区春熙路99号', manager: '周婷', area: '西南', dailyRevenue: 15600 },
      { id: 's5', name: '中街店', address: '沈阳市沈河区中街路55号', manager: '赵强', area: '东北', dailyRevenue: 12300 },
    ],
    reports: [
      { id: 'r1', name: '2026年7月销售月报', type: '销售报表', author: '李红', updatedAt: '2026-07-20', status: '已发布' },
      { id: 'r2', name: 'Q3季度财务汇总', type: '财务报表', author: '赵伟', updatedAt: '2026-07-18', status: '审核中' },
      { id: 'r3', name: '商品库存周转分析', type: '库存报表', author: '张明', updatedAt: '2026-07-15', status: '已发布' },
      { id: 'r4', name: '门店客流趋势周报', type: '运营报表', author: '李红', updatedAt: '2026-07-19', status: '已发布' },
      { id: 'r5', name: '营销活动ROI分析', type: '营销报表', author: '陈静', updatedAt: '2026-07-17', status: '草稿' },
      { id: 'r6', name: '员工绩效考核汇总', type: 'HR报表', author: '孙莉', updatedAt: '2026-07-16', status: '已发布' },
    ],
    campaigns: [
      { id: 'c1', name: '夏日清凉节', type: '促销活动', budget: 50000, roi: 3.2, startDate: '2026-07-01', endDate: '2026-07-31' },
      { id: 'c2', name: '会员日双倍积分', type: '会员营销', budget: 20000, roi: 5.8, startDate: '2026-07-15', endDate: '2026-07-15' },
      { id: 'c3', name: '新品上市推广', type: '品牌推广', budget: 80000, roi: 2.1, startDate: '2026-07-10', endDate: '2026-08-10' },
      { id: 'c4', name: '社群裂变拉新', type: '社交营销', budget: 15000, roi: 8.5, startDate: '2026-07-05', endDate: '2026-07-25' },
      { id: 'c5', name: '周末限时秒杀', type: '促销活动', budget: 10000, roi: 12.0, startDate: '2026-07-20', endDate: '2026-07-21' },
    ],
  },
  en: {
    users: [
      { id: 'u1', name: 'Ming Zhang', role: 'Operations Manager', department: 'Operations', email: 'ming.zhang@example.com', phone: '138****6789' },
      { id: 'u2', name: 'Hong Li', role: 'Data Analyst', department: 'Data', email: 'hong.li@example.com', phone: '139****8901' },
      { id: 'u3', name: 'Lei Wang', role: 'Store Manager', department: 'Store Ops', email: 'lei.wang@example.com', phone: '136****0123' },
      { id: 'u4', name: 'Jing Chen', role: 'Marketing Lead', department: 'Marketing', email: 'jing.chen@example.com', phone: '137****4567' },
      { id: 'u5', name: 'Wei Zhao', role: 'Finance Head', department: 'Finance', email: 'wei.zhao@example.com', phone: '135****7890' },
      { id: 'u6', name: 'Li Sun', role: 'Product Manager', department: 'Product', email: 'li.sun@example.com', phone: '133****2345' },
    ],
    products: [
      { id: 'p1', name: 'Classic Latte', category: 'Beverage', price: 28.0, sku: 'DRK-001', stock: 156, sales: 2340 },
      { id: 'p2', name: 'Matcha Cake', category: 'Dessert', price: 35.0, sku: 'DST-002', stock: 42, sales: 890 },
      { id: 'p3', name: 'Beef Burger', category: 'Main Course', price: 45.0, sku: 'FOD-003', stock: 78, sales: 1567 },
      { id: 'p4', name: 'Mango Smoothie', category: 'Beverage', price: 32.0, sku: 'DRK-004', stock: 23, sales: 2100 },
      { id: 'p5', name: 'Tiramisu', category: 'Dessert', price: 38.0, sku: 'DST-005', stock: 15, sales: 654 },
      { id: 'p6', name: 'Chicken Salad', category: 'Light Meal', price: 36.0, sku: 'LGT-006', stock: 90, sales: 1120 },
      { id: 'p7', name: 'Iced Americano', category: 'Beverage', price: 22.0, sku: 'DRK-007', stock: 200, sales: 3450 },
    ],
    stores: [
      { id: 's1', name: 'Chaoyang Flagship', address: 'No.88 Jianguo Rd, Chaoyang, Beijing', manager: 'Lei Wang', area: 'North China', dailyRevenue: 28500 },
      { id: 's2', name: 'Pudong New City', address: 'No.168 Zhangyang Rd, Pudong, Shanghai', manager: 'Yang Liu', area: 'East China', dailyRevenue: 32100 },
      { id: 's3', name: 'Tianhe City', address: 'No.230 Tianhe Rd, Tianhe, Guangzhou', manager: 'Bin Chen', area: 'South China', dailyRevenue: 19800 },
      { id: 's4', name: 'Chunxi Road', address: 'No.99 Chunxi Rd, Jinjiang, Chengdu', manager: 'Ting Zhou', area: 'Southwest', dailyRevenue: 15600 },
      { id: 's5', name: 'Zhongjie', address: 'No.55 Zhongjie Rd, Shenhe, Shenyang', manager: 'Qiang Zhao', area: 'Northeast', dailyRevenue: 12300 },
    ],
    reports: [
      { id: 'r1', name: 'July 2026 Sales Report', type: 'Sales', author: 'Hong Li', updatedAt: '2026-07-20', status: 'Published' },
      { id: 'r2', name: 'Q3 Financial Summary', type: 'Finance', author: 'Wei Zhao', updatedAt: '2026-07-18', status: 'In Review' },
      { id: 'r3', name: 'Inventory Turnover Analysis', type: 'Inventory', author: 'Ming Zhang', updatedAt: '2026-07-15', status: 'Published' },
      { id: 'r4', name: 'Store Traffic Weekly', type: 'Operations', author: 'Hong Li', updatedAt: '2026-07-19', status: 'Published' },
      { id: 'r5', name: 'Campaign ROI Analysis', type: 'Marketing', author: 'Jing Chen', updatedAt: '2026-07-17', status: 'Draft' },
      { id: 'r6', name: 'Staff Performance Summary', type: 'HR', author: 'Li Sun', updatedAt: '2026-07-16', status: 'Published' },
    ],
    campaigns: [
      { id: 'c1', name: 'Summer Cool Festival', type: 'Promotion', budget: 50000, roi: 3.2, startDate: '2026-07-01', endDate: '2026-07-31' },
      { id: 'c2', name: 'Member Double Points', type: 'Loyalty', budget: 20000, roi: 5.8, startDate: '2026-07-15', endDate: '2026-07-15' },
      { id: 'c3', name: 'New Product Launch', type: 'Branding', budget: 80000, roi: 2.1, startDate: '2026-07-10', endDate: '2026-08-10' },
      { id: 'c4', name: 'Social Referral Campaign', type: 'Social', budget: 15000, roi: 8.5, startDate: '2026-07-05', endDate: '2026-07-25' },
      { id: 'c5', name: 'Weekend Flash Sale', type: 'Promotion', budget: 10000, roi: 12.0, startDate: '2026-07-20', endDate: '2026-07-21' },
    ],
  },
}

const categoryLabels = {
  zh: { users: '用户', products: '商品', stores: '门店', reports: '报表', campaigns: '营销活动' },
  en: { users: 'Users', products: 'Products', stores: 'Stores', reports: 'Reports', campaigns: 'Campaigns' },
}

const categoryKeys = ['users', 'products', 'stores', 'reports', 'campaigns']

const categoryRouteMap = {
  users: '/app/staff',
  products: '/app/products',
  stores: '/app/stores',
  reports: '/app/reports',
  campaigns: '/app/marketing',
}

const itemFields = {
  users: ['role', 'department', 'email', 'phone'],
  products: ['category', 'price', 'sku', 'stock', 'sales'],
  stores: ['address', 'manager', 'area', 'dailyRevenue'],
  reports: ['type', 'author', 'updatedAt', 'status'],
  campaigns: ['type', 'budget', 'roi', 'startDate', 'endDate'],
}

export function useSearch() {
  const { language } = useLanguage()
  const keyword = ref('')
  const results = ref([])
  const isOpen = ref(false)

  const labels = computed(() => categoryLabels[language.value])
  const placeholder = computed(() => language.value === 'zh' ? '搜索用户、商品、门店…' : 'Search users, products, stores…')

  function search() {
    const q = keyword.value.trim().toLowerCase()
    if (!q) {
      results.value = []
      isOpen.value = false
      return
    }

    const data = mockData[language.value]
    const grouped = []

    for (const cat of categoryKeys) {
      const items = data[cat].filter(item => {
        return itemFields[cat].some(field => {
          const val = item[field]
          if (typeof val === 'number') return String(val).includes(q)
          if (typeof val === 'string') return val.toLowerCase().includes(q)
          return false
        }) || item.name.toLowerCase().includes(q)
      })

      if (items.length) {
        grouped.push({ category: cat, label: labels.value[cat], items })
      }
    }

    results.value = grouped
    isOpen.value = grouped.length > 0
  }

  watch(keyword, () => { search() })

  function clear() {
    keyword.value = ''
    results.value = []
    isOpen.value = false
  }

  function getItemRoute(category) {
    return categoryRouteMap[category] || '/app/dashboard'
  }

  function clickItem(item, category) {
    isOpen.value = false
    return { path: getItemRoute(category), query: { id: item.id } }
  }

  function close() {
    isOpen.value = false
  }

  return { keyword, results, isOpen, labels, placeholder, search, clear, clickItem, close }
}
