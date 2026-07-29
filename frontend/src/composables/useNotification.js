import { ref, computed } from 'vue'
import { useLanguage } from '../utils/language'

const notifications = ref([
  { id: 'n1', title: '新订单提醒', titleEn: 'New Order Alert', time: '10 分钟前', timeEn: '10 min ago', isRead: false, type: 'order' },
  { id: 'n2', title: '库存预警：抹茶蛋糕不足', titleEn: 'Stock Alert: Matcha Cake low', time: '30 分钟前', timeEn: '30 min ago', isRead: false, type: 'stock' },
  { id: 'n3', title: '系统更新完成', titleEn: 'System update completed', time: '1 小时前', timeEn: '1 hour ago', isRead: false, type: 'system' },
  { id: 'n4', title: '周报已生成，请查收', titleEn: 'Weekly report ready', time: '2 小时前', timeEn: '2 hours ago', isRead: true, type: 'report' },
  { id: 'n5', title: '营销活动「夏日清凉节」已上线', titleEn: 'Campaign "Summer Festival" launched', time: '1 天前', timeEn: '1 day ago', isRead: true, type: 'campaign' },
])

export function useNotification() {
  const { language } = useLanguage()
  const isOpen = ref(false)

  const unreadCount = computed(() => notifications.value.filter(n => !n.isRead).length)

  const displayList = computed(() =>
    notifications.value.map(n => ({
      ...n,
      displayTitle: language.value === 'zh' ? n.title : n.titleEn,
      displayTime: language.value === 'zh' ? n.time : n.timeEn,
    }))
  )

  function toggle() {
    isOpen.value = !isOpen.value
  }

  function close() {
    isOpen.value = false
  }

  function markAsRead(id) {
    const n = notifications.value.find(item => item.id === id)
    if (n) n.isRead = true
  }

  function clickItem(item) {
    isOpen.value = false
  }

  return { notifications, isOpen, unreadCount, displayList, toggle, close, markAsRead, clickItem }
}
