import useAppStore from '../store/appStore'

const StatusBar = () => {
  const { status, taskId, outputs } = useAppStore()

  const statusColors = {
    idle: 'text-apple-gray-secondary',
    queued: 'text-yellow-500',
    running: 'text-apple-blue',
    completed: 'text-green-600',
    failed: 'text-red-500',
  }

  const statusLabels = {
    idle: 'Sẵn sàng',
    queued: 'Đang chờ',
    running: 'Đang xử lý',
    completed: 'Hoàn thành',
    failed: 'Lỗi',
  }

  return (
    <footer className="status-footer fixed bottom-0 left-0 right-0 px-6 py-3">
      <div className="flex flex-col gap-2 text-sm md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-control text-apple-gray-secondary">Trạng thái:</span>
          <span className={`text-control font-semibold ${statusColors[status]}`}>
            {statusLabels[status]}
          </span>

          {taskId && (
            <span className="text-control text-apple-gray-secondary">
              Task ID: <span className="font-mono text-apple-ink">{taskId.slice(0, 8)}</span>
            </span>
          )}
        </div>

        {status === 'completed' && outputs && (
          <div className="text-control text-apple-gray-secondary">
            Outputs sẵn sàng trong panel kết quả.
          </div>
        )}
      </div>
    </footer>
  )
}

export default StatusBar
