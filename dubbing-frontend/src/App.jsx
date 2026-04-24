import { useState } from 'react'
import useAppStore from './store/appStore'
import useWebSocket from './hooks/useWebSocket'
import { useProcessing } from './hooks/useProcessing'
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
  const { connected } = useWebSocket()
  const { status, currentStep, progress, message, processingOptions } = useAppStore()
  const { start, cancel, isStarting } = useProcessing()

  const isStepByStepMode = processingOptions.mode === 'step-by-step'
  const tabs = [
    { id: 'source', label: 'Nguồn Video', icon: '🎬' },
    { id: 'adjust', label: 'Điều Chỉnh', icon: '⚙️' },
    { id: 'dub', label: 'Lồng Tiếng', icon: '🎤' },
    { id: 'log', label: 'Nhật Ký', icon: '📋' },
  ]

  const isProcessing = status === 'running' || status === 'queued'

  return (
    <div className="min-h-screen bg-apple-gray text-apple-ink font-sf-text">
      {/* Header */}
      <header className="bg-white border-b border-apple-border-soft px-8 py-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h1 className="text-promo font-sf-display text-apple-ink leading-tight">
                Dubbing Extractor v3
              </h1>
              <p className="text-control text-apple-gray-secondary">
                Web-based video processing with real-time updates
              </p>
            </div>

            <div className="flex items-center gap-6">
              {/* Connection status */}
              <div className="flex items-center gap-2 px-3 py-2 bg-apple-gray rounded-apple-pill">
                <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-control text-apple-gray-secondary font-medium">
                  {connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>

              {/* Action buttons */}
              {isStepByStepMode ? (
                <div className="px-4 py-2 bg-blue-50 border border-blue-300 rounded-apple-md">
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

          {/* Progress bar */}
          {isProcessing && (
            <div className="mt-6">
              <ProgressBar
                progress={progress}
                step={currentStep}
                message={message}
              />
            </div>
          )}
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-apple-border-soft bg-white sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-8">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-4 font-semibold text-body transition-all border-b-2 -mb-px ${
                  activeTab === tab.id
                    ? 'border-apple-blue text-apple-blue'
                    : 'border-transparent text-apple-gray-secondary hover:text-apple-ink hover:border-apple-border-soft'
                }`}
              >
                <span className="mr-2 text-lg">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab content */}
      <main className="py-8 px-8">
        <div className="max-w-7xl mx-auto">
          {/* Step-by-step panel (shown when mode is step-by-step) */}
          {isStepByStepMode && (
            <div className="mb-8">
              <StepByStepPanel />
            </div>
          )}

          {activeTab === 'source' && <SourceTab />}
          {activeTab === 'adjust' && <AdjustTab />}
          {activeTab === 'dub' && <DubTab />}
          {activeTab === 'log' && <LogTab />}

          
          {/* Output panel - shows when completed */}
          <OutputPanel />
        </div>
      </main>

      {/* Status bar */}
      <StatusBar />
    </div>
  )
}

export default App
