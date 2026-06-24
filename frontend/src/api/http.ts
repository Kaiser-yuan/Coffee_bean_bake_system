import { useAuthStore } from '../stores/auth'

export const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const isDemoMode = import.meta.env.VITE_DEMO_MODE !== 'false'

/** P0: backend version contract — checked once on first real-API call. */
export interface MetaResponse {
  service: string
  app_version: string
  git_sha: string
  api_contract_version: string
  features: string[]
}

let _meta: MetaResponse | null = null
let _metaError: string | null = null
let _metaPromise: Promise<MetaResponse> | null = null

export async function fetchMeta(): Promise<MetaResponse> {
  if (_meta) return _meta
  if (_metaError) throw new Error(_metaError)
  if (_metaPromise) return _metaPromise

  const base = apiBaseUrl.replace(/\/api\/v1$/, '')
  _metaPromise = fetch(`${base}/api/v1/meta`)
    .then(async (r) => {
      if (!r.ok) throw new Error(`后端不可达 (${r.status})`)
      const data = await r.json()
      _meta = data as MetaResponse
      _metaPromise = null
      return _meta
    })
    .catch((e) => {
      _metaPromise = null
      _metaError = `后端版本检查失败：${e.message}`
      throw new Error(_metaError)
    })
  return _metaPromise
}

/** Ensure backend supports a required feature. Throws if not. */
export async function requireFeature(feature: string): Promise<void> {
  if (isDemoMode) return
  const meta = await fetchMeta()
  if (!meta.features.includes(feature)) {
    throw new Error(
      `后端进程版本过旧：当前不支持 ${feature}。\n请重启 8000 端口后端，而不是重新上传 CSV。\n当前 SHA: ${meta.git_sha}`,
    )
  }
}

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
