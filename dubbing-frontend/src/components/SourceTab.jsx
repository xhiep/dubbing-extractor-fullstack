import { useEffect, useState } from 'react'
import { FileVideo, Link as LinkIcon, Loader2 } from 'lucide-react'
import useAppStore from '../store/appStore'
import { usePreview } from '../hooks/useProcessing'
import { apiClient } from '../api/client'
import PreviewCanvas from './PreviewCanvas'

const SOURCE_PREVIEW_START = 1
const SOURCE_PREVIEW_DURATION = 3

const SourceTab = () => {
  const { processingOptions, updateProcessingOptions, setPreview } = useAppStore()
  const [sourceInput, setSourceInput] = useState(processingOptions.source)
  const [showPreview, setShowPreview] = useState(false)
  const [backendPreview, setBackendPreview] = useState(null)
  const [backendPreviewLoading, setBackendPreviewLoading] = useState(false)
  const [backendPreviewError, setBackendPreviewError] = useState('')

  const { data: preview, isLoading, error } = usePreview(showPreview ? sourceInput : null)

  useEffect(() => {
    if (preview) {
      setPreview(preview)
    }
  }, [preview, setPreview])

  useEffect(() => {
    if (!showPreview || !sourceInput.trim()) {
      setBackendPreview(null)
      setBackendPreviewError('')
      return
    }

    let cancelled = false

    const fetchBackendPreview = async () => {
      setBackendPreviewLoading(true)
      setBackendPreviewError('')

      try {
        const response = await apiClient.post('/preview-render/layout', {
          source: sourceInput.trim(),
          start_time: SOURCE_PREVIEW_START,
          duration: SOURCE_PREVIEW_DURATION,
          preview_text: '',
          burn_subtitle: false,
          srt_max_chars_per_line: processingOptions.srt_max_chars_per_line,
          cover_mode: 'none',
          cover_strength: processingOptions.cover_strength,
          subtitle_font_scale: processingOptions.subtitle_font_scale,
          subtitle_font_size: processingOptions.subtitle_font_size,
          subtitle_margin_px: processingOptions.subtitle_margin_px,
          blur_padding_px: processingOptions.blur_padding_px,
          cover_offset_px: processingOptions.cover_offset_px,
          render_video_speed: 1.0,
          video_speed: 1.0,
        })

        if (!cancelled) {
          setBackendPreview(response.data)
        }
      } catch (layoutError) {
        if (!cancelled) {
          console.error('Source backend preview failed:', layoutError)
          setBackendPreview(null)
          setBackendPreviewError(layoutError.response?.data?.detail || layoutError.message)
        }
      } finally {
        if (!cancelled) {
          setBackendPreviewLoading(false)
        }
      }
    }

    fetchBackendPreview()

    return () => {
      cancelled = true
    }
  }, [
    showPreview,
    sourceInput,
    processingOptions.srt_max_chars_per_line,
    processingOptions.cover_strength,
    processingOptions.subtitle_font_scale,
    processingOptions.subtitle_font_size,
    processingOptions.subtitle_margin_px,
    processingOptions.blur_padding_px,
    processingOptions.cover_offset_px,
  ])

  const handleSourceChange = (e) => {
    const value = e.target.value
    setSourceInput(value)
    updateProcessingOptions({ source: value })
    setShowPreview(false)
    setBackendPreview(null)
    setBackendPreviewError('')
  }

  const handlePreview = () => {
    if (sourceInput.trim()) {
      setShowPreview(true)
      setBackendPreview(null)
      setBackendPreviewError('')
    }
  }

  const isUrl = sourceInput.startsWith('http://') || sourceInput.startsWith('https://')

  return (
    <div className="space-y-8">
      <div className="card">
        <h2 className="text-utility font-sf-display text-apple-ink mb-6">Nguon Video</h2>

        <div className="space-y-5">
          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              URL hoac duong dan file local
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
                  placeholder="https://youtube.com/watch?v=... hoac C:\\path\\to\\video.mp4"
                  className="input pl-12 py-3"
                />
              </div>
              <button
                onClick={handlePreview}
                disabled={!sourceInput.trim() || isLoading || backendPreviewLoading}
                className="btn btn-secondary px-8 py-3 rounded-apple-md"
              >
                {isLoading || backendPreviewLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  'Preview'
                )}
              </button>
            </div>
          </div>

          {showPreview && (isLoading || backendPreviewLoading) && (
            <div className="notice-info rounded-apple-xl p-5">
              <p className="text-blue-600 text-control font-medium">
                Dang tai metadata va frame backend 1-3s dau...
              </p>
            </div>
          )}

          {showPreview && preview && (
            <div className="surface-subtle rounded-apple-xl p-5 space-y-3">
              <div className="grid gap-5 lg:grid-cols-[minmax(320px,1.1fr)_minmax(0,0.9fr)] items-start">
                <div className="bg-apple-black rounded-apple-lg overflow-hidden aspect-video flex items-center justify-center">
                  {backendPreview?.image_url ? (
                    <PreviewCanvas
                      imageUrl={backendPreview.image_url}
                      renderedPreview
                      previewText=""
                      coverMode="none"
                      coverStrength={0}
                      subtitleFontScale={processingOptions.subtitle_font_scale}
                      subtitleFontSize={processingOptions.subtitle_font_size}
                      subtitleMargin={processingOptions.subtitle_margin_px}
                      blurPadding={processingOptions.blur_padding_px}
                      coverOffset={processingOptions.cover_offset_px}
                      maxCharsPerLine={processingOptions.srt_max_chars_per_line}
                      previewWidth={backendPreview.width}
                      previewHeight={backendPreview.height}
                    />
                  ) : (
                    <div className="text-center px-6 text-apple-gray-secondary">
                      <Loader2 className="h-8 w-8 mx-auto mb-3 animate-spin opacity-70" />
                      <p className="text-control">Dang lay frame preview tu backend...</p>
                    </div>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-apple-ink mb-2 text-body-emphasis">
                    {preview.title}
                  </h3>
                  <div className="text-control text-apple-gray-secondary space-y-1.5">
                    <p>Platform: {preview.platform}</p>
                    <p>Duration: {Math.floor(preview.duration / 60)}:{String(Math.floor(preview.duration % 60)).padStart(2, '0')}</p>
                    <p>Resolution: {preview.width}x{preview.height}</p>
                    <p>Backend preview: clip {SOURCE_PREVIEW_START}-{SOURCE_PREVIEW_START + SOURCE_PREVIEW_DURATION}s, khong lay overlay tu tab khac.</p>
                    {backendPreviewError && <p className="text-red-600">{backendPreviewError}</p>}
                  </div>
                </div>
              </div>
            </div>
          )}

          {showPreview && error && (
            <div className="notice-error rounded-apple-xl p-5">
              <p className="text-red-600 text-control font-medium">
                {error.message}
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="text-utility font-sf-display text-apple-ink mb-6">Che Do Xu Ly</h2>

        <div className="space-y-4">
          <label className="option-card flex items-start gap-4 p-5 rounded-apple-xl cursor-pointer transition-all">
            <input
              type="radio"
              name="mode"
              value="monolithic"
              checked={processingOptions.mode === 'monolithic'}
              onChange={(e) => updateProcessingOptions({ mode: e.target.value })}
              className="mt-1 w-4 h-4 accent-apple-blue"
            />
            <div className="flex-1">
              <div className="font-semibold text-body-emphasis text-apple-ink mb-1">Monolithic (tu dong)</div>
              <div className="text-control text-apple-gray-secondary leading-relaxed">
                Chay toan bo pipeline mot lan, khong can can thiep.
              </div>
            </div>
          </label>

          <label className="option-card flex items-start gap-4 p-5 rounded-apple-xl cursor-pointer transition-all">
            <input
              type="radio"
              name="mode"
              value="step-by-step"
              checked={processingOptions.mode === 'step-by-step'}
              onChange={(e) => updateProcessingOptions({ mode: e.target.value })}
              className="mt-1 w-4 h-4 accent-apple-blue"
            />
            <div className="flex-1">
              <div className="font-semibold text-body-emphasis text-apple-ink mb-1">Step-by-Step (thu cong)</div>
              <div className="text-control text-apple-gray-secondary leading-relaxed">
                Chay tung buoc rieng, co the chinh SRT va tham so giua chung.
              </div>
            </div>
          </label>
        </div>
      </div>
    </div>
  )
}

export default SourceTab
