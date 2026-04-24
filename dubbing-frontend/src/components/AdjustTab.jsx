import useAppStore from '../store/appStore'

const AdjustTab = () => {
  const { processingOptions, updateProcessingOptions } = useAppStore()

  return (
    <div className="space-y-6">
      {/* Whisper settings */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Whisper Transcription</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-2">
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
            <label className="block text-sm font-medium text-dark-300 mb-2">
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
        <h2 className="text-xl font-semibold mb-4">Che Phụ Đề Gốc</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-2">
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
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Blur Strength: {processingOptions.cover_strength}
              </label>
              <input
                type="range"
                min="5"
                max="30"
                value={processingOptions.cover_strength}
                onChange={(e) => updateProcessingOptions({ cover_strength: parseInt(e.target.value) })}
                className="w-full"
              />
            </div>
          )}
        </div>
      </div>

      {/* Subtitle settings */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Phụ Đề</h2>

        <div className="space-y-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={processingOptions.burn_subtitle}
              onChange={(e) => updateProcessingOptions({ burn_subtitle: e.target.checked })}
            />
            <span className="text-sm">Burn subtitle vào video</span>
          </label>

          <div>
            <label className="block text-sm font-medium text-dark-300 mb-2">
              Font Scale: {processingOptions.subtitle_font_scale.toFixed(1)}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={processingOptions.subtitle_font_scale}
              onChange={(e) => updateProcessingOptions({ subtitle_font_scale: parseFloat(e.target.value) })}
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-dark-300 mb-2">
              Timing Scale: {processingOptions.subtitle_timing_scale.toFixed(1)}x
            </label>
            <input
              type="range"
              min="0.8"
              max="1.2"
              step="0.05"
              value={processingOptions.subtitle_timing_scale}
              onChange={(e) => updateProcessingOptions({ subtitle_timing_scale: parseFloat(e.target.value) })}
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-dark-300 mb-2">
              Offset (seconds): {processingOptions.subtitle_offset_sec.toFixed(2)}s
            </label>
            <input
              type="range"
              min="-5"
              max="5"
              step="0.1"
              value={processingOptions.subtitle_offset_sec}
              onChange={(e) => updateProcessingOptions({ subtitle_offset_sec: parseFloat(e.target.value) })}
              className="w-full"
            />
          </div>
        </div>
      </div>

      {/* Video settings */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Video</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-2">
              Video Speed: {processingOptions.video_speed.toFixed(1)}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={processingOptions.video_speed}
              onChange={(e) => updateProcessingOptions({ video_speed: parseFloat(e.target.value) })}
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-dark-300 mb-2">
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
