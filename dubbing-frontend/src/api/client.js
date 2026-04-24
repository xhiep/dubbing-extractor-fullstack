import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

// API methods
export const processAPI = {
  start: (data) => api.post('/process/', data),
  runStep: (stepNum, data) => api.post(`/process/step/${stepNum}`, data),
  getStatus: (taskId) => api.get(`/process/status/${taskId}`),
  cancel: (taskId) => api.post(`/process/cancel/${taskId}`),
}

export const previewAPI = {
  getInfo: (source) => api.post('/preview/', { source }),
}

export const ttsAPI = {
  checkStatus: (config) => api.post('/tts/status', config),
  listVoices: (params) => api.get('/tts/voices', { params }),
  test: (data) => api.post('/tts/test', data),
}

export default api
