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

  // Preview data
  preview: null,

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
    video_speed: 1.0,
    output_format: 'mp4',

    // TTS/Dubbing options
    enable_dub: false,
    dub_mode: 'preset',
    dub_backend_mode: 'turbo',
    dub_remote_api_base: 'http://localhost:23333/v1',
    dub_preset_voice: '',
    dub_ref_audio: '',
    dub_ref_text: '',
    dub_voice_volume: 1.35,
    dub_source_volume: 0.18,
    dub_mix_mode: 'nen_nho',
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

  setPreview: (preview) => set({ preview }),

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
