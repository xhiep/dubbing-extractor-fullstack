import { getProgressSnapshot, getStepLabel, TOTAL_PROCESSING_STEPS } from '../utils/processingStatus'

const ProgressBar = ({ status, progress, step, message }) => {
  const { safeStep, safeProgress, safeMessage } = getProgressSnapshot(status, step, progress, message)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-dark-400">
          Buoc {safeStep}/{TOTAL_PROCESSING_STEPS}: {getStepLabel(safeStep)}
        </span>
        <span className="text-primary-400 font-medium">
          {safeProgress.toFixed(1)}%
        </span>
      </div>

      <div className="relative h-2 bg-dark-700 rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary-600 to-primary-400 transition-all duration-300 ease-out"
          style={{ width: `${safeProgress}%` }}
        />
      </div>

      {safeMessage && (
        <p className="text-sm text-dark-300">
          {safeMessage}
        </p>
      )}
    </div>
  )
}

export default ProgressBar
