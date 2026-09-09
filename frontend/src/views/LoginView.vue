<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { login } = useAuth()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref(null)

async function submit() {
  if (loading.value) return
  error.value = null
  loading.value = true
  try {
    await login(username.value.trim(), password.value)
    router.push('/')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-surface-0 px-4">
    <div class="w-full max-w-sm">
      <!-- Header -->
      <div class="mb-8 text-center">
        <p class="font-condensed text-[11px] uppercase tracking-[0.22em] text-muted">
          Hibot · Analítica de mensajes
        </p>
        <h1 class="mt-2 font-condensed text-3xl font-semibold tracking-tight text-ink-50">
          Iniciar sesión
        </h1>
      </div>

      <!-- Card -->
      <div class="rounded-lg border border-line bg-surface-1 p-6">
        <form @submit.prevent="submit" class="space-y-4">
          <div>
            <label
              for="username"
              class="mb-1.5 block font-condensed text-[11px] uppercase tracking-[0.18em] text-muted"
            >
              Usuario
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              autocomplete="username"
              placeholder="admin"
              class="w-full rounded-md border border-line bg-surface-0 px-3 py-2 font-mono text-sm text-ink-50 placeholder:text-muted/60 focus:border-aqua focus:outline-none"
              :disabled="loading"
            />
          </div>

          <div>
            <label
              for="password"
              class="mb-1.5 block font-condensed text-[11px] uppercase tracking-[0.18em] text-muted"
            >
              Contraseña
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              class="w-full rounded-md border border-line bg-surface-0 px-3 py-2 font-mono text-sm text-ink-50 placeholder:text-muted/60 focus:border-aqua focus:outline-none"
              :disabled="loading"
            />
          </div>

          <div
            v-if="error"
            class="rounded-md border border-rose/40 bg-rose/10 px-3 py-2 text-sm text-ink-200"
            role="alert"
          >
            {{ error }}
          </div>

          <button
            type="submit"
            class="w-full rounded-md bg-aqua px-5 py-2.5 text-sm font-medium text-surface-0 transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-aqua"
            :disabled="!username.trim() || !password || loading"
          >
            {{ loading ? 'Verificando…' : 'Entrar' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
