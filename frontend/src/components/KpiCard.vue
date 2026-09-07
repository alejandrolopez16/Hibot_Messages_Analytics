<script setup>
import { computed } from 'vue'
import { formatNumber } from '../constants/outbound'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], required: true },
  caption: { type: String, default: '' },
  accent: { type: String, default: '#8994AB' },
  loading: { type: Boolean, default: false },
})

const display = computed(() =>
  typeof props.value === 'number' ? formatNumber(props.value) : props.value,
)
</script>

<template>
  <div class="relative overflow-hidden rounded-lg border border-line bg-surface-1 p-4">
    <!-- Filete de color: liga la tarjeta con su segmento en la barra y el donut. -->
    <span class="absolute inset-x-0 top-0 h-px" :style="{ backgroundColor: accent }" />

    <p class="font-condensed text-[11px] uppercase tracking-[0.18em] text-muted">
      {{ label }}
    </p>

    <p
      v-if="loading"
      class="mt-2 h-8 w-24 animate-pulse rounded bg-line"
      aria-hidden="true"
    />
    <p v-else class="mt-1 font-mono text-3xl leading-none tabular-nums text-ink-50">
      {{ display }}
    </p>

    <p v-if="caption && !loading" class="mt-1.5 text-xs text-muted">{{ caption }}</p>
  </div>
</template>
