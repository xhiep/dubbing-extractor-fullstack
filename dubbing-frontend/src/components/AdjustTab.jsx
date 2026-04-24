import { useState, useEffect, useRef } from 'react'
import useAppStore from '../store/appStore'
import { FileVideo } from 'lucide-react'

const AdjustTab = () => {
  const { processingOptions, updateProcessingOptions, outputs, preview } = useAppStore()
  const [previewText, setPreviewText] = useState('Dòng phụ đề mẫu số 1\nDòng phụ đề mẫu số 2')
  const videoRef = useRef(null)
  const [thumbnailError, setThumbnailError] = useState(false)

  // Load video preview if available
  useEffect(() => {
    if (outputs.video_path && videoRef.current) {
      // Try to load the processed video from backend static files
      const filename = outputs.video_path.split('/').pop()
      videoRef.current.src = `/output/${filename}`
    }
  }, [outputs.video_path])

  return (
    <div className="space-y-8">
      {/* Video Preview Section */}
      <div className="card">
        <h2 className="text-utility font-sf-display text-apple-ink mb-6">Video Preview</h2>

        <div className="space-y-4">
          {/* Preview Canvas */}
          <div className="bg-apple-black rounded-apple-xl overflow-hidden aspect-video flex items-center justify-center relative">
            {outputs.video_path ? (
              <video
                ref={videoRef}
                controls
                className="w-full h-full object-contain"
                onError={(e) => {
                  console.error('Video load error:', e)
                }}
              >
                Video không được hỗ trợ
              </video>
            ) : preview && preview.thumbnail && !thumbnailError ? (
              <img
                src={`/api/preview/thumbnail?url=${encodeURIComponent(preview.thumbnail)}`}
                alt={preview.title || 'Video preview'}
                className="w-full h-full object-contain"
                onError={() => {
                  console.error('Thumbnail failed to load')
                  setThumbnailError(true)
                }}
              />
            ) : (
              <div className="text-apple-gray-secondary text-center">
                <FileVideo className="w-16 h-16 mx-auto mb-3 opacity-50" />
                <p className="text-control">Video preview sẽ hiển thị ở đây</p>
                <p className="text-micro mt-1">Nhập URL ở tab "Nguồn Video" và bấm "Preview"</p>
              </div>
            )}
          </div>

          {/* Preview Text Input */}
          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-2">
              Preview Text (để test subtitle)
            </label>
            <textarea
              value={previewText}
              onChange={(e) => setPreviewText(e.target.value)}
              placeholder="Nhập text để xem preview subtitle..."
              rows={3}
              className="input resize-none"
            />
          </div>
        </div>
      </div>

      {/* Whisper settings */}
      <div className="card">
        <h2 className="text-utility font-sf-display text-apple-ink mb-6">Whisper Transcription</h2>

        <div className="space-y-5">
          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Model Size
            </label>
            <select
              value={processingOptions.whisper_model}
              onChange={(e) => updateProcessingOptions({ whisper_model: e.target.value })}
              className="input"
            >
              <option value="tiny">Tiny (fastest, least accurate)</option>
              <option value="base">Base</option>
              <option value="small">Small</option>
              <option value="medium">Medium (recommended)</option>
              <option value="large">Large (slowest, most accurate)</option>
            </select>
          </div>

          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Language (auto-detect nếu để trống)
            </label>
            <input
              type="text"
              value={processingOptions.whisper_language || ''}
              onChange={(e) => updateProcessingOptions({ whisper_language: e.target.value || null })}
              placeholder="en, vi, ja, ko..."
              className="input"
            />
          </div>
        </div>
      </div>

      {/* Cover settings */}
      <div className="card">
        <h2 className="text-utility font-sf-display text-apple-ink mb-6">Che Phụ Đề Gốc</h2>

        <div className="space-y-5">
          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Cover Mode
            </label>
            <select
              value={processingOptions.cover_mode}
              onChange={(e) => updateProcessingOptions({ cover_mode: e.target.value })}
              className="input"
            >
              <option value="blur">Blur (làm mờ)</option>
              <option value="blackbar">Black Bar (thanh đen)</option>
              <option value="none">None (không che)</option>
            </select>
          </div>

          {processingOptions.cover_mode === 'blur' && (
            <div>
              <label className="block text-control font-medium text-apple-gray-secondary mb-3">
                Blur Strength: {processingOptions.cover_strength}
              </label>
              <input
                type="range"
                min="5"
                max="30"
                value={processingOptions.cover_strength}
                onChange={(e) => updateProcessingOptions({ cover_strength: parseInt(e.target.value) })}
                className="w-full accent-apple-blue"
              />
            </div>
          )}
        </div>
      </div>

      {/* Subtitle settings */}
      <div className="card">
        <h2 className="text-utility font-sf-display text-apple-ink mb-6">Phụ Đề</h2>

        <div className="space-y-5">
          <label className="flex items-center gap-3 p-4 bg-apple-gray rounded-apple-lg cursor-pointer hover:bg-apple-border-soft transition-all border border-apple-border-soft">
            <input
              type="checkbox"
              checked={processingOptions.burn_subtitle}
              onChange={(e) => updateProcessingOptions({ burn_subtitle: e.target.checked })}
              className="w-4 h-4 accent-apple-blue"
            />
            <span className="text-body text-apple-ink font-medium">Burn subtitle vào video</span>
          </label>

          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Font Scale: {processingOptions.subtitle_font_scale.toFixed(1)}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={processingOptions.subtitle_font_scale}
              onChange={(e) => updateProcessingOptions({ subtitle_font_scale: parseFloat(e.target.value) })}
              className="w-full accent-apple-blue"
            />
          </div>

          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Timing Scale: {processingOptions.subtitle_timing_scale.toFixed(1)}x
            </label>
            <input
              type="range"
              min="0.8"
              max="1.2"
              step="0.05"
              value={processingOptions.subtitle_timing_scale}
              onChange={(e) => updateProcessingOptions({ subtitle_timing_scale: parseFloat(e.target.value) })}
              className="w-full accent-apple-blue"
            />
          </div>

          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Offset (seconds): {processingOptions.subtitle_offset_sec.toFixed(2)}s
            </label>
            <input
              type="range"
              min="-5"
              max="5"
              step="0.1"
              value={processingOptions.subtitle_offset_sec}
              onChange={(e) => updateProcessingOptions({ subtitle_offset_sec: parseFloat(e.target.value) })}
              className="w-full accent-apple-blue"
            />
          </div>
        </div>
      </div>

      {/* Video settings */}
      <div className="card">
        <h2 className="text-utility font-sf-display text-apple-ink mb-6">Video</h2>

        <div className="space-y-5">
          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Video Speed: {processingOptions.video_speed.toFixed(1)}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={processingOptions.video_speed}
              onChange={(e) => updateProcessingOptions({ video_speed: parseFloat(e.target.value) })}
              className="w-full accent-apple-blue"
            />
          </div>

          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Output Format
            </label>
            <select
              value={processingOptions.output_format}
              onChange={(e) => updateProcessingOptions({ output_format: e.target.value })}
              className="input"
            >
              <option value="mp4">MP4</option>
              <option value="mkv">MKV</option>
              <option value="webm">WebM</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AdjustTab
