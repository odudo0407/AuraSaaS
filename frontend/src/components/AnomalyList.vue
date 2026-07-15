<template>
  <div>
    <div v-for="(a, i) in items" :key="i"
      class="flex items-start gap-3.5 py-4"
      :class="i < items.length - 1 ? 'border-b border-hairline-soft' : ''">
      <span class="inline-flex items-center justify-center w-8 h-8 rounded-full shrink-0 text-sm font-semibold"
        :class="a.severity === 'high' ? 'bg-primary/10 text-primary' : 'bg-muted/10 text-muted'">
        !
      </span>
      <div class="flex-1">
        <div class="text-sm text-ink font-medium mb-1">{{ a.message }}</div>
        <div class="flex gap-2 items-center">
          <span class="text-xs px-2 py-0.5 rounded-full bg-surface-soft text-muted font-medium">{{ a.tag }}</span>
          <span class="text-xs text-muted-soft">{{ a.time }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ items: Array })
</script>
