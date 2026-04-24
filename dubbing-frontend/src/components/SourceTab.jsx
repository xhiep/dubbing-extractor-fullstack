import { useState } from 'react'
import useAppStore from '../store/appStore'
import { usePreview } from '../hooks/useProcessing'
import { FileVideo, Link as LinkIcon, Loader2 } from 'lucide-react'

const SourceTab = () => {
  const { processingOptions, updateProcessingOptions } = useAppStore()
  const [sourceInput, setSourceInput] = useState(processingOptions.source)
  const [showPreview, setShowPreview] = useState(false)

  const { data: preview, isLoading, error } = usePreview(
    showPreview ? sourceInput : null
  )

  const handleSourceChange = (e) => {
    const value = e.target.value
    setSourceInput(value)
    updateProcessingOptions({ source: value })
    setShowPreview(false)
  }

  const handlePreview = () => {
    if (sourceInput.trim()) {
      setShowPreview(true)
    }
  }

  const isUrl = sourceInput.startsWith('http://') || sourceInput.startsWith('https://')

  return (
    <div className="space-y-6">
      {/* Source input */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Nguồn Video</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-2">
              URL hoặc đường dẫn file local
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  {isUrl ? (
                    <LinkIcon className="h-5 w-5 text-dark-400" />
                  ) : (
                    <FileVideo className="h-5 w-5 text-dark-400" />
                  )}
                </div>
                <input
                  type="text"
                  value={sourceInput}
                  onChange={handleSourceChange}
                  placeholder="https://youtube.com/watch?v=... hoặc C:\path\to\video.mp4"
                  className="input pl-10"
                />
              </div>
              <button
                onClick={handlePreview}
                disabled={!sourceInput.trim() || isLoading}
                className="btn btn-secondary px-6"
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  'Preview'
                )}
              </button>
            </div>
          </div>

          {/* Preview info */}
          {showPreview && preview && (
            <div className="bg-dark-700 rounded-lg p-4 space-y-3">
              <div className="flex items-start gap-4">
                {preview.thumbnail && (
                  <img
                    src={preview.thumbnail}
                    alt={preview.title}
                    className="w-32 h-20 object-cover rounded"
                  />
                )}
                <div className="flex-1">
                  <h3 className="font-medium text-white mb-1">
                    {preview.title}
                  </h3>
                  <div className="text-sm text-dark-300 space-y-1">
                    <p>Platform: {preview.platform}</p>
                    <p>Duration: {Math.floor(preview.duration / 60)}:{String(Math.floor(preview.duration % 60)).padStart(2, '0')}</p>
                    <p>Resolution: {preview.width}x{preview.height}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {showPreview && error && (
            <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
              <p className="text-red-400 text-sm">
                ⚠️ {error.message}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Processing mode */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Chế Độ Xử Lý</h2>

        <div className="space-y-3">
          <label className="flex items-start gap-3 p-4 bg-dark-700 rounded-lg cursor-pointer hover:bg-dark-600 transition-colors">
            <input
              type="radio"
              name="mode"
              value="monolithic"
              checked={processingOptions.mode === 'monolithic'}
              onChange={(e) => updateProcessingOptions({ mode: e.target.value })}
              className="mt-1"
            />
            <div>
              <div className="font-medium">Monolithic (Tự động)</div>
              <div className="text-sm text-dark-300 mt-1">
                Chạy toàn bộ pipeline một lần, không cần can thiệp
              </div>
            </div>
          </label>

          <label className="flex items-start gap-3 p-4 bg-dark-700 rounded-lg cursor-pointer hover:bg-dark-600 transition-colors">
            <input
              type="radio"
              name="mode"
              value="step-by-step"
              checked={processingOptions.mode === 'step-by-step'}
              onChange={(e) => updateProcessingOptions({ mode: e.target.value })}
              className="mt-1"
            />
            <div>
              <div className="font-medium">Step-by-Step (Thủ công)</div>
              <div className="text-sm text-dark-300 mt-1">
                Chạy từng bước riêng, có thể edit SRT giữa chừng
              </div>
            </div>
          </label>
        </div>
      </div>
    </div>
  )
}

export default SourceTab
