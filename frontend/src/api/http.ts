import { useAuthStore } from '../stores/auth'

export const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const isDemoMode = import.meta.env.VITE_DEMO_MODE !== 'false'

export class ApiError extends Error {
  status: number
  code?: string
  details?: unknown
  requestId?: string

  constructor(message: string, status: number, code?: string, details?: unknown, requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.requestId = requestId
  }
}

type RequestOptions = {
  method?: string
  body?: unknown
  auth?: boolean
  timeoutMs?: number
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), options.timeoutMs ?? 15000)
  const headers = new Headers()

  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (options.auth) {
    const auth = useAuthStore()
    if (auth.accessToken) {
      headers.set('Authorization', `Bearer ${auth.accessToken}`)
    }
  }

  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body instanceof FormData
        ? options.body
        : options.body === undefined
          ? undefined
          : JSON.stringify(options.body),
      signal: controller.signal,
    })

    if (response.status === 204) {
      return undefined as T
    }

    const contentType = response.headers.get('content-type') || ''
    const data = contentType.includes('application/json')
      ? await response.json()
      : await response.text()

    if (!response.ok) {
      if (response.status === 401) {
        useAuthStore().clearAuth()
      }
      if (data && typeof data === 'object') {
        throw new ApiError(
          data.message || data.detail || `请求失败 (${response.status})`,
          response.status,
          data.code,
          data.details,
          data.request_id,
        )
      }
      throw new ApiError(String(data || `请求失败 (${response.status})`), response.status)
    }

    return data as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('请求超时，请稍后重试', 0)
    }
    throw new ApiError('网络连接失败，请确认后端服务已启动', 0)
  } finally {
    window.clearTimeout(timeout)
  }
}
