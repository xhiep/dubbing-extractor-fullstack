import { useEffect, useRef, useState } from 'react'
import { FileVideo, Loader2, Play, RotateCcw } from 'lucide-react'
import useAppStore from '../store/appStore'
import { usePreview } from '../hooks/useProcessing'
import { apiClient } from '../api/client'
import PreviewCanvas, { getRepresentativeSubtitleBand } from './PreviewCanvas'
import SectionCard from './ui/SectionCard'
import SliderField from './ui/SliderField'

const SUBTITLE_PRESETS = {
  custom: null,
  default: {
    subtitle_font_scale: 1.0,
    subtitle_font_size: 0,
    subtitle_margin_px: 0,
    srt_max_chars_per_line: 45,
    subtitle_offset_sec: 0.0,
    subtitle_timing_scale: 1.0,
  },
  large: {
    subtitle_font_scale: 1.4,
    subtitle_font_size: 0,
    subtitle_margin_px: 16,
    srt_max_chars_per_line: 34,
    subtitle_offset_sec: 0.0,
    subtitle_timing_scale: 1.0,
  },
  compact: {
    subtitle_font_scale: 0.85,
    subtitle_font_size: 0,
    subtitle_margin_px: -8,
    srt_max_chars_per_line: 52,
    subtitle_offset_sec: 0.0,
    subtitle_timing_scale: 1.0,
  },
  tiktok: {
    subtitle_font_scale: 1.55,
    subtitle_font_size: 0,
    subtitle_margin_px: 44,
    srt_max_chars_per_line: 24,
    subtitle_offset_sec: 0.0,
    subtitle_timing_scale: 1.0,
  },
  anime: {
    subtitle_font_scale: 1.15,
    subtitle_font_size: 30,
    subtitle_margin_px: 30,
    srt_max_chars_per_line: 32,
    subtitle_offset_sec: 0.0,
    subtitle_timing_scale: 1.0,
  },
}

