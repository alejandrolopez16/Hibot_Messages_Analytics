<script setup>
import { computed, onMounted, reactive } from 'vue'
import FlowStrip from './FlowStrip.vue'
import KpiCard from './KpiCard.vue'
import OutboundDonut from './OutboundDonut.vue'
import { useChannelReport } from '../composables/useChannelReport'
import { INBOUND_COLOR, OUTBOUND_SEGMENTS, formatNumber, formatPercent } from '../constants/outbound'
import { DEFAULT_TIMEZONE, TIMEZONE_OPTIONS } from '../constants/timezones'

const MAX_DAYS = 31
const OBJECT_ID = /^[a-f\d]{24}$/i

const { report, rows, totals, loading, error, fetchReport } = useChannelReport()

const filters = reactive({
  mode: 'tenant',
  tenant: '',
  account: '',
  dateFrom: isoDate(-7),
  dateTo: isoDate(0),
  timezone: DEFAULT_TIMEZONE,
})

const rangeDays = computed(() => {
  const from = new Date(`${filters.dateFrom}T00:00:00`)
  const to = new Date(`${filters.dateTo}T00:00:00`)
  return Math.round((to - from) / 86_400_000) + 1
})

/**
 * Validación en el cliente antes de disparar una consulta cara: un rango
 * inválido no debería costar un viaje al clúster para volver como 422.
 */
const validationError = computed(() => {
  if (filters.mode === 'tenant') {
    const value = filters.tenant.trim()
    if (!value) return 'Escribe el id del tenant.'
    if (!OBJECT_ID.test(value)) return 'El id del tenant tiene 24 caracteres hexadecimales.'
  } else {
    const value = filters.account.trim()
    if (!value) return 'Escribe el número de línea.'
  }
  if (rangeDays.value <= 0) return 'La fecha final debe ser posterior a la inicial.'
  if (rangeDays.value > MAX_DAYS) {
    return `El rango máximo es de un mes. Seleccionaste ${rangeDays.value} días.`
  }
  return null
})

const outboundShare = computed(() => {
  const t = totals.value
  if (!t) return ''
  const traffic = t.incoming + t.outbound.total
  return `${formatPercent(t.outbound.total, traffic)} del tráfico total`
})

const templateShare = computed(() => {
  const t = totals.value
  if (!t) return ''
  return `${formatPercent(t.outbound.template, t.outbound.total)} de los salientes`
})

const messagesPerConversation = computed(() => {
  const t = totals.value
  if (!t || !t.conversations) return '—'
  return ((t.incoming + t.outbound.total) / t.conversations).toFixed(1)
})

const activeRows = computed(() =>
  rows.value.filter((row) => row.conversations || row.incoming || row.outbound.total),
)

const idleCount = computed(() => rows.value.length - activeRows.value.length)

function submit() {
  if (validationError.value || loading.value) return
  fetchReport({ ...filters })
}

function isoDate(offsetDays) {
  const date = new Date()
  date.setDate(date.getDate() + offsetDays)
  return date.toISOString().slice(0, 10)
}

onMounted(() => {
  // Sin filtro no hay consulta: la pantalla arranca vacía a propósito para no
  // lanzar una agregación de varios minutos al abrir el dashboard.
})
</script>

