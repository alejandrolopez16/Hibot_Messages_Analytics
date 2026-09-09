import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

const TOKEN_KEY = 'hibot_token'
const USER_KEY = 'hibot_user'

// Estado reactivo global (se comparte entre todos los componentes que importen este composable)
const token = ref(localStorage.getItem(TOKEN_KEY) ?? null)
const user = ref(JSON.parse(localStorage.getItem(USER_KEY) ?? 'null'))

export function useAuth() {
  const router = useRouter()

  const isAuthenticated = computed(() => !!token.value)

  async function login(username, password) {
    const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })

    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(body.detail ?? 'Credenciales incorrectas.')
    }

    const data = await response.json()
    token.value = data.access_token
    user.value = { username: data.username, full_name: data.full_name }

    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    router.push('/login')
  }

  function getToken() {
    return token.value
  }

  return { isAuthenticated, user, login, logout, getToken }
}