const AdjustTab = () => {
  const { processingOptions, updateProcessingOptions, outputs, preview } = useAppStore()
  const [previewText, setPreviewText] = useState('Dòng phụ đề mẫu số 1\nDòng phụ đề mẫu số 2')
  const [subtitlePreset, setSubtitlePreset] = useState('default')
  const [previewRenderLoading, setPreviewRenderLoading] = useState(false)
  const [previewRenderUrl, setPreviewRenderUrl] = useState(null)
  const [previewStartTime, setPreviewStartTime] = useState(1)
  const [previewDuration, setPreviewDuration] = useState(5)
  const [previewLayout, setPreviewLayout] = useState(null)
  const [previewLayoutLoading, setPreviewLayoutLoading] = useState(false)
  const videoRef = useRef(null)
  const { data: previewInfo } = usePreview(processingOptions.source)

  const effectivePreview = previewInfo || preview
  const previewTotalDuration = Math.max(3, Math.floor(effectivePreview?.duration || 18))
  const renderVideoSpeed = processingOptions.render_video_speed ?? processingOptions.video_speed ?? 1.0
  const outputVideoSpeed = processingOptions.output_video_speed ?? processingOptions.video_speed ?? 1.0
  const exportVsRenderFactor = outputVideoSpeed / Math.max(0.01, renderVideoSpeed)

  const buildLayoutPayload = () => ({
    source: processingOptions.source,
    start_time: previewStartTime,
    duration: Math.min(3, previewDuration),
    preview_text: previewText,
    burn_subtitle: processingOptions.burn_subtitle,
    srt_max_chars_per_line: processingOptions.srt_max_chars_per_line,
    cover_mode: processingOptions.cover_mode,
    cover_strength: processingOptions.cover_strength,
    subtitle_font_scale: processingOptions.subtitle_font_scale,
    subtitle_font_size: processingOptions.subtitle_font_size,
    subtitle_margin_px: processingOptions.subtitle_margin_px,
    blur_padding_px: processingOptions.blur_padding_px,
    cover_offset_px: processingOptions.cover_offset_px,
    render_video_speed: renderVideoSpeed,
    video_speed: renderVideoSpeed,
  })

  const fetchLatestPreviewLayout = async () => {
    const response = await apiClient.post('/preview-render/layout', buildLayoutPayload())
    setPreviewLayout(response.data)
    return response.data
  }

  useEffect(() => {
    if (outputs.video_path && videoRef.current) {
      const filename = outputs.video_path.split('/').pop()
      videoRef.current.src = `/output/${filename}`
    }
  }, [outputs.video_path])

  useEffect(() => {
    setPreviewRenderUrl(null)
    // Reset locked subtitle position when start time changes to force re-detection
    updateProcessingOptions({
      locked_subtitle_top_y: null,
      locked_subtitle_bottom_y: null,
    })
  }, [
    previewStartTime,
  ])

  useEffect(() => {
    setPreviewRenderUrl(null)
  }, [
    previewText,
    previewDuration,
    processingOptions.cover_mode,
    processingOptions.cover_strength,
    processingOptions.burn_subtitle,
    processingOptions.srt_max_chars_per_line,
    processingOptions.subtitle_font_scale,
    processingOptions.subtitle_font_size,
    processingOptions.subtitle_margin_px,
    processingOptions.subtitle_timing_scale,
    processingOptions.subtitle_offset_sec,
    processingOptions.blur_padding_px,
    processingOptions.cover_offset_px,
    renderVideoSpeed,
  ])

  useEffect(() => {
    if (!processingOptions.source || !effectivePreview) {
      setPreviewLayout(null)
      return
    }

    let cancelled = false
    const timer = setTimeout(async () => {
      setPreviewLayoutLoading(true)
      try {
        const response = await apiClient.post('/preview-render/layout', buildLayoutPayload())
        if (!cancelled) {
          setPreviewLayout(response.data)
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Preview layout failed:', error)
          setPreviewLayout(null)
        }
      } finally {
        if (!cancelled) {
          setPreviewLayoutLoading(false)
        }
      }
    }, 350)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [
    processingOptions.source,
    effectivePreview,
    previewText,
    previewStartTime,
    previewDuration,
    processingOptions.cover_mode,
    processingOptions.cover_strength,
    processingOptions.burn_subtitle,
    processingOptions.srt_max_chars_per_line,
    processingOptions.subtitle_font_scale,
    processingOptions.subtitle_font_size,
    processingOptions.subtitle_margin_px,
    processingOptions.blur_padding_px,
    processingOptions.cover_offset_px,
    renderVideoSpeed,
  ])

  useEffect(() => {
    if (!previewLayout) return

    const nextTop = previewLayout.subtitle_top_y ?? null
    const nextBottom = previewLayout.subtitle_bottom_y ?? null

    if (
      processingOptions.locked_subtitle_top_y !== nextTop ||
      processingOptions.locked_subtitle_bottom_y !== nextBottom
    ) {
      updateProcessingOptions({
        locked_subtitle_top_y: nextTop,
        locked_subtitle_bottom_y: nextBottom,
      })
    }
  }, [
    previewLayout,
    processingOptions.locked_subtitle_top_y,
    processingOptions.locked_subtitle_bottom_y,
    updateProcessingOptions,
  ])

  useEffect(() => {
    const matchedPreset = Object.entries(SUBTITLE_PRESETS).find(([key, value]) => (
      key !== 'custom' &&
      value.subtitle_font_scale === processingOptions.subtitle_font_scale &&
      value.subtitle_font_size === processingOptions.subtitle_font_size &&
      value.subtitle_margin_px === processingOptions.subtitle_margin_px &&
      value.srt_max_chars_per_line === processingOptions.srt_max_chars_per_line &&
      value.subtitle_offset_sec === processingOptions.subtitle_offset_sec &&
      value.subtitle_timing_scale === processingOptions.subtitle_timing_scale
    ))
    setSubtitlePreset(matchedPreset?.[0] || 'custom')
  }, [
    processingOptions.subtitle_font_scale,
    processingOptions.subtitle_font_size,
    processingOptions.subtitle_margin_px,
    processingOptions.srt_max_chars_per_line,
    processingOptions.subtitle_offset_sec,
    processingOptions.subtitle_timing_scale,
  ])

  const applyPreset = (presetKey) => {
    setSubtitlePreset(presetKey)
    const preset = SUBTITLE_PRESETS[presetKey]
    if (preset) updateProcessingOptions(preset)
  }

  const resetPreviewPosition = () => {
    updateProcessingOptions({
      subtitle_margin_px: 0,
      subtitle_offset_sec: 0.0,
      blur_padding_px: 12,
      cover_offset_px: 0,
    })
  }

  const resetPreviewStyle = () => {
    applyPreset('default')
    updateProcessingOptions({
      cover_strength: 15,
      blur_padding_px: 12,
      cover_offset_px: 0,
    })
  }

  const handleSubtitleDrag = (nextMargin) => {
    updateProcessingOptions({
      subtitle_margin_px: Math.max(-240, Math.min(240, nextMargin)),
    })
  }

  const handleRenderPreview = async () => {
    if (!processingOptions.source) {
      alert('Vui lòng nhập URL video ở tab Nguồn Video')
      return
    }

    setPreviewRenderLoading(true)
    setPreviewRenderUrl(null)

    let timeoutId = null

    try {
      // Set timeout for 60 seconds
      const timeoutPromise = new Promise((_, reject) => {
        timeoutId = setTimeout(() => {
          reject(new Error('Render preview timeout - vui lòng thử lại hoặc giảm duration'))
        }, 60000)
      })

      const renderPromise = (async () => {
        const latestLayout = await fetchLatestPreviewLayout()
        const subtitleBand = latestLayout?.subtitle_top_y != null && latestLayout?.subtitle_bottom_y != null
          ? { topY: latestLayout.subtitle_top_y, bottomY: latestLayout.subtitle_bottom_y }
          : getRepresentativeSubtitleBand(effectivePreview?.height || 1080)

        const response = await apiClient.post('/preview-render/render', {
          source: processingOptions.source,
          start_time: previewStartTime,
          duration: previewDuration,
          preview_text: previewText,
          cover_mode: processingOptions.cover_mode,
          cover_strength: processingOptions.cover_strength,
          burn_subtitle: processingOptions.burn_subtitle,
          subtitle_font_scale: processingOptions.subtitle_font_scale,
          subtitle_font_size: processingOptions.subtitle_font_size,
          subtitle_margin_px: processingOptions.subtitle_margin_px,
          srt_max_chars_per_line: processingOptions.srt_max_chars_per_line,
          blur_padding_px: processingOptions.blur_padding_px,
          cover_offset_px: processingOptions.cover_offset_px,
          preview_subtitle_top_y: subtitleBand.topY,
          preview_subtitle_bottom_y: subtitleBand.bottomY,
          render_video_speed: renderVideoSpeed,
          output_video_speed: outputVideoSpeed,
          video_speed: renderVideoSpeed,
        })

        return response
      })()

      const response = await Promise.race([renderPromise, timeoutPromise])

      if (timeoutId) {
        clearTimeout(timeoutId)
      }

      setPreviewRenderUrl(response.data.video_url)
    } catch (error) {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      console.error('Preview render failed:', error)
      alert(`Lỗi render preview: ${error.response?.data?.detail || error.message}`)
    } finally {
      setPreviewRenderLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)] gap-8 items-start">

      {/* ── Cột trái: Preview (sticky) ── */}
      <div className="xl:sticky xl:top-28 space-y-6">
        <div className="card">
          <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end">
            <div className="flex-1">
              <h2 className="text-utility font-sf-display text-apple-ink">Video Preview</h2>
              <p className="mt-2 text-control text-apple-gray-secondary">
                Tab này tự lấy frame preview từ backend. Không cần bấm preview ở tab Nguồn trước.
              </p>
            </div>
            <button
              onClick={handleRenderPreview}
              disabled={previewRenderLoading || previewLayoutLoading || !processingOptions.source}
              className="btn btn-primary px-6 py-3 rounded-apple-md flex items-center gap-2 self-start"
            >
              {previewRenderLoading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Đang render...
                </>
              ) : (
                <>
                  <Play className="h-5 w-5" />
                  Render Preview
                </>
              )}
            </button>
          </div>

          {/* Timeline controls */}
          <div className="surface-subtle rounded-apple-lg px-4 py-4 mb-4">
            <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-3 items-end">
              <div>
                <label className="block text-control font-medium text-apple-gray-secondary mb-2">
                  Start Time (giây)
                </label>
                <input
                  type="number"
                  min="1"
                  max={previewTotalDuration}
                  step="1"
                  value={previewStartTime}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value)
                    if (isNaN(val)) {
                      setPreviewStartTime(1)
                    } else {
                      setPreviewStartTime(Math.max(1, Math.min(previewTotalDuration, Math.floor(val))))
                    }
                  }}
                  className="input"
                />
              </div>
              <div>
                <label className="block text-control font-medium text-apple-gray-secondary mb-2">
                  Duration (backend clip 3–8s)
                </label>
                <input
                  type="number"
                  min="3"
                  max="8"
                  step="1"
                  value={previewDuration}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value)
                    if (isNaN(val)) {
                      setPreviewDuration(5)
                    } else {
                      setPreviewDuration(Math.max(3, Math.min(8, Math.floor(val))))
                    }
                  }}
                  className="input"
                />
              </div>
              <div className="text-right">
                <p className="text-body-emphasis text-apple-ink">{previewStartTime.toFixed(1)}s</p>
                <p className="text-micro text-apple-gray-secondary">/ {previewTotalDuration}s</p>
              </div>
            </div>

            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between gap-4">
                <p className="text-control font-medium text-apple-ink">Timeline Preview</p>
                <p className="text-micro text-apple-gray-secondary">
                  Chọn mốc timeline rồi render backend clip ngắn tại mốc đó.
                </p>
              </div>
              <input
                type="range"
                min="1"
                max={previewTotalDuration}
                step="0.5"
                value={Math.max(1, Math.min(previewStartTime, previewTotalDuration))}
                onChange={(e) => setPreviewStartTime(Math.max(1, parseFloat(e.target.value)))}
                className="w-full accent-apple-blue"
                disabled={!processingOptions.source}
              />
            </div>
          </div>

          {/* Preview canvas */}
          <div className="bg-apple-black rounded-apple-xl overflow-hidden aspect-video flex items-center justify-center relative">
            {previewRenderUrl ? (
              <video
                key={previewRenderUrl}
                controls
                autoPlay
                className="w-full h-full object-contain"
                src={previewRenderUrl}
              >
                Video không được hỗ trợ
              </video>
            ) : previewLayout?.image_url ? (
              <PreviewCanvas
                imageUrl={previewLayout.image_url}
                renderedPreview
                previewText={processingOptions.burn_subtitle ? previewText : ''}
                coverMode={processingOptions.cover_mode}
                coverStrength={processingOptions.cover_strength}
                subtitleFontScale={processingOptions.subtitle_font_scale}
                subtitleFontSize={processingOptions.subtitle_font_size}
                subtitleMargin={processingOptions.subtitle_margin_px}
                blurPadding={processingOptions.blur_padding_px}
                coverOffset={processingOptions.cover_offset_px}
                maxCharsPerLine={processingOptions.srt_max_chars_per_line}
                previewWidth={previewLayout.width}
                previewHeight={previewLayout.height}
                subtitleTopY={previewLayout.subtitle_top_y}
                subtitleBottomY={previewLayout.subtitle_bottom_y}
                subtitleFontSizeExact={previewLayout.subtitle_layout?.font_size}
                subtitleMarginVExact={previewLayout.subtitle_layout?.margin_v}
                interactive
                onSubtitleDrag={handleSubtitleDrag}
              />
            ) : processingOptions.source && (previewLayoutLoading || effectivePreview) ? (
              <div className="text-apple-gray-secondary text-center px-6">
                <Loader2 className="w-12 h-12 mx-auto mb-3 animate-spin opacity-70" />
                <p className="text-control">Đang tạo frame preview từ backend...</p>
                <p className="text-micro mt-1">Frame này được cập nhật độc lập với tab Nguồn Video.</p>
              </div>
            ) : outputs.video_path ? (
              <video ref={videoRef} controls className="w-full h-full object-contain">
                Video không được hỗ trợ
              </video>
            ) : (
              <div className="text-apple-gray-secondary text-center px-6">
                <FileVideo className="w-16 h-16 mx-auto mb-3 opacity-50" />
                <p className="text-control">Video preview sẽ hiển thị ở đây</p>
                <p className="text-micro mt-1">Nhập URL ở tab Nguồn Video và backend sẽ tự tạo frame preview.</p>
              </div>
            )}
          </div>

          {previewRenderLoading && (
            <div className="notice-info rounded-apple-xl p-4 mt-4">
              <p className="text-blue-600 text-control font-medium">
                Đang render preview video với blur và subtitle...
              </p>
            </div>
          )}

          {previewLayoutLoading && !previewRenderLoading && (
            <div className="notice-info rounded-apple-xl p-4 mt-4">
              <p className="text-blue-600 text-control font-medium">
                Đang đồng bộ frame preview thật từ backend...
              </p>
            </div>
          )}

          {/* Preview text + reset */}
          <div className="mt-4">
            <label className="block text-control font-medium text-apple-gray-secondary mb-2">
              Preview Text
            </label>
            <textarea
              value={previewText}
              onChange={(e) => setPreviewText(e.target.value)}
              placeholder="Nhập text để xem preview subtitle..."
              rows={4}
              className="input resize-none"
            />
            <div className="mt-3 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={resetPreviewPosition}
                className="btn btn-secondary px-4 py-2 rounded-apple-md flex items-center gap-2"
              >
                <RotateCcw className="h-4 w-4" />
                Reset Vị Trí
              </button>
              <button
                type="button"
                onClick={resetPreviewStyle}
                className="btn btn-secondary px-4 py-2 rounded-apple-md flex items-center gap-2"
              >
                <RotateCcw className="h-4 w-4" />
                Reset Style
              </button>
            </div>
            <p className="text-micro text-apple-gray-secondary mt-3">
              Kéo trực tiếp subtitle trên khung preview để căn vị trí độc trước khi render.
            </p>
          </div>
        </div>
      </div>

      {/* ── Cột phải: Controls ── */}
      <div className="space-y-6">

        <SectionCard title="Whisper Transcription">
          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Model Size
            </label>
            <select
              value={processingOptions.whisper_model}
              onChange={(e) => updateProcessingOptions({ whisper_model: e.target.value })}
              className="input"
            >
              <option value="tiny">Tiny (nhanh nhất, kém chính xác nhất)</option>
              <option value="base">Base</option>
              <option value="small">Small</option>
              <option value="medium">Medium (khuyến dùng)</option>
              <option value="large">Large (chậm nhất, chính xác nhất)</option>
            </select>
          </div>

          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Language (để trống để auto-detect)
            </label>
            <input
              type="text"
              value={processingOptions.whisper_language || ''}
              onChange={(e) => updateProcessingOptions({ whisper_language: e.target.value || null })}
              placeholder="en, vi, ja, ko..."
              className="input"
            />
          </div>
        </SectionCard>

        <SectionCard title="Che Phủ Đề Gốc">
          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Cover Mode
            </label>
            <select
              value={processingOptions.cover_mode}
              onChange={(e) => updateProcessingOptions({ cover_mode: e.target.value })}
              className="input"
            >
              <option value="blur">Blur</option>
              <option value="blackbar">Black Bar</option>
              <option value="none">None</option>
            </select>
          </div>

          {processingOptions.cover_mode === 'blur' && (
            <SliderField
              label="Blur Strength"
              value={processingOptions.cover_strength}
              min={5}
              max={30}
              step={1}
              onChange={(v) => updateProcessingOptions({ cover_strength: Math.round(v) })}
            />
          )}

          <SliderField
            label="Blur Padding"
            value={processingOptions.blur_padding_px}
            unit="px"
            min={0}
            max={200}
            step={2}
            onChange={(v) => updateProcessingOptions({ blur_padding_px: Math.round(v) })}
          />

          <SliderField
            label="Cover Offset"
            value={processingOptions.cover_offset_px}
            unit="px"
            min={-240}
            max={240}
            step={2}
            onChange={(v) => updateProcessingOptions({ cover_offset_px: Math.round(v) })}
          />
        </SectionCard>

        <SectionCard title="Phụ Đề">
          <div>
            <label className="block text-control font-medium text-apple-gray-secondary mb-3">
              Subtitle Preset
            </label>
            <select
              value={subtitlePreset}
              onChange={(e) => applyPreset(e.target.value)}
              className="input"
            >
              <option value="custom">Tùy chỉnh</option>
              <option value="default">Mặc định</option>
              <option value="large">Chữ lớn</option>
              <option value="compact">Gọn</option>
              <option value="tiktok">TikTok</option>
              <option value="anime">Kiểu Anime</option>
            </select>
          </div>

          <label className="option-card flex items-center gap-3 p-4 rounded-apple-lg cursor-pointer transition-all">
            <input
              type="checkbox"
              checked={processingOptions.burn_subtitle}
              onChange={(e) => updateProcessingOptions({ burn_subtitle: e.target.checked })}
              className="w-4 h-4 accent-apple-blue"
            />
            <span className="text-body text-apple-ink font-medium">Burn subtitle vào video</span>
          </label>

          <SliderField
            label="Font Scale"
            value={processingOptions.subtitle_font_scale}
            displayValue={`${processingOptions.subtitle_font_scale.toFixed(1)}x`}
            min={0.5}
            max={2.5}
            step={0.1}
            onChange={(v) => updateProcessingOptions({ subtitle_font_scale: v })}
          />

          <SliderField
            label="Font Size"
            value={processingOptions.subtitle_font_size}
            displayValue={processingOptions.subtitle_font_size === 0 ? 'Auto' : `${processingOptions.subtitle_font_size}px`}
            min={0}
            max={96}
            step={1}
            onChange={(v) => updateProcessingOptions({ subtitle_font_size: Math.round(v) })}
          />

          <SliderField
            label="Vertical Offset"
            value={processingOptions.subtitle_margin_px}
            unit="px"
            min={-240}
            max={240}
            step={4}
            onChange={(v) => updateProcessingOptions({ subtitle_margin_px: Math.round(v) })}
          />

          <SliderField
            label="Max Chars Per Line"
            value={processingOptions.srt_max_chars_per_line}
            min={20}
            max={80}
            step={1}
            onChange={(v) => updateProcessingOptions({ srt_max_chars_per_line: Math.round(v) })}
          />

          <SliderField
            label="Timing Scale"
            value={processingOptions.subtitle_timing_scale}
            displayValue={`${processingOptions.subtitle_timing_scale.toFixed(1)}x`}
            min={0.8}
            max={1.2}
            step={0.05}
            onChange={(v) => updateProcessingOptions({ subtitle_timing_scale: v })}
          />

          <SliderField
            label="Offset"
            value={processingOptions.subtitle_offset_sec}
            displayValue={`${processingOptions.subtitle_offset_sec.toFixed(2)}s`}
            min={-5}
            max={5}
            step={0.1}
            onChange={(v) => updateProcessingOptions({ subtitle_offset_sec: v })}
          />
        </SectionCard>

        <SectionCard title="Video">
          <SliderField
            label="Render Speed"
            value={renderVideoSpeed}
            displayValue={`${renderVideoSpeed.toFixed(1)}x`}
            min={0.5}
            max={2.0}
            step={0.1}
            onChange={(v) => updateProcessingOptions({ render_video_speed: v, video_speed: v })}
          />

          <SliderField
            label="Output Speed"
            value={outputVideoSpeed}
            displayValue={`${outputVideoSpeed.toFixed(1)}x so với video gốc`}
            min={0.5}
            max={2.0}
            step={0.1}
            onChange={(v) => updateProcessingOptions({ output_video_speed: v })}
          />

          <div className="surface-subtle rounded-apple-lg p-4 space-y-2">
            <p className="text-control font-medium text-apple-ink">
              Render = tốc độ dùng cho cover + subtitle timing + lồng tiếng
            </p>
            <p className="text-control text-apple-gray-secondary">
              Output = tốc độ file xuất cuối cùng so với video gốc.
            </p>
            <p className="text-control text-apple-gray-secondary">
              Hệ số retime cuối: {outputVideoSpeed.toFixed(2)} / {renderVideoSpeed.toFixed(2)} = {exportVsRenderFactor.toFixed(2)}x
            </p>
            <p className="text-micro text-apple-gray-secondary">
              Ví dụ: render 0.8x + output 1.0x nghĩa là pipeline xử lý và lồng tiếng trên timeline chậm hơn, sau đó file cuối được đưa về tốc độ gốc 1.0x.
            </p>
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
        </SectionCard>

      </div>
    </div>
  )
}

export default AdjustTab
