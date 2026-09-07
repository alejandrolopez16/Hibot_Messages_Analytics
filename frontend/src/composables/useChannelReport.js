import { computed, ref, shallowRef } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

/**
 * Consume POST /api/v1/analytics/channels-report.
 *
 * La consulta puede tardar decenas de segundos sobre el histórico completo, así
 * que cada llamada cancela la anterior: si el usuario cambia el filtro mientras
 * corre una consulta, la respuesta vieja no puede llegar después y pisar la
 * nueva en pantalla.
 */
export function useChannelReport() {
  const report = shallowRef(null)
  const loading = ref(false)
  const error = ref(null)

  let controller = null

  const totals = computed(() => report.value?.totals ?? null)
  const rows = computed(() => report.value?.rows ?? [])

  async function fetchReport(filters) {
    controller?.abort()
    controller = new AbortController()

    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE}/api/v1/analytics/channels-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify(buildPayload(filters)),
      })

      if (!response.ok) {
        throw new Error(await readError(response))
      }

      report.value = await response.json()
    } catch (err) {
      if (err.name === 'AbortError') return
      report.value = null
      error.value = err.message
    } finally {
      if (!controller.signal.aborted) loading.value = false
    }
  }

  return { report, rows, totals, loading, error, fetchReport }
}

function buildPayload({ mode, tenant, account, dateFrom, dateTo, timezone }) {
  return {
    tenant: mode === 'tenant' ? tenant.trim() : null,
    account: mode === 'line' ? account.trim() : null,
    // El backend interpreta una fecha sin offset en la zona indicada, así que
    // se envía el valor tal como lo escribió el usuario.
    dateFrom: `${dateFrom}T00:00:00`,
    dateTo: `${dateTo}T23:59:59.999`,
    timezone,
  }
}

async function readError(response) {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
    // Errores de validación de Pydantic: se muestra el primero, que es el que
    // el usuario puede corregir.
    if (Array.isArray(body.detail) && body.detail.length) {
      return body.detail[0].msg?.replace(/^Value error,\s*/, '') ?? 'Revisa los filtros.'
    }
  } catch {
    /* respuesta sin cuerpo JSON */
  }
  return `La consulta falló (HTTP ${response.status}).`
}
