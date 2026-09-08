/**
 * Vocabulario visual del reporte.
 *
 * El color codifica dirección, no decoración: el entrante tiene su propia
 * familia (aqua) y los cuatro orígenes de saliente comparten una familia cálida
 * distinguible entre sí. Donut, barra de flujo y tabla usan estas mismas claves,
 * así que un color significa lo mismo en toda la pantalla.
 */

export const INBOUND_COLOR = '#3FD0C9'

export const CONSECUTIVE_COLOR_BOT = '#8B7BF0'
export const CONSECUTIVE_COLOR_AGENT = '#4A9EFF'
export const CONSECUTIVE_LABEL = 'Mensajes continuos'
export const CONSECUTIVE_HINT = 'Segundo mensaje seguido de BOT o AGENT sin respuesta del contacto'

export const OUTBOUND_SEGMENTS = [
  { key: 'template', label: 'Template', color: '#F0B429', hint: 'Salientes con plantilla (HSM)' },
  { key: 'bot', label: 'Bot', color: '#8B7BF0', hint: 'Respuestas automáticas sin plantilla' },
  { key: 'agent', label: 'Agente', color: '#4A9EFF', hint: 'Escritos por una persona' },
  { key: 'external', label: 'External', color: '#E9668B', hint: 'Inyectados por integraciones' },
  { key: 'other', label: 'Otro', color: '#5B6680', hint: 'Orígenes no clasificados' },
]

// Metadatos por categoría de template (WhatsApp Cloud API + `UNKNOWN` para
// mensajes con template sin `category`).
export const TEMPLATE_CATEGORY_META = {
  MARKETING: { label: 'Marketing', color: '#F0B429' },
  UTILITY: { label: 'Utility', color: '#4A9EFF' },
  AUTHENTICATION: { label: 'Authentication', color: '#8B7BF0' },
  SERVICE: { label: 'Service', color: '#3FD0C9' },
  UNKNOWN: { label: 'Sin categoría', color: '#5B6680' },
}

// Colores para categorías nuevas que la API pueda devolver.
const TEMPLATE_CATEGORY_FALLBACK_PALETTE = [
  '#E9668B',
  '#F7A072',
  '#7CD6FC',
  '#B4E197',
  '#F9A03F',
]

export function resolveTemplateCategory(name, index = 0) {
  return (
    TEMPLATE_CATEGORY_META[name] ?? {
      label: name,
      color:
        TEMPLATE_CATEGORY_FALLBACK_PALETTE[index % TEMPLATE_CATEGORY_FALLBACK_PALETTE.length],
    }
  )
}

const formatter = new Intl.NumberFormat('es-CO')

export function formatNumber(value) {
  return formatter.format(value ?? 0)
}

export function formatPercent(part, total) {
  if (!total) return '0%'
  const pct = (part / total) * 100
  return `${pct < 1 && pct > 0 ? pct.toFixed(1) : Math.round(pct)}%`
}
