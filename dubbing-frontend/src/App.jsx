import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Clapperboard, FileText, Loader2, Mic2, Moon, Settings2, Sun, Trash2 } from 'lucide-react'
import useAppStore from './store/appStore'
import useWebSocket from './hooks/useWebSocket'
import { useProcessing } from './hooks/useProcessing'
import { systemAPI, ttsAPI } from './api/client'
import SourceTab from './components/SourceTab'
import AdjustTab from './components/AdjustTab'
import DubTab from './components/DubTab'
import LogTab from './components/LogTab'
import StatusBar from './components/StatusBar'
import ProgressBar from './components/ProgressBar'
import StepByStepPanel from './components/StepByStepPanel'
import OutputPanel from './components/OutputPanel'

function App() {
  const [activeTab, setActiveTab] = useState('source')
  const [cleaningStorage, setCleaningStorage] = useState(false)
  const { connected } = useWebSocket()
  const {
    status,
    currentStep,
    progress,
    message,
    processingOptions,
    theme,
    setTheme,
    updateProcessingOptions,
  } = useAppStore()
  const { start, cancel, isStarting } = useProcessing()

  const isStepByStepMode = processingOptions.mode === 'step-by-step'
  const tabs = [
    { id: 'source', label: 'Nguồn Video', icon: Clapperboard },
    { id: 'adjust', label: 'Điều Chỉnh', icon: Settings2 },
    { id: 'dub', label: 'Lồng Tiếng', icon: Mic2 },
    { id: 'log', label: 'Nhật Ký', icon: FileText },
  ]

  const isProcessing = status === 'running' || status === 'queued'
  const isDark = theme === 'dark'

  useEffect(() => {
    document.documentElement.classList.remove('theme-light', 'theme-dark')
    document.documentElement.classList.add(isDark ? 'theme-dark' : 'theme-light')
    document.documentElement.style.colorScheme = isDark ? 'dark' : 'light'
  }, [isDark])

  useEffect(() => {
    let cancelled = false

    const verifyPersistedRefAudio = async () => {
      const refAudioPath = processingOptions.dub_ref_audio?.trim()
      if (!refAudioPath) return

      try {
        const result = await ttsAPI.checkRefAudio(refAudioPath)
        if (!cancelled && (!result.exists || !result.allowed)) {
          updateProcessingOptions({
            dub_ref_audio: '',
            dub_ref_text: '',
          })
          toast.error('File giong mau da mat hoac path khong hop le. Setting cu da duoc xoa.')
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to verify persisted ref audio:', error)
        }
      }
    }

    verifyPersistedRefAudio()

    return () => {
      cancelled = true
    }
  }, [processingOptions.dub_ref_audio, updateProcessingOptions])

  const handleCleanupStorage = async () => {
    setCleaningStorage(true)
    try {
      const result = await systemAPI.cleanupStorage()
      toast.success(result.message || 'Da don dep cache/temp.')
    } catch (error) {
      console.error('Failed to clean storage:', error)
      toast.error(error.response?.data?.detail || error.message)
    } finally {
      setCleaningStorage(false)
    }
  }

  return (
    <div className="app-shell min-h-screen bg-apple-gray text-apple-ink font-sf-text">
      <header className="app-header bg-white border-b border-apple-border-soft px-8 py-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <h1 className="text-promo font-sf-display text-apple-ink leading-tight">
                Dubbing Extractor v3
              </h1>
              <p className="text-control text-apple-gray-secondary">
                Web-based video processing with real-time updates
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-3">
              <div className="surface-muted flex items-center gap-2 px-3 py-2 rounded-apple-pill">
                <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-control text-apple-gray-secondary font-medium">
                  {connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>

              <button
                type="button"
                onClick={() => setTheme(isDark ? 'light' : 'dark')}
                className="btn btn-tertiary btn-pill flex items-center gap-2 px-4 py-2"
                aria-label={isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}
                title={isDark ? 'Light mode' : 'Dark mode'}
              >
                {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                {isDark ? 'Light' : 'Dark'}
              </button>

              <button
                type="button"
                onClick={handleCleanupStorage}
                disabled={cleaningStorage}
                className="btn btn-tertiary btn-pill flex items-center gap-2 px-4 py-2"
                title="Xoa preview cache, preview render va file tam"
              >
                {cleaningStorage ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                {cleaningStorage ? 'Dang Don' : 'Don Cache/Temp'}
              </button>

              {isStepByStepMode ? (
                <div className="status-chip px-4 py-2 rounded-apple-md">
                  <span className="text-control text-blue-600 font-medium">
                    Step-by-Step Mode - Chạy từng bước bên dưới
                  </span>
                </div>
              ) : isProcessing ? (
                <button
                  onClick={() => cancel()}
                  className="btn bg-red-600 hover:bg-red-700 text-white rounded-apple-md"
                >
                  Hủy Xử Lý
                </button>
              ) : (
                <button
                  onClick={() => start()}
                  disabled={isStarting}
                  className="btn btn-primary rounded-apple-md"
                >
                  {isStarting ? 'Đang Khởi Động...' : 'Bắt Đầu Xử Lý'}
                </button>
              )}
            </div>
          </div>

          {isProcessing && (
            <div className="mt-6">
              <ProgressBar
                status={status}
                progress={progress}
                step={currentStep}
                message={message}
              />
            </div>
          )}
        </div>
      </header>

      <div className="app-tabs border-b border-apple-border-soft bg-white sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-8">
          <div className="flex gap-2">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`tab-button flex items-center gap-2 px-6 py-4 font-semibold text-body transition-all border-b-2 -mb-px ${
                    activeTab === tab.id
                      ? 'border-apple-blue text-apple-blue'
                      : 'border-transparent text-apple-gray-secondary hover:text-apple-ink hover:border-apple-border-soft'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <main className="py-8 px-8">
        <div className="max-w-7xl mx-auto">
          {isStepByStepMode && (
            <div className="mb-8">
              <StepByStepPanel />
            </div>
          )}

          {activeTab === 'source' && <SourceTab />}
          {activeTab === 'adjust' && <AdjustTab />}
          {activeTab === 'dub' && <DubTab />}
          {activeTab === 'log' && <LogTab />}

          <OutputPanel />
        </div>
      </main>

      <StatusBar />
    </div>
  )
}

export default App
