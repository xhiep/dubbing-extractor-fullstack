import useAppStore from '../store/appStore'

const ProgressBar = ({ progress, step, message }) => {
  const steps = [
    'Chuẩn bị',
    'Transcribe',
    'Dịch',
    'Che phụ đề',
    'Xuất file',
    'Burn subtitle',
    'Lồng tiếng',
  ]

  return (
    <div className="space-y-2">
      {/* Step indicator */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-dark-400">
          Bước {step}/7: {steps[step - 1] || 'Đang xử lý...'}
        </span>
        <span className="text-primary-400 font-medium">
          {progress.toFixed(1)}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="relative h-2 bg-dark-700 rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary-600 to-primary-400 transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Message */}
      {message && (
        <p className="text-sm text-dark-300">
          {message}
        </p>
      )}
    </div>
  )
}

export default ProgressBar
