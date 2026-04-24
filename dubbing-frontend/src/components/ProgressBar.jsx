import { getProgressSnapshot, getStepLabel, TOTAL_PROCESSING_STEPS } from '../utils/processingStatus'

const ProgressBar = ({ status, progress, step, message }) => {
  const { safeStep, safeProgress, safeMessage } = getProgressSnapshot(status, step, progress, message)
  const stepShare = TOTAL_PROCESSING_STEPS > 0 ? ((safeStep - 1) / TOTAL_PROCESSING_STEPS) * 100 : 0
  const effectiveProgress = Math.max(stepShare, safeProgress)

  return (
    <div className="surface-subtle rounded-apple-xl border border-apple-border-soft px-5 py-4 space-y-3">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-control font-medium text-apple-gray-secondary">
            Bước {safeStep}/{TOTAL_PROCESSING_STEPS}
          </p>
          <p className="text-body-emphasis text-apple-ink truncate">
            {getStepLabel(safeStep)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-micro text-apple-gray-secondary">Tiến độ</p>
          <p className="text-body-emphasis text-apple-blue">
            {safeProgress.toFixed(1)}%
          </p>
        </div>
      </div>

      <div className="relative h-3 rounded-apple-pill overflow-hidden progress-track">
        <div
          className="absolute inset-y-0 left-0 progress-fill transition-all duration-500 ease-out"
          style={{ width: `${effectiveProgress}%` }}
        />
        {(status === 'running' || status === 'queued') && (
          <div
            className="absolute inset-y-0 progress-runner"
            style={{ left: `max(calc(${effectiveProgress}% - 56px), 0px)` }}
          />
        )}
      </div>

      <div className="grid grid-cols-7 gap-2">
        {Array.from({ length: TOTAL_PROCESSING_STEPS }, (_, index) => {
          const stepNumber = index + 1
          const isActive = stepNumber === safeStep
          const isDone = stepNumber < safeStep || (safeProgress >= 100 && stepNumber === safeStep)

          return (
            <div
              key={stepNumber}
              className={`h-1.5 rounded-apple-pill transition-all ${
                isDone
                  ? 'bg-apple-blue'
                  : isActive
                  ? 'bg-blue-300'
                  : 'bg-apple-border-soft'
              }`}
            />
          )
        })}
      </div>

      {safeMessage && (
        <p className="text-control text-apple-gray-secondary">
          {safeMessage}
        </p>
      )}

      {status === 'queued' && (
        <p className="text-micro text-apple-gray-secondary">
          Tác vụ đã được tạo. Thanh tiến trình sẽ chạy ngay khi backend bắt đầu từng bước.
        </p>
      )}
    </div>
  )
}

export default ProgressBar
