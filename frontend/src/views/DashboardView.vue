<script setup>
import ChannelAnalyticsDashboard from '../components/ChannelAnalyticsDashboard.vue'
import { useAuth } from '../composables/useAuth'

const { user, logout } = useAuth()
</script>

<template>
  <div>
    <!-- Barra superior con info del usuario y botón de logout -->
    <div class="border-b border-line bg-surface-1 px-4 py-2 sm:px-8">
      <div class="mx-auto flex max-w-6xl items-center justify-between">
        <span class="font-condensed text-[11px] uppercase tracking-[0.18em] text-muted">
          {{ user?.full_name ?? user?.username }}
        </span>
        <button
          type="button"
          class="font-condensed text-[11px] uppercase tracking-[0.18em] text-muted transition-colors hover:text-ink-200"
          @click="logout"
        >
          Cerrar sesión
        </button>
      </div>
    </div>

    <ChannelAnalyticsDashboard />
  </div>
</template>
