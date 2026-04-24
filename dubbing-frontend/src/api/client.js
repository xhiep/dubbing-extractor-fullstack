import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5 minutes for preview render
  headers: {
    'Content-Type': 'application/json',
  },
})

export const processAPI = {
  start: (options) => apiClient.post('/process/', {
    ...options,
    enable_dub: options.enable_dub,
    enable_dubbing: options.enable_dub,
  }).then(res => res.data),
  cancel: (taskId) => apiClient.post(`/process/cancel/${taskId}`).then(res => res.data),
  status: (taskId) => apiClient.get(`/process/status/${taskId}`).then(res => res.data),
  runStep: (stepNum, data) => apiClient.post(`/process/step/${stepNum}`, data).then(res => res.data),
  getStepSrt: (taskId) => apiClient.get(`/process/step-srt/${taskId}`).then(res => res.data),
  saveStepSrt: (taskId, content) => apiClient.post(`/process/step-srt/${taskId}`, { content }).then(res => res.data),
}

export const previewAPI = {
  getInfo: (source) => apiClient.post('/preview', { source }).then(res => res.data),
}

export const ttsAPI = {
  checkStatus: (payload) => apiClient.post('/tts/status', payload).then(res => res.data),
  listVoices: (params) => apiClient.get('/tts/voices', { params }).then(res => res.data),
  test: (payload) => apiClient.post('/tts/test', payload).then(res => res.data),
  checkRefAudio: (path) => apiClient.get('/tts/ref-audio-status', { params: { path } }).then(res => res.data),
}
