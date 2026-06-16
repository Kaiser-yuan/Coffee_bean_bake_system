import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '../api/auth'

const STORAGE_KEY = 'coffee_roast_auth'

type AuthSnapshot = {
  accessToken: string
  expiresAt: string
  userId: string
  displayName: string | null
}

function readSnapshot(): AuthSnapshot | null {
  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (!raw) return null

  try {
    return JSON.parse(raw) as AuthSnapshot
  } catch {
    window.localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const snapshot = readSnapshot()
  const accessToken = ref(snapshot?.accessToken || '')
  const expiresAt = ref(snapshot?.expiresAt || '')
  const userId = ref(snapshot?.userId || '')
  const displayName = ref(snapshot?.displayName || '')
  const loading = ref(false)

  const isAuthenticated = computed(() => {
    if (!accessToken.value || !expiresAt.value) return false
    return new Date(expiresAt.value).getTime() > Date.now()
  })

  function persist() {
    const data: AuthSnapshot = {
      accessToken: accessToken.value,
      expiresAt: expiresAt.value,
      userId: userId.value,
      displayName: displayName.value,
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  }

  function clearAuth() {
    accessToken.value = ''
    expiresAt.value = ''
    userId.value = ''
    displayName.value = ''
    window.localStorage.removeItem(STORAGE_KEY)
  }

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const res = await authApi.login({ username, password })
      accessToken.value = res.access_token
      expiresAt.value = res.expires_at
      userId.value = res.user_id
      displayName.value = res.display_name || username
      persist()
    } finally {
      loading.value = false
    }
  }

  return {
    accessToken,
    expiresAt,
    userId,
    displayName,
    loading,
    isAuthenticated,
    login,
    clearAuth,
  }
})
