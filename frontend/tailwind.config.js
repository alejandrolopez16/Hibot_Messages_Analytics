/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      colors: {
        // Superficies grafito-azul: es una consola que se mira durante horas,
        // no una landing. El contraste vive en los datos, no en el fondo.
        surface: { 0: '#12161F', 1: '#1A2030' },
        line: '#2A3244',
        ink: { 50: '#E6E9F0', 200: '#C2C9D8' },
        muted: '#8994AB',
        // Acentos semánticos: aqua = entrante, la familia cálida = saliente.
        aqua: '#3FD0C9',
        amber: '#F0B429',
        violet: '#8B7BF0',
        azure: '#4A9EFF',
        rose: '#E9668B',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        condensed: ['"IBM Plex Sans Condensed"', 'Inter', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
