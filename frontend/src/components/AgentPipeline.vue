<template>
  <div class="w-300px bg-canvas border border-hairline rounded-3.5 p-6 shrink-0">
    <div class="text-base font-semibold text-ink mb-7">Agent Pipeline</div>

    <div class="relative">
      <div v-for="(agent, i) in agents" :key="agent.id" class="relative">
        <!-- Dashed connecting line -->
        <div v-if="i < agents.length - 1"
          class="absolute left-4.5 top-12 w-px h-9 border-l border-dashed border-hairline" />

        <!-- Agent node -->
        <div class="flex items-center gap-3.5 px-3 py-2.5 mb-1 rounded-xl transition-all"
          :class="agent.status === 'running' ? 'bg-primary/4' : ''">

          <!-- Icon circle -->
          <div class="relative w-10 h-10 rounded-full flex items-center justify-center text-lg shrink-0"
            :class="{
              'bg-ink text-white': agent.status === 'complete',
              'bg-primary text-white': agent.status === 'running',
              'bg-surface-strong text-muted-soft': agent.status === 'pending',
            }">
            {{ agent.status === 'complete' ? '✓' : agent.icon }}
            <div v-if="agent.status === 'running'"
              class="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-primary border-2 border-canvas"
              style="animation: pulse-dot 1.5s ease-in-out infinite" />
          </div>

          <!-- Text -->
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium" :class="agent.status === 'pending' ? 'text-muted-soft' : 'text-ink'">
              {{ agent.name }}
            </div>
            <div class="text-xs"
              :class="{
                'text-muted': agent.status === 'complete',
                'text-primary': agent.status === 'running',
                'text-muted-soft': agent.status === 'pending',
              }">
              {{ agent.status === 'complete' ? 'Completed' : agent.status === 'running' ? 'Processing...' : 'Waiting' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="mt-7 p-5 bg-surface-soft rounded-xl">
      <div class="text-xs text-muted mb-3 font-semibold tracking-wider uppercase">Session Stats</div>
      <div class="flex justify-between">
        <div>
          <div class="text-xl font-bold text-ink">{{ agents.length }}</div>
          <div class="text-xs text-muted-soft">Agents</div>
        </div>
        <div>
          <div class="text-xl font-bold text-ink">--</div>
          <div class="text-xs text-muted-soft">Total</div>
        </div>
        <div>
          <div class="text-xl font-bold text-ink">{{ queryCount }}</div>
          <div class="text-xs text-muted-soft">Queries</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ agents: Array })
const queryCount = computed(() => props.agents.filter(a => a.status === 'complete').length > 0 ? 1 : 0)
</script>
