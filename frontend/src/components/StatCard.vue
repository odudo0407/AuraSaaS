<template>
  <div class="card-hover bg-canvas border border-hairline rounded-3.5 p-6 cursor-default">
    <div class="text-muted text-sm font-medium mb-2">{{ label }}</div>
    <div class="text-ink font-bold leading-none mb-2" style="font-size: 28px; letter-spacing: -0.2px">
      {{ value }}
    </div>
    <div class="flex items-center gap-2">
      <span
        class="inline-flex items-center gap-0.5 text-xs font-semibold px-2.5 py-0.5 rounded-full"
        :class="growth >= 0 ? 'bg-primary/8 text-primary' : 'bg-muted/8 text-muted'"
      >
        {{ growth >= 0 ? '↑' : '↓' }} {{ Math.abs(growth) }}%
      </span>
      <span class="text-muted-soft text-xs">{{ subtext }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: String,
  value: String,
  growth: Number,
  subtext: { type: String, default: 'vs last month' },
})
</script>
