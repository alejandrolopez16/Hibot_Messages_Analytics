/**
 * Zonas horarias disponibles en el selector del reporte.
 *
 * Se listan explícitamente en vez de exponer todas las IANA para que el usuario
 * escoja rápido y no aparezcan zonas irrelevantes. El backend valida el string
 * con `ZoneInfo`, así que agregar una zona nueva es solo sumar una línea aquí.
 */
export const TIMEZONE_OPTIONS = [
  { value: 'America/Bogota', label: 'Colombia (Bogotá) · UTC-5' },
  { value: 'America/Argentina/Buenos_Aires', label: 'Argentina (Buenos Aires) · UTC-3' },
  { value: 'America/Mexico_City', label: 'México (CDMX) · UTC-6' },
  { value: 'America/Santiago', label: 'Chile (Santiago) · UTC-4/-3' },
  { value: 'America/Lima', label: 'Perú (Lima) · UTC-5' },
  { value: 'America/Caracas', label: 'Venezuela (Caracas) · UTC-4' },
  { value: 'America/Sao_Paulo', label: 'Brasil (São Paulo) · UTC-3' },
  { value: 'America/Guayaquil', label: 'Ecuador (Guayaquil) · UTC-5' },
  { value: 'America/La_Paz', label: 'Bolivia (La Paz) · UTC-4' },
  { value: 'America/Asuncion', label: 'Paraguay (Asunción) · UTC-4/-3' },
  { value: 'America/Montevideo', label: 'Uruguay (Montevideo) · UTC-3' },
  { value: 'America/Panama', label: 'Panamá · UTC-5' },
  { value: 'America/Costa_Rica', label: 'Costa Rica · UTC-6' },
  { value: 'UTC', label: 'UTC · sin desfase' },
]

export const DEFAULT_TIMEZONE = 'America/Bogota'
