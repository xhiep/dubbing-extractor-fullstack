// localStorage middleware for Zustand
const STORAGE_KEY = 'dubbing-app-settings'

export const localStorageMiddleware = (config) => (set, get, api) => {
  // Load initial state from localStorage
  const savedState = localStorage.getItem(STORAGE_KEY)
  if (savedState) {
    try {
      const parsed = JSON.parse(savedState)
      // Only restore processingOptions, not runtime state
      if (parsed.processingOptions) {
        config.processingOptions = { ...config.processingOptions, ...parsed.processingOptions }
      }
    } catch (e) {
      console.error('Failed to load settings from localStorage:', e)
    }
  }

  // Create the store
  const store = config(
    (...args) => {
      set(...args)
      // Save processingOptions to localStorage after each update
      const state = get()
      const toSave = {
        processingOptions: state.processingOptions,
      }
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
      } catch (e) {
        console.error('Failed to save settings to localStorage:', e)
      }
    },
    get,
    api
  )

  return store
}
