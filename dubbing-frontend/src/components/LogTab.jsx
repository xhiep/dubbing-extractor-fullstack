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
    debug: 'text-dark-400',
    info: 'text-blue-400',
    warning: 'text-yellow-400',
    error: 'text-red-400',
  }

  const levelIcons = {
    debug: '🔍',
    info: 'ℹ️',
    warning: '⚠️',
    error: '❌',
  }

  return (
    <div className="space-y-4">
      {/* Log controls */}
      <div className="card flex items-center justify-between">
        <div className="text-sm text-dark-400">
          {logs.length} log entries
        </div>
        <button
          onClick={() => useAppStore.getState().clearLogs()}
          className="btn btn-secondary text-sm"
        >
          Clear Logs
        </button>
      </div>

      {/* Log viewer */}
      <div className="card">
        <div className="bg-dark-900 rounded-lg p-4 h-[600px] overflow-y-auto font-mono text-sm">
          {logs.length === 0 ? (
            <div className="text-center text-dark-400 py-8">
              No logs yet. Start processing to see logs here.
            </div>
          ) : (
            <div className="space-y-1">
              {logs.map((log, index) => (
                <div
                  key={index}
                  className={`flex items-start gap-2 ${levelColors[log.level]}`}
                >
                  <span className="flex-shrink-0">
                    {levelIcons[log.level]}
                  </span>
                  <span className="text-dark-500 flex-shrink-0">
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
        <h3 className="text-sm font-medium text-dark-400 mb-2">Log Levels:</h3>
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-1">
            <span>🔍</span>
            <span className="text-dark-400">Debug</span>
          </div>
          <div className="flex items-center gap-1">
            <span>ℹ️</span>
            <span className="text-blue-400">Info</span>
          </div>
          <div className="flex items-center gap-1">
            <span>⚠️</span>
            <span className="text-yellow-400">Warning</span>
          </div>
          <div className="flex items-center gap-1">
            <span>❌</span>
            <span className="text-red-400">Error</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LogTab
