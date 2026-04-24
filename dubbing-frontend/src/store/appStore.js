import { create } from 'zustand'

const useAppStore = create((set, get) => ({
  // Current task
  taskId: null,
  status: 'idle', // idle, queued, running, completed, failed
  currentStep: 0,
  progress: 0,
  message: '',

  // Outputs
  outputs: {},

  // Logs
  logs: [],
  maxLogs: 1000,

  // Processing options
  processingOptions: {
    source: '',
    mode: 'monolithic',
    whisper_model: 'medium',
    whisper_language: null,
    cover_mode: 'blur',
    cover_strength: 15,
    burn_subtitle: true,
    subtitle_font_scale: 1.0,
    subtitle_timing_scale: 1.0,
    subtitle_offset_sec: 0.0,
    enable_dubbing: false,
    tts_voice: 'female_north',
    video_speed: 1.0,
    output_format: 'mp4',
  },

  // Actions
  setTaskId: (taskId) => set({ taskId }),

  setStatus: (status) => set({ status }),

  setProgress: (step, progress, message) => set({
    currentStep: step,
    progress,
    message,
  }),

  setOutputs: (outputs) => set({ outputs }),

  addLog: (level, message) => set((state) => {
    const timestamp = new Date().toISOString()
    const newLog = { level, message, timestamp }
    const logs = [...state.logs, newLog]

    // Keep only last maxLogs entries
    if (logs.length > state.maxLogs) {
      logs.shift()
    }

    return { logs }
  }),

  clearLogs: () => set({ logs: [] }),

  updateProcessingOptions: (options) => set((state) => ({
    processingOptions: { ...state.processingOptions, ...options },
  })),

  reset: () => set({
    taskId: null,
    status: 'idle',
    currentStep: 0,
    progress: 0,
    message: '',
    outputs: {},
    logs: [],
  }),
}))

export default useAppStore
