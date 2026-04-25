import { useEffect, useRef } from 'react'
import useAppStore from '../store/appStore'

const LogTab = () => {
  const { logs } = useAppStore()
  const logEndRef = useRef(null)

  useEffect(() => {
    // Auto-scroll to bottom when new logs arrive
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const levelColors = {
    debug: 'text-apple-gray-secondary',
    info: 'text-apple-blue',
    warning: 'text-yellow-600',
    error: 'text-red-600',
  }

  const levelIcons = {
    debug: '🔍',
    info: 'ℹ️',
    warning: '⚠️',
    error: '❌',
  }

  return (
    <div className="space-y-6">
      {/* Log controls */}
      <div className="card flex items-center justify-between">
        <div className="text-control text-apple-gray-secondary">
          {logs.length} log entries
        </div>
        <button
          onClick={() => useAppStore.getState().clearLogs()}
          className="btn btn-secondary rounded-apple-md px-6 py-2"
        >
          Clear Logs
        </button>
      </div>

      {/* Log viewer */}
      <div className="card">
        <div className="bg-apple-black rounded-apple-lg p-5 h-[600px] overflow-y-auto font-mono text-control">
          {logs.length === 0 ? (
            <div className="text-center text-apple-gray-secondary py-12">
              No logs yet. Start processing to see logs here.
            </div>
          ) : (
            <div className="space-y-2">
              {logs.map((log, index) => (
                <div
                  key={index}
                  className={`flex items-start gap-3 ${levelColors[log.level]}`}
                >
                  <span className="flex-shrink-0">
                    {levelIcons[log.level]}
                  </span>
                  <span className="text-apple-gray-secondary flex-shrink-0 min-w-[80px]">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span className="flex-1 break-words">
                    {log.message}
                  </span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Log legend */}
      <div className="card">
        <h3 className="text-body-emphasis text-apple-ink mb-4">Log Levels:</h3>
        <div className="flex flex-wrap gap-6 text-control">
          <div className="flex items-center gap-2">
            <span>🔍</span>
            <span className="text-apple-gray-secondary">Debug</span>
          </div>
          <div className="flex items-center gap-2">
            <span>ℹ️</span>
            <span className="text-apple-blue">Info</span>
          </div>
          <div className="flex items-center gap-2">
            <span>⚠️</span>
            <span className="text-yellow-600">Warning</span>
          </div>
          <div className="flex items-center gap-2">
            <span>❌</span>
            <span className="text-red-600">Error</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LogTab
