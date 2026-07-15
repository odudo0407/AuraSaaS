/**
 * HTTP request wrapper — fetch-based, with global error handling,
 * automatic token refresh, and 401 redirect.
 */

const BASE_URL = ''

// --- internal helpers -------------------------------------------------------

function _authHeaders() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function _handleAuthExpired() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  window.dispatchEvent(new CustomEvent('aurasaas:auth-expired'))
}

/** In-flight refresh promise — prevents concurrent refresh calls. */
let _refreshPromise = null

async function _tryRefreshToken() {
  if (_refreshPromise) return _refreshPromise

  const oldToken = localStorage.getItem('token')
  if (!oldToken) return null

  _refreshPromise = (async () => {
    try {
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${oldToken}` },
      })
      if (!res.ok) return null
      const payload = await res.json()
      const newToken = payload?.data?.access_token
      if (newToken) {
        localStorage.setItem('token', newToken)
        if (payload.data.username) {
          localStorage.setItem('user', JSON.stringify({
            username: payload.data.username,
            email: payload.data.email,
          }))
        }
        return newToken
      }
    } catch {
      // refresh failed
    } finally {
      _refreshPromise = null
    }
    return null
  })()

  return _refreshPromise
}

function _resolveContentType(body, headers) {
  if (body instanceof FormData) return
  if (body instanceof URLSearchParams) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    return
  }
  if (body !== undefined && body !== null) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json'
  }
}

/**
 * Show a global error toast via a custom event.
 */
export function showError(message, detail = '') {
  window.dispatchEvent(new CustomEvent('aurasaas:error', { detail: { message, detail } }))
}

// --- public API -------------------------------------------------------------

/**
 * Fetch wrapper with token refresh and error interception.
 *
 * - On 401: tries token refresh; on success retries the request; on failure clears auth
 * - On other HTTP errors: dispatches `aurasaas:error` and throws
 * - On network failure: dispatches `aurasaas:error` and throws
 *
 * Returns the full parsed JSON response (e.g. `{code, data, message, trace_id}`).
 *
 *    const res = await request('/api/dashboard/stores')
 *    const stores = res.data
 *
 * @param {string} url
 * @param {object} [options]
 * @returns {Promise<object>} parsed JSON response body
 */
export async function request(url, options = {}) {
  const fullUrl = `${BASE_URL}${url}`
  const headers = { ...options.headers, ..._authHeaders() }

  _resolveContentType(options.body, headers)

  let res
  try {
    res = await fetch(fullUrl, { ...options, headers })
  } catch (networkError) {
    showError('Network error', networkError.message)
    throw networkError
  }

  // Attempt token refresh on 401 before giving up
  if (res.status === 401) {
    const newToken = await _tryRefreshToken()
    if (newToken) {
      // Retry the original request with refreshed token
      const retryHeaders = { ...options.headers, Authorization: `Bearer ${newToken}` }
      _resolveContentType(options.body, retryHeaders)
      try {
        res = await fetch(fullUrl, { ...options, headers: retryHeaders })
      } catch (networkError) {
        showError('Network error', networkError.message)
        throw networkError
      }
      if (res.ok) return res.json().catch(() => null)
    }
    // Refresh failed or retry still 401
    _handleAuthExpired()
    const body = await res.json().catch(() => ({}))
    throw new Error(body.message || body.detail || 'Authentication required')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const msg = body.detail || body.message || `HTTP ${res.status}`
    showError('Request failed', msg)
    throw new Error(msg)
  }

  return res.json().catch(() => null)
}

export async function uploadFile(url, formData) {
  return request(url, { method: 'POST', body: formData })
}

export async function* streamSSE(url, options = {}) {
  const fetchOptions = { ...options }
  const headers = { ...options.headers, ..._authHeaders() }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json'
  }
  fetchOptions.headers = headers

  let res
  try {
    res = await fetch(url, fetchOptions)
  } catch (networkError) {
    showError('SSE connection error', networkError.message)
    throw networkError
  }

  if (res.status === 401) {
    _handleAuthExpired()
    return
  }

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}))
    throw new Error(errBody.detail || errBody.message || `SSE HTTP ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        try {
          yield JSON.parse(data)
        } catch {
          yield { raw: data }
        }
      }
    }
  }
}
