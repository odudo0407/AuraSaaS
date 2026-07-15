<template>
  <div>
    <div class="grid pb-3 border-b border-hairline-soft" style="grid-template-columns: 1.5fr 0.8fr 0.8fr 1fr 0.8fr">
      <span v-for="h in ['Item', 'Category', 'Sales', 'Revenue', 'Margin']" :key="h"
        class="text-muted text-sm font-medium">{{ h }}</span>
    </div>
    <div v-for="(sku, i) in skus" :key="sku.sku_name"
      class="grid py-3.5 items-center"
      :class="i < skus.length - 1 ? 'border-b border-hairline-soft' : ''"
      style="grid-template-columns: 1.5fr 0.8fr 0.8fr 1fr 0.8fr">
      <span class="text-sm font-medium text-ink">{{ sku.sku_name }}</span>
      <span class="text-sm text-muted">{{ sku.category }}</span>
      <span class="text-sm text-body">{{ sku.total_sales }}</span>
      <span class="text-sm text-body">¥{{ sku.total_revenue?.toLocaleString() }}</span>
      <span class="text-sm font-semibold"
        :class="sku.avg_margin >= 60 ? 'text-ink' : sku.avg_margin >= 40 ? 'text-muted' : 'text-error-text'">
        {{ sku.avg_margin }}%
      </span>
    </div>
  </div>
</template>

<script setup>
defineProps({ skus: Array })
</script>
