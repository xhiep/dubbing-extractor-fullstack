import useAppStore from '../store/appStore'

const StatusBar = () => {
  const { status, taskId, outputs } = useAppStore()

  const statusColors = {
    idle: 'text-dark-400',
    queued: 'text-yellow-400',
    running: 'text-blue-400',
    completed: 'text-green-400',
    failed: 'text-red-400',
  }

  const statusLabels = {
    idle: 'Sẵn sàng',
    queued: 'Đang chờ',
    running: 'Đang xử lý',
    completed: 'Hoàn thành',
    failed: 'Lỗi',
  }

  return (
    <footer className="fixed bottom-0 left-0 right-0 bg-dark-800 border-t border-dark-700 px-6 py-3">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-4">
          <span className="text-dark-400">Trạng thái:</span>
          <span className={`font-medium ${statusColors[status]}`}>
            {statusLabels[status]}
          </span>

          {taskId && (
            <>
              <span className="text-dark-600">|</span>
              <span className="text-dark-400">
                Task ID: <span className="text-dark-300 font-mono">{taskId.slice(0, 8)}</span>
              </span>
            </>
          )}
        </div>

        {status === 'completed' && outputs && (
          <div className="flex items-center gap-2">
            <span className="text-dark-400">Outputs:</span>
            {outputs.video_clean && (
              <a
                href={outputs.video_clean}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-400 hover:text-primary-300 underline"
              >
                Video Clean
              </a>
            )}
            {outputs.video_dubbed && (
              <a
                href={outputs.video_dubbed}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-400 hover:text-primary-300 underline"
              >
                Video Dubbed
              </a>
            )}
          </div>
        )}
      </div>
    </footer>
  )
}

export default StatusBar
