<script setup>
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import { ArcElement, Chart as ChartJS, Legend, Tooltip } from 'chart.js'
import { OUTBOUND_SEGMENTS, formatNumber, formatPercent } from '../constants/outbound'

ChartJS.register(ArcElement, Tooltip, Legend)

const props = defineProps({
  outbound: { type: Object, required: true },
})

const segments = computed(() =>
  OUTBOUND_SEGMENTS.map((segment) => ({
    ...segment,
    value: props.outbound?.[segment.key] ?? 0,
  })).filter((segment) => segment.value > 0),
)

const total = computed(() => props.outbound?.total ?? 0)

const chartData = computed(() => ({
  labels: segments.value.map((segment) => segment.label),
  datasets: [
    {
      data: segments.value.map((segment) => segment.value),
      backgroundColor: segments.value.map((segment) => segment.color),
      borderWidth: 0,
      hoverOffset: 6,
      spacing: 2,
    },
  ],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '72%',
  // La leyenda va aparte porque necesita mostrar valor absoluto y porcentaje,
  // que es lo que se compara entre canales; la de Chart.js solo da la etiqueta.
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1A2030',
      borderColor: '#2A3244',
      borderWidth: 1,
      padding: 10,
      titleFont: { family: 'Inter, sans-serif', size: 12 },
      bodyFont: { family: 'IBM Plex Mono, monospace', size: 12 },
      displayColors: true,
      callbacks: {
        label(context) {
          const value = context.parsed
          const sum = context.dataset.data.reduce((acc, item) => acc + item, 0)
          return ` ${formatNumber(value)} · ${formatPercent(value, sum)}`
        },
      },
    },
  },
}
</script>

<template>
  <section class="rounded-lg border border-line bg-surface-1 p-5">
    <header class="flex items-baseline justify-between">
      <h2 class="font-condensed text-[11px] uppercase tracking-[0.18em] text-muted">
        Composición del saliente
      </h2>
      <span class="font-mono text-xs tabular-nums text-muted">{{ formatNumber(total) }} msj</span>
    </header>

    <div v-if="!segments.length" class="py-14 text-center text-sm text-muted">
      No hubo mensajes salientes en este rango. Amplía las fechas o revisa el canal.
    </div>

    <div v-else class="mt-5 flex flex-col gap-6 sm:flex-row sm:items-center">
      <div class="relative mx-auto h-44 w-44 shrink-0">
        <Doughnut :data="chartData" :options="chartOptions" />
        <!-- El centro del donut no se desperdicia: lleva el total que da sentido
             a los porcentajes de la leyenda. -->
        <div class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span class="font-mono text-xl leading-none tabular-nums text-ink-50">
            {{ formatNumber(total) }}
          </span>
          <span class="mt-1 font-condensed text-[10px] uppercase tracking-[0.18em] text-muted">
            Salientes
          </span>
        </div>
      </div>

      <ul class="flex-1 space-y-2.5">
        <li v-for="segment in segments" :key="segment.key" class="flex items-center gap-3">
          <span class="h-2.5 w-2.5 shrink-0 rounded-sm" :style="{ backgroundColor: segment.color }" />
          <span class="flex-1 text-sm text-ink-200" :title="segment.hint">{{ segment.label }}</span>
          <span class="font-mono text-sm tabular-nums text-ink-50">
            {{ formatNumber(segment.value) }}
          </span>
          <span class="w-11 text-right font-mono text-xs tabular-nums text-muted">
            {{ formatPercent(segment.value, total) }}
          </span>
        </li>
      </ul>
    </div>
  </section>
</template>
