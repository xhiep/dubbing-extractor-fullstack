import { useEffect, useMemo, useState } from 'react'
import { useStepProcessing } from '../hooks/useProcessing'
import { processAPI } from '../api/client'
import useAppStore from '../store/appStore'
import { Play, Check, Clock, FilePenLine, RefreshCw, Save } from 'lucide-react'

const steps = [
  { num: 1, name: 'Prepare Source', description: 'Tải video hoặc dùng file local, sau đó chuẩn bị audio.' },
  { num: 2, name: 'Transcribe Audio', description: 'Nhận dạng giọng nói bằng Whisper.' },
  { num: 3, name: 'Translate Subtitle', description: 'Dịch sang tiếng Việt và tạo SRT để có thể sửa tay.' },
  { num: 4, name: 'Cover Original Subtitle', description: 'Che phụ đề gốc theo timing subtitle mới.' },
  { num: 5, name: 'Export Files', description: 'Xuất SRT, script, song ngữ và metadata render.' },
  { num: 6, name: 'Burn Subtitle', description: 'Gắn phụ đề Việt vào video.' },
  { num: 7, name: 'Generate Dub', description: 'Tạo audio/video lồng tiếng bằng VieNeu-TTS.' },
]

const StepByStepPanel = () => {
  const {
    taskId,
    status,
    outputs,
    currentStep,
    processingOptions,
  } = useAppStore()
  const { runStep, isRunning } = useStepProcessing()

  const [currentRunningTarget, setCurrentRunningTarget] = useState(null)
  const [srtContent, setSrtContent] = useState('')
  const [savingSrt, setSavingSrt] = useState(false)
  const [reloadingSrt, setReloadingSrt] = useState(false)

  const completedSteps = useMemo(
    () => new Set(outputs?.completed_steps || []),
    [outputs]
  )

  useEffect(() => {
    if (typeof outputs?.srt_content === 'string') {
      setSrtContent(outputs.srt_content)
    }
  }, [outputs?.srt_content])

  const canRunSteps = Boolean(processingOptions.source?.trim() || taskId)
  const showSrtEditor = Boolean(taskId && (outputs?.srt_path || completedSteps.has(3)))

  const handleRunStep = (stepNum) => {
    if (!canRunSteps) return

    setCurrentRunningTarget(stepNum)
    runStep(
      {
        stepNum,
        taskId: taskId || 'new',
        stepData: {
          source: processingOptions.source,
          options: processingOptions,
          srt_content: srtContent,
        },
      },
      {
        onError: () => {
          setCurrentRunningTarget(null)
        },
      }
    )
  }

  useEffect(() => {
    if (!isRunning) {
      setCurrentRunningTarget(null)
    }
  }, [isRunning])

  const handleSaveSrt = async () => {
    if (!taskId || !showSrtEditor) return
    setSavingSrt(true)
    try {
      await processAPI.saveStepSrt(taskId, srtContent)
    } finally {
      setSavingSrt(false)
    }
  }

  const handleReloadSrt = async () => {
    if (!taskId || !showSrtEditor) return
    setReloadingSrt(true)
    try {
      const result = await processAPI.getStepSrt(taskId)
      setSrtContent(result.content || '')
    } finally {
      setReloadingSrt(false)
    }
  }

  const getStepStatus = (stepNum) => {
    if (status === 'running' && currentStep === stepNum) return 'running'
    if (completedSteps.has(stepNum)) return 'completed'
    return 'ready'
  }

  const getStepIcon = (stepNum) => {
    const stepStatus = getStepStatus(stepNum)
    switch (stepStatus) {
      case 'completed':
        return <Check className="h-5 w-5 text-green-600" />
      case 'running':
        return <Clock className="h-5 w-5 text-blue-600 animate-spin" />
      default:
        return <Play className="h-5 w-5 text-apple-blue" />
    }
  }

  return (
    <div className="card">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-utility font-sf-display text-apple-ink">
            Step-by-Step Processing
          </h2>
          <p className="mt-2 text-control text-apple-gray-secondary">
            Có thể bấm trực tiếp bước bất kỳ. Backend sẽ tự chạy bù các bước còn thiếu trước bước bạn chọn.
          </p>
        </div>
        {taskId && (
          <div className="surface-subtle rounded-apple-lg px-4 py-3 text-right">
            <div className="text-micro text-apple-gray-secondary">Task ID</div>
            <div className="text-control font-mono text-apple-ink">{taskId.slice(0, 8)}</div>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {steps.map((step) => {
          const stepStatus = getStepStatus(step.num)
          const isDisabled = isRunning || !canRunSteps
          const isTarget = currentRunningTarget === step.num

          return (
            <div
              key={step.num}
              className={`flex items-center gap-4 p-4 rounded-apple-xl border transition-all ${
                stepStatus === 'completed'
                  ? 'bg-green-50 border-green-300'
                  : stepStatus === 'running' || isTarget
                  ? 'bg-blue-50 border-blue-300'
                  : 'surface-subtle'
              }`}
            >
              <div className="flex-shrink-0">
                {getStepIcon(step.num)}
              </div>

              <div className="flex-1 min-w-0">
                <div className="font-semibold text-body text-apple-ink">
                  {step.num}. {step.name}
                </div>
                <div className="text-control text-apple-gray-secondary">
                  {step.description}
                </div>
              </div>

              <button
                onClick={() => handleRunStep(step.num)}
                disabled={isDisabled}
                className={`btn px-6 py-2 rounded-apple-md ${isDisabled ? 'btn-secondary opacity-50 cursor-not-allowed' : 'btn-primary'}`}
              >
                {stepStatus === 'running' || isTarget ? 'Đang chạy...' : `Chạy bước ${step.num}`}
              </button>
            </div>
          )
        })}
      </div>

      {showSrtEditor && (
        <div className="mt-6 rounded-apple-xl border border-apple-border-soft p-5 surface-subtle">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <FilePenLine className="mt-0.5 h-5 w-5 text-apple-blue" />
              <div>
                <h3 className="font-semibold text-body text-apple-ink">SRT Editor</h3>
                <p className="text-control text-apple-gray-secondary">
                  Sau bước 3 có thể sửa trực tiếp text sub trước khi chạy bước 4-7.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleReloadSrt}
                disabled={reloadingSrt}
                className="btn btn-tertiary"
              >
                <RefreshCw className={`h-4 w-4 ${reloadingSrt ? 'animate-spin' : ''}`} />
                Reload
              </button>
              <button
                type="button"
                onClick={handleSaveSrt}
                disabled={savingSrt}
                className="btn btn-primary"
              >
                <Save className="h-4 w-4" />
                {savingSrt ? 'Đang lưu...' : 'Lưu SRT'}
              </button>
            </div>
          </div>

          <textarea
            value={srtContent}
            onChange={(e) => setSrtContent(e.target.value)}
            rows={14}
            className="input w-full resize-y font-mono text-sm"
            placeholder="SRT sẽ xuất hiện ở đây sau khi chạy bước 3."
          />
        </div>
      )}

      {Object.keys(outputs || {}).length > 0 && (
        <div className="mt-6 p-4 surface-subtle rounded-apple-xl">
          <h3 className="font-semibold text-body text-apple-ink mb-3">Step Outputs</h3>
          <div className="space-y-2 text-control text-apple-gray-secondary">
            {Object.entries(outputs)
              .filter(([key]) => !['srt_content', 'cover_meta', 'completed_steps'].includes(key))
              .map(([key, value]) => (
                <div key={key} className="flex justify-between gap-4">
                  <span>{key}:</span>
                  <span className="font-mono text-apple-ink break-all text-right">
                    {typeof value === 'string' ? value : JSON.stringify(value)}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default StepByStepPanel
