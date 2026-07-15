<template>
  <div>
    <div v-for="(c, i) in items" :key="i"
      class="flex items-center justify-between py-4"
      :class="i < items.length - 1 ? 'border-b border-hairline-soft' : ''">
      <div>
        <div class="text-sm text-ink font-medium mb-1.5">{{ c.name }}</div>
        <div class="flex gap-2 items-center">
          <span class="text-xs px-2 py-0.5 rounded-full bg-surface-soft text-muted font-medium">{{ c.channel }}</span>
          <span class="text-xs px-2.5 py-0.5 rounded-full font-semibold"
            :class="{
              'bg-primary/10 text-primary': c.status === 'active',
              'bg-ink/6 text-ink': c.status === 'completed',
              'bg-muted/8 text-muted': c.status === 'draft',
            }">
            {{ { active: 'Active', completed: 'Completed', draft: 'Draft' }[c.status] }}
          </span>
        </div>
      </div>
      <div class="text-right">
        <div class="text-base font-semibold" :class="c.conversion === '—' ? 'text-muted-soft' : 'text-ink'">
          {{ c.conversion }}
        </div>
        <div class="text-xs text-muted-soft">conversion</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ items: Array })
</script>
