<script setup>
import { computed } from 'vue'
import { INBOUND_COLOR, OUTBOUND_SEGMENTS, formatNumber, formatPercent } from '../constants/outbound'

/**
 * Una sola barra que lee de izquierda a derecha: lo que entró, y frente a ello
 * de qué se compuso lo que salió. Es la misma gramática en la cabecera y en cada
 * fila de la tabla, así que comparar canales es comparar formas.
 */
const props = defineProps({
  incoming: { type: Number, default: 0 },
  outbound: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})

const total = computed(() => props.incoming + (props.outbound?.total ?? 0))

const parts = computed(() => {
  if (!total.value) return []
  const items = [
    { key: 'incoming', label: 'Entrantes', color: INBOUND_COLOR, value: props.incoming },
    ...OUTBOUND_SEGMENTS.map((segment) => ({
      ...segment,
      value: props.outbound?.[segment.key] ?? 0,
    })),
  ]
  return items
    .filter((item) => item.value > 0)
    .map((item) => ({ ...item, width: (item.value / total.value) * 100 }))
})

const splitAt = computed(() => (total.value ? (props.incoming / total.value) * 100 : 0))
</script>

<template>
  <div>
    <div
      class="relative flex w-full overflow-hidden rounded-full bg-line"
      :class="compact ? 'h-1.5' : 'h-3'"
      role="img"
      :aria-label="`Entrantes ${formatNumber(incoming)}, salientes ${formatNumber(outbound?.total)}`"
    >
      <span
        v-for="part in parts"
        :key="part.key"
        class="flow-segment h-full"
        :style="{ width: `${part.width}%`, backgroundColor: part.color }"
        :title="`${part.label}: ${formatNumber(part.value)} (${formatPercent(part.value, total)})`"
      />

      <!-- Marca la frontera entrante / saliente: sin ella la barra sería una
           sucesión de colores sin eje de lectura. -->
      <span
        v-if="!compact && splitAt > 0 && splitAt < 100"
        class="pointer-events-none absolute top-0 h-full w-px bg-surface-1"
        :style="{ left: `${splitAt}%` }"
      />
    </div>

    <div
      v-if="!compact"
      class="mt-2 flex justify-between font-condensed text-[11px] uppercase tracking-[0.16em] text-muted"
    >
      <span>← Entrantes {{ formatPercent(incoming, total) }}</span>
      <span>Salientes {{ formatPercent(outbound?.total ?? 0, total) }} →</span>
    </div>
  </div>
</template>

<style scoped>
.flow-segment {
  transition: width 480ms cubic-bezier(0.22, 1, 0.36, 1);
}

@media (prefers-reduced-motion: reduce) {
  .flow-segment {
    transition: none;
  }
}
</style>
