import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

function getStoredTokens() {
  try {
    const raw = localStorage.getItem('tokens')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function storeTokens(tokens) {
  localStorage.setItem('tokens', JSON.stringify(tokens))
}

function clearTokens() {
  localStorage.removeItem('tokens')
}

let isRefreshing = false
let pendingRequests = []

api.interceptors.request.use((config) => {
  const tokens = getStoredTokens()
  if (tokens?.access) {
    config.headers.Authorization = `Bearer ${tokens.access}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const tokens = getStoredTokens()
      if (!tokens?.refresh) {
        clearTokens()
        return Promise.reject(error)
      }
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingRequests.push({ resolve, reject, original })
        })
      }
      try {
        isRefreshing = true
        const { data } = await axios.post('/api/auth/token/refresh/', {
          refresh: tokens.refresh,
        })
        const newTokens = { ...tokens, access: data.access }
        storeTokens(newTokens)
        pendingRequests.forEach(({ resolve, original: req }) => {
          req.headers = { ...(req.headers || {}), Authorization: `Bearer ${newTokens.access}` }
          resolve(api(req))
        })
        pendingRequests = []
        original.headers.Authorization = `Bearer ${newTokens.access}`
        return api(original)
      } catch (e) {
        clearTokens()
        pendingRequests.forEach(({ reject }) => reject(e))
        pendingRequests = []
        return Promise.reject(e)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

export const AuthAPI = {
  async login(username, password) {
    const { data } = await api.post('/auth/token/', { username, password })
    storeTokens({ access: data.access, refresh: data.refresh })
    return data
  },
  async register({ username, email, password, password2 }) {
    const { data } = await api.post('/auth/register/', {
      username,
      email,
      password,
      password2,
    })
    return data
  },
  async me() {
    const { data } = await api.get('/auth/me/')
    return data
  },
  logout() {
    clearTokens()
  },
}

export const RAGAPI = {
  async upload(files, source) {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    if (source) form.append('source', source)
    const { data } = await api.post('/documents/upload/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
  async query({ query, top_k = 4, generate = true, temperature = 0.7 }) {
    const { data } = await api.post('/query/', {
      query,
      top_k,
      generate,
      temperature,
    })
    return data
  },
}

export function getTokens() {
  return getStoredTokens()
}


