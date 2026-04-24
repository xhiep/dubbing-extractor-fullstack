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

function App() {
  const [activeTab, setActiveTab] = useState('source')
  const { connected } = useWebSocket()
  const { status, currentStep, progress, message } = useAppStore()
  const { start, cancel, isStarting } = useProcessing()

  const tabs = [
    { id: 'source', label: 'Nguồn Video', icon: '🎬' },
    { id: 'adjust', label: 'Điều Chỉnh', icon: '⚙️' },
    { id: 'dub', label: 'Lồng Tiếng', icon: '🎤' },
    { id: 'log', label: 'Nhật Ký', icon: '📋' },
  ]

  const isProcessing = status === 'running' || status === 'queued'

  return (
    <div className="min-h-screen bg-dark-900 text-white">
      {/* Header */}
      <header className="bg-dark-800 border-b border-dark-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-primary-400">
              Dubbing Extractor v3
            </h1>
            <p className="text-sm text-dark-400 mt-1">
              Web-based video processing with real-time updates
            </p>
          </div>

          <div className="flex items-center gap-4">
            {/* Connection status */}
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm text-dark-400">
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>

            {/* Action buttons */}
            {isProcessing ? (
              <button
                onClick={() => cancel()}
                className="btn bg-red-600 hover:bg-red-700"
              >
                Hủy Xử Lý
              </button>
            ) : (
              <button
                onClick={() => start()}
                disabled={isStarting}
                className="btn btn-primary"
              >
                {isStarting ? 'Đang Khởi Động...' : 'Bắt Đầu Xử Lý'}
              </button>
            )}
          </div>
        </div>

        {/* Progress bar */}
        {isProcessing && (
          <div className="mt-4">
            <ProgressBar
              progress={progress}
              step={currentStep}
              message={message}
            />
          </div>
        )}
      </header>

      {/* Tabs */}
      <div className="border-b border-dark-700">
        <div className="flex px-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 font-medium transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-400'
                  : 'border-transparent text-dark-400 hover:text-white'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <main className="p-6">
        <div className="max-w-7xl mx-auto">
          {activeTab === 'source' && <SourceTab />}
          {activeTab === 'adjust' && <AdjustTab />}
          {activeTab === 'dub' && <DubTab />}
          {activeTab === 'log' && <LogTab />}
        </div>
      </main>

      {/* Status bar */}
      <StatusBar />
    </div>
  )
}

export default App
