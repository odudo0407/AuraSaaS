<template>
  <section class="bg-canvas border border-hairline rounded-xl p-6">
    <div v-if="title" class="text-sm font-semibold text-ink mb-4">{{ title }}</div>
    <slot />
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '',
  },
})
</script>