<template>
  <div class="min-h-screen bg-surface-0 px-4 py-8 text-ink-200 sm:px-8">
    <div class="mx-auto max-w-6xl space-y-6">
      <header>
        <p class="font-condensed text-[11px] uppercase tracking-[0.22em] text-muted">
          Hibot · Analítica de mensajes
        </p>
        <h1 class="mt-1 font-condensed text-3xl font-semibold tracking-tight text-ink-50">
          Tráfico por canal/Tenant
        </h1>
      </header>

      <!-- Filtros -->
      <section class="rounded-lg border border-line bg-surface-1 p-5">
        <div class="flex flex-wrap items-end gap-4">
          <div>
            <label class="mb-1.5 block font-condensed text-[11px] uppercase tracking-[0.18em] text-muted">
              Filtrar por
            </label>
            <div class="inline-flex rounded-md border border-line p-0.5" role="group">
              <button
                v-for="mode in ['tenant', 'line']"
                :key="mode"
                type="button"
                class="rounded px-3 py-1.5 text-sm capitalize transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-aqua"
                :class="
                  filters.mode === mode
                    ? 'bg-line text-ink-50'
                    : 'text-muted hover:text-ink-200'
                "
                :aria-pressed="filters.mode === mode"
                @click="filters.mode = mode"
              >
                {{ mode === 'tenant' ? 'Tenant' : 'Línea' }}
              </button>
            </div>
          </div>

          <div class="min-w-[19rem] flex-1">
            <label
              for="scope-id"
              class="mb-1.5 block font-condensed text-[11px] uppercase tracking-[0.18em] text-muted"
            >
              {{ filters.mode === 'tenant' ? 'Id de tenant' : 'Número de línea' }}
            </label>
            <input
              v-if="filters.mode === 'tenant'"
              id="scope-id"
              v-model="filters.tenant"
              type="text"
              placeholder="6696761e3c8a4cfe71502bbc"
              class="w-full rounded-md border border-line bg-surface-0 px-3 py-2 font-mono text-sm text-ink-50 placeholder:text-muted/60 focus:border-aqua focus:outline-none"
            />
            <input
              v-else
              id="scope-id"
              v-model="filters.account"
              type="text"
              placeholder="573001234567"
              class="w-full rounded-md border border-line bg-surface-0 px-3 py-2 font-mono text-sm text-ink-50 placeholder:text-muted/60 focus:border-aqua focus:outline-none"
            />
          </div>

          <div>
            <label
              for="date-from"
              class="mb-1.5 block font-condensed text-[11px] uppercase tracking-[0.18em] text-muted"
            >
              Desde
            </label>
            <input
              id="date-from"
              v-model="filters.dateFrom"
              type="date"
              class="rounded-md border border-line bg-surface-0 px-3 py-2 font-mono text-sm text-ink-50 focus:border-aqua focus:outline-none"
            />
          </div>

          <div>
            <label
              for="date-to"
              class="mb-1.5 block font-condensed text-[11px] uppercase tracking-[0.18em] text-muted"
            >
              Hasta
            </label>
            <input
              id="date-to"
              v-model="filters.dateTo"
              type="date"
              class="rounded-md border border-line bg-surface-0 px-3 py-2 font-mono text-sm text-ink-50 focus:border-aqua focus:outline-none"
            />
          </div>

          <div>
            <label
              for="timezone"
              class="mb-1.5 block font-condensed text-[11px] uppercase tracking-[0.18em] text-muted"
            >
              Zona horaria
            </label>
            <select
              id="timezone"
              v-model="filters.timezone"
              class="rounded-md border border-line bg-surface-0 px-3 py-2 font-mono text-sm text-ink-50 focus:border-aqua focus:outline-none"
            >
              <option v-for="tz in TIMEZONE_OPTIONS" :key="tz.value" :value="tz.value">
                {{ tz.label }}
              </option>
            </select>
          </div>

          <button
            type="button"
            class="rounded-md bg-aqua px-5 py-2 text-sm font-medium text-surface-0 transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-aqua"
            :disabled="Boolean(validationError) || loading"
            @click="submit"
          >
            {{ loading ? 'Consultando…' : 'Generar reporte' }}
          </button>
        </div>

        <p class="mt-3 text-xs text-muted">
          <span v-if="validationError" class="text-rose">{{ validationError }}</span>
          <span v-else>
           Consulta: {{ rangeDays }} {{ rangeDays === 1 ? 'día' : 'días' }}, hora de {{ filters.timezone }}.
            Máximo un mes por consulta.
          </span>
        </p>
      </section>

      <!-- Error del servidor -->
      <div
        v-if="error"
        class="rounded-lg border border-rose/40 bg-rose/10 px-4 py-3 text-sm text-ink-200"
        role="alert"
      >
        {{ error }}
      </div>

      <!-- Resultados -->
      <template v-if="loading || report">
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="Conversaciones"
            :value="totals?.conversations ?? 0"
            :caption="`${messagesPerConversation} mensajes por conversación`"
            accent="#8994AB"
            :loading="loading"
          />
          <KpiCard
            label="Mensajes entrantes"
            :value="totals?.incoming ?? 0"
            caption="Enviados por el contacto"
            :accent="INBOUND_COLOR"
            :loading="loading"
          />
          <KpiCard
            label="Mensajes salientes"
            :value="totals?.outbound.total ?? 0"
            :caption="outboundShare"
            accent="#F0B429"
            :loading="loading"
          />
          <KpiCard
            label="Salientes por template"
            :value="totals?.outbound.template ?? 0"
            :caption="templateShare"
            accent="#F0B429"
            :loading="loading"
          />
        </div>

        <section v-if="totals && !loading" class="rounded-lg border border-line bg-surface-1 p-5">
          <h2 class="mb-4 font-condensed text-[11px] uppercase tracking-[0.18em] text-muted">
            Flujo del periodo
          </h2>
          <FlowStrip :incoming="totals.incoming" :outbound="totals.outbound" />
        </section>

        <OutboundDonut v-if="totals && !loading" :outbound="totals.outbound" />

        <!-- Detalle por canal -->
        <section class="overflow-hidden rounded-lg border border-line bg-surface-1">
          <header class="flex items-baseline justify-between border-b border-line px-5 py-4">
            <h2 class="font-condensed text-[11px] uppercase tracking-[0.18em] text-muted">
              Detalle por canal
            </h2>
            <span v-if="report" class="font-mono text-xs tabular-nums text-muted">
              {{ activeRows.length }} con tráfico<template v-if="idleCount">
                · {{ idleCount }} sin actividad</template
              >
            </span>
          </header>

          <div v-if="loading" class="space-y-2 p-5">
            <div v-for="n in 4" :key="n" class="h-10 animate-pulse rounded bg-line" />
          </div>

          <div v-else-if="!activeRows.length" class="px-5 py-12 text-center text-sm text-muted">
            Ningún canal registró tráfico en este rango. Prueba con otras fechas.
          </div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-line font-condensed text-[11px] uppercase tracking-[0.16em] text-muted">
                  <th class="px-5 py-2.5 text-left font-medium">Canal</th>
                  <th class="px-3 py-2.5 text-right font-medium">Conv.</th>
                  <th class="px-3 py-2.5 text-right font-medium">Entrantes</th>
                  <th class="px-3 py-2.5 text-right font-medium">Salientes</th>
                  <th class="px-3 py-2.5 text-right font-medium">Template</th>
                  <th class="w-40 px-5 py-2.5 text-left font-medium">Composición</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in activeRows"
                  :key="row.channelId"
                  class="border-b border-line/60 last:border-0 hover:bg-line/30"
                >
                  <td class="px-5 py-3">
                    <div class="flex items-center gap-2">
                      <span class="text-ink-50">{{ row.name || 'Canal sin nombre' }}</span>
                      <span
                        v-if="row.type"
                        class="rounded border border-line px-1.5 py-0.5 font-condensed text-[10px] uppercase tracking-wider text-muted"
                      >
                        {{ row.type }}
                      </span>
                    </div>
                    <span class="font-mono text-xs text-muted">{{ row.account || row.channelId }}</span>
                  </td>
                  <td class="px-3 py-3 text-right font-mono tabular-nums">
                    {{ formatNumber(row.conversations) }}
                  </td>
                  <td class="px-3 py-3 text-right font-mono tabular-nums">
                    {{ formatNumber(row.incoming) }}
                  </td>
                  <td class="px-3 py-3 text-right font-mono tabular-nums">
                    {{ formatNumber(row.outbound.total) }}
                  </td>
                  <td class="px-3 py-3 text-right font-mono tabular-nums text-amber">
                    {{ formatNumber(row.outbound.template) }}
                  </td>
                  <td class="px-5 py-3">
                    <FlowStrip :incoming="row.incoming" :outbound="row.outbound" compact />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <p v-if="report && !loading" class="text-right font-mono text-[11px] text-muted">
          {{ formatNumber(report.elapsedMs) }} ms
          <template v-if="report.cached"> · desde caché</template>
        </p>
      </template>

      <!-- Estado inicial -->
      <section
        v-else
        class="rounded-lg border border-dashed border-line px-6 py-16 text-center"
      >
        <p class="text-ink-50">Elige un tenant o una línea y genera el reporte.</p>
        <p class="mx-auto mt-2 max-w-md text-sm text-muted">
          La consulta recorre el histórico de producción, así que puede tardar.
          Rangos cortos responden más rápido.
        </p>
      </section>
    </div>
  </div>
</template>
