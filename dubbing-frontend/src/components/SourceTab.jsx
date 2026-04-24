import { useState, useEffect } from 'react'
import useAppStore from '../store/appStore'
import { usePreview } from '../hooks/useProcessing'
import { FileVideo, Link as LinkIcon, Loader2 } from 'lucide-react'

const SourceTab = () => {
  const { processingOptions, updateProcessingOptions, setPreview } = useAppStore()
  const [sourceInput, setSourceInput] = useState(processingOptions.source)
  const [showPreview, setShowPreview] = useState(false)
  const [thumbnailError, setThumbnailError] = useState(false)
  const [thumbnailLoading, setThumbnailLoading] = useState(false)

  const { data: preview, isLoading, error } = usePreview(
    showPreview ? sourceInput : null
  )

  // Save preview to store when it loads
  useEffect(() => {
    if (preview) {
      setPreview(preview)
    }
  }, [preview, setPreview])

  // Debug logging
  console.log('Preview state:', { showPreview, preview, isLoading, error, thumbnailError })

  const handleSourceChange = (e) => {
    const value = e.target.value
    setSourceInput(value)
    updateProcessingOptions({ source: value })
    setShowPreview(false)
    setThumbnailError(false)
    setThumbnailLoading(false)
  }

  const handlePreview = () => {
    if (sourceInput.trim()) {
      setShowPreview(true)
      setThumbnailError(false)
      setThumbnailLoading(true)
    }
  }

  const isUrl = sourceInput.startsWith('http://') || sourceInput.startsWith('https://')

  return (
    <div className="space-y-8">
      {/* Source input */}
      <div className="card">
        <h2 className="text-utility font-sf-display text-apple-ink mb-6">Nguồn Video</h2>

        <div className="space-y-5">
          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              URL hoặc đường dẫn file local
            </label>
            <div className="flex gap-3">
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  {isUrl ? (
                    <LinkIcon className="h-5 w-5 text-apple-gray-secondary" />
                  ) : (
                    <FileVideo className="h-5 w-5 text-apple-gray-secondary" />
                  )}
                </div>
                <input
                  type="text"
                  value={sourceInput}
                  onChange={handleSourceChange}
                  placeholder="https://youtube.com/watch?v=... hoặc C:\path\to\video.mp4"
                  className="input pl-12 py-3"
                />
              </div>
              <button
                onClick={handlePreview}
                disabled={!sourceInput.trim() || isLoading}
                className="btn btn-secondary px-8 py-3 rounded-apple-md"
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  'Preview'
                )}
              </button>
            </div>
          </div>

          {/* Debug: Show loading/error state */}
          {showPreview && isLoading && (
            <div className="bg-blue-50 border border-blue-300 rounded-apple-xl p-5">
              <p className="text-blue-600 text-control font-medium">
                🔄 Đang tải preview...
              </p>
            </div>
          )}

          {/* Preview info */}
          {showPreview && preview && (
            <div className="bg-apple-gray rounded-apple-xl p-5 space-y-3 border border-apple-border-soft">
              <div className="flex items-start gap-5">
                {preview.thumbnail && !thumbnailError ? (
                  <div className="relative w-40 h-24 rounded-apple-lg flex-shrink-0 bg-apple-black">
                    {thumbnailLoading && (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <Loader2 className="h-6 w-6 text-apple-blue animate-spin" />
                      </div>
                    )}
                    <img
                      src={`/api/preview/thumbnail?url=${encodeURIComponent(preview.thumbnail)}`}
                      alt={preview.title}
                      className={`w-full h-full object-cover rounded-apple-lg ${thumbnailLoading ? 'opacity-0' : 'opacity-100'} transition-opacity duration-300`}
                      onError={() => {
                        console.error('Thumbnail failed to load:', preview.thumbnail)
                        setThumbnailError(true)
                        setThumbnailLoading(false)
                      }}
                      onLoad={() => {
                        console.log('Thumbnail loaded successfully')
                        setThumbnailLoading(false)
                      }}
                    />
                  </div>
                ) : (
                  <div className="w-40 h-24 rounded-apple-lg flex-shrink-0 bg-apple-black flex items-center justify-center">
                    <FileVideo className="h-8 w-8 text-apple-gray-secondary opacity-50" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-apple-ink mb-2 text-body-emphasis">
                    {preview.title}
                  </h3>
                  <div className="text-control text-apple-gray-secondary space-y-1.5">
                    <p>Platform: {preview.platform}</p>
                    <p>Duration: {Math.floor(preview.duration / 60)}:{String(Math.floor(preview.duration % 60)).padStart(2, '0')}</p>
                    <p>Resolution: {preview.width}x{preview.height}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {showPreview && error && (
            <div className="bg-red-50 border border-red-300 rounded-apple-xl p-5">
              <p className="text-red-600 text-control font-medium">
                ⚠️ {error.message}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Processing mode */}
      <div className="card">
        <h2 className="text-utility font-sf-display text-apple-ink mb-6">Chế Độ Xử Lý</h2>

        <div className="space-y-4">
          <label className="flex items-start gap-4 p-5 bg-apple-gray rounded-apple-xl cursor-pointer hover:bg-apple-border-soft transition-all border border-apple-border-soft hover:border-apple-border-mid">
            <input
              type="radio"
              name="mode"
              value="monolithic"
              checked={processingOptions.mode === 'monolithic'}
              onChange={(e) => updateProcessingOptions({ mode: e.target.value })}
              className="mt-1 w-4 h-4 accent-apple-blue"
            />
            <div className="flex-1">
              <div className="font-semibold text-body-emphasis text-apple-ink mb-1">Monolithic (Tự động)</div>
              <div className="text-control text-apple-gray-secondary leading-relaxed">
                Chạy toàn bộ pipeline một lần, không cần can thiệp
              </div>
            </div>
          </label>

          <label className="flex items-start gap-4 p-5 bg-apple-gray rounded-apple-xl cursor-pointer hover:bg-apple-border-soft transition-all border border-apple-border-soft hover:border-apple-border-mid">
            <input
              type="radio"
              name="mode"
              value="step-by-step"
              checked={processingOptions.mode === 'step-by-step'}
              onChange={(e) => updateProcessingOptions({ mode: e.target.value })}
              className="mt-1 w-4 h-4 accent-apple-blue"
            />
            <div className="flex-1">
              <div className="font-semibold text-body-emphasis text-apple-ink mb-1">Step-by-Step (Thủ công)</div>
              <div className="text-control text-apple-gray-secondary leading-relaxed">
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
