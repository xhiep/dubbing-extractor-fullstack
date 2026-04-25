import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import useAppStore from '../store/appStore'
import { ttsAPI } from '../api/client'
import SectionCard from './ui/SectionCard'
import SliderField from './ui/SliderField'

const DubTab = () => {
  const { processingOptions, updateProcessingOptions } = useAppStore()

  const [ttsStatus, setTtsStatus] = useState({ available: null, error: '' })
  const [checkingStatus, setCheckingStatus] = useState(false)
  const [voices, setVoices] = useState([])
  const [loadingVoices, setLoadingVoices] = useState(false)
  const [previewText, setPreviewText] = useState('Xin chào, đây là bài test giọng đọc tiếng Việt.')
  const [previewAudio, setPreviewAudio] = useState(null)
  const [testingVoice, setTestingVoice] = useState(false)
  const [audioPlayer, setAudioPlayer] = useState(null)

  useEffect(() => {
    checkTTSStatus()
  }, [processingOptions.dub_backend_mode, processingOptions.dub_remote_api_base])

  const checkTTSStatus = async () => {
    setCheckingStatus(true)
    try {
      const result = await ttsAPI.checkStatus({
        engine_mode: processingOptions.dub_backend_mode || 'turbo',
        backbone_repo: '',
        backbone_device: '',
        remote_api_base: processingOptions.dub_remote_api_base || 'http://localhost:23333/v1',
      })
      setTtsStatus(result)

      if (!result.available && result.error) {
        const currentMode = processingOptions.dub_backend_mode || 'turbo'
        const isGpuMode = currentMode === 'turbo_gpu' || currentMode === 'fast' || currentMode === 'xpu'
        const isCudaError = result.error.includes('CUDA') || result.error.includes('PyTorch') || result.error.includes('GPU')

        if (isGpuMode && isCudaError) {
          updateProcessingOptions({ dub_backend_mode: 'turbo' })
          toast.error(
            `Mode "${currentMode}" không khả dụng trên máy này — đã tự chuyển về "turbo" (CPU). Xem chi tiết lỗi bên dưới.`,
            { duration: 6000, position: 'bottom-left' }
          )
        }
      }
    } catch (error) {
      setTtsStatus({ available: false, error: error.message })
    } finally {
      setCheckingStatus(false)
    }
  }

  const loadVoices = async () => {
    setLoadingVoices(true)
    try {
      const result = await ttsAPI.listVoices({
        engine_mode: processingOptions.dub_backend_mode || 'turbo',
        backbone_repo: '',
        backbone_device: '',
        remote_api_base: processingOptions.dub_remote_api_base || 'http://localhost:23333/v1',
      })
      setVoices(result.voices || [])
      if (result.voices && result.voices.length > 0 && !processingOptions.dub_preset_voice) {
        updateProcessingOptions({ dub_preset_voice: result.voices[0] })
      }
    } catch (error) {
      console.error('Failed to load voices:', error)
    } finally {
      setLoadingVoices(false)
    }
  }

  const testVoice = async () => {
    if (!previewText.trim()) return

    setTestingVoice(true)
    try {
      const result = await ttsAPI.test({
        text: previewText,
        mode: processingOptions.dub_mode || 'preset',
        preset_voice: processingOptions.dub_preset_voice || '',
        ref_audio: processingOptions.dub_ref_audio || '',
        ref_text: processingOptions.dub_ref_text || '',
        engine_mode: processingOptions.dub_backend_mode || 'turbo',
        backbone_repo: '',
        backbone_device: '',
        remote_api_base: processingOptions.dub_remote_api_base || 'http://localhost:23333/v1',
      })

      setPreviewAudio(result.audio_url)

      setTimeout(() => {
        if (audioPlayer) {
          audioPlayer.play()
        }
      }, 100)
    } catch (error) {
      console.error('Failed to test voice:', error)
      alert(`Lỗi test giọng: ${error.message}`)
    } finally {
      setTestingVoice(false)
    }
  }

  const stopPreview = () => {
    if (audioPlayer) {
      audioPlayer.pause()
      audioPlayer.currentTime = 0
    }
  }

  const handleFileSelect = async () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'audio/*'
    input.onchange = async (e) => {
      const file = e.target.files[0]
      if (file) {
        try {
          const formData = new FormData()
          formData.append('file', file)

          const response = await fetch('/api/tts/upload-ref-audio', {
            method: 'POST',
            body: formData,
          })

          if (!response.ok) {
            throw new Error('Upload failed')
          }

          const data = await response.json()
          updateProcessingOptions({ dub_ref_audio: data.file_path })
          toast.success(`Đã upload: ${file.name}`, {
            duration: 3000,
            position: 'bottom-left',
          })
        } catch (error) {
          toast.error(`Lỗi upload: ${error.message}`, {
            duration: 4000,
            position: 'bottom-left',
          })
        }
      }
    }
    input.click()
  }

  return (
    <div className="space-y-6">

      {/* Trạng thái TTS */}
      <SectionCard title="Trạng Thái VieNeu-TTS">
        <div className="space-y-3">
          {checkingStatus ? (
            <div className="flex items-center gap-2 text-control text-apple-gray-secondary">
              <div className="w-2 h-2 rounded-full bg-apple-gray-secondary animate-pulse" />
              Đang kiểm tra...
            </div>
          ) : ttsStatus.available === true ? (
            <div className="flex items-center gap-2 text-control text-green-600">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              VieNeu-TTS sẵn sàng ({processingOptions.dub_backend_mode || 'turbo'})
            </div>
          ) : ttsStatus.available === false ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-control text-red-600">
                <div className="w-2 h-2 rounded-full bg-red-500" />
                VieNeu-TTS không khả dụng với mode &quot;{processingOptions.dub_backend_mode || 'turbo'}&quot;
              </div>
              {ttsStatus.error && (
                <div className="notice-error rounded-apple-md p-3 space-y-2">
                  <p className="text-footnote text-apple-gray-secondary">{ttsStatus.error}</p>
                  {(() => {
                    const err = ttsStatus.error
                    const isCuda = err.includes('CUDA') || err.includes('PyTorch') || err.includes('GPU')
                    const isWindows = err.includes('Windows') || err.includes('LMDeploy') || err.includes('Triton')
                    const isXpu = err.includes('intel') || err.includes('ipex') || err.includes('xpu')
                    if (isCuda || isWindows || isXpu) {
                      return (
                        <div className="notice-warning p-3 rounded-apple-md">
                          <p className="text-footnote font-semibold text-yellow-800 mb-1">Gợi ý khắc phục:</p>
                          <ul className="list-disc list-inside text-footnote text-yellow-800 space-y-1">
                            {isCuda && <li>Chọn mode <strong>turbo</strong> (CPU) hoặc <strong>standard</strong> (CPU/GPU tự động) bên dưới.</li>}
                            {isCuda && <li>Nếu có GPU NVIDIA: cài lại PyTorch bản CUDA tại <strong>pytorch.org</strong>.</li>}
                            {isWindows && <li>Mode <strong>fast</strong> không hỗ trợ Windows — chọn <strong>turbo_gpu</strong> thay thế.</li>}
                            {isXpu && <li>Mode <strong>xpu</strong> cần Intel Extension for PyTorch — xem <strong>intel.github.io/intel-extension-for-pytorch</strong>.</li>}
                            <li>Dùng mode <strong>remote</strong> để kết nối server TTS chạy trên máy khác.</li>
                          </ul>
                        </div>
                      )
                    }
                    return null
                  })()}
                </div>
              )}
            </div>
          ) : (
            <div className="text-control text-apple-gray-secondary">Chưa kiểm tra</div>
          )}

          <button
            onClick={checkTTSStatus}
            disabled={checkingStatus}
            className="btn btn-tertiary rounded-apple-md px-4 py-2 text-control"
          >
            {checkingStatus ? 'Đang kiểm tra...' : 'Kiểm Tra Lại'}
          </button>
        </div>
      </SectionCard>

      {/* Bật lồng tiếng */}
      <div className="card">
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={processingOptions.enable_dub || false}
            onChange={(e) => updateProcessingOptions({ enable_dub: e.target.checked })}
            className="mt-1 w-5 h-5 rounded border-apple-border-soft accent-apple-blue"
          />
          <div className="flex-1">
            <div className="text-body font-semibold text-apple-ink">Bật Lồng Tiếng Tiếng Việt</div>
            <div className="text-control text-apple-gray-secondary mt-1">
              Tự động tạo giọng đọc tiếng Việt và trộn vào video.
            </div>
          </div>
        </label>
      </div>

      {processingOptions.enable_dub && (
        <>
          {/* Chế độ giọng */}
          <SectionCard title="Chế Độ Giọng">
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="dub_mode"
                  value="preset"
                  checked={processingOptions.dub_mode === 'preset'}
                  onChange={(e) => updateProcessingOptions({ dub_mode: e.target.value })}
                  className="w-4 h-4 accent-apple-blue"
                />
                <span className="text-body text-apple-ink">Giọng Mẫu</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="dub_mode"
                  value="clone"
                  checked={processingOptions.dub_mode === 'clone'}
                  onChange={(e) => updateProcessingOptions({ dub_mode: e.target.value })}
                  className="w-4 h-4 accent-apple-blue"
                />
                <span className="text-body text-apple-ink">Clone Từ File</span>
              </label>
            </div>
          </SectionCard>

          {/* Backend VieNeu */}
          <SectionCard title="Backend VieNeu">
            <div className="space-y-3">
              <select
                value={processingOptions.dub_backend_mode || 'turbo'}
                onChange={(e) => updateProcessingOptions({ dub_backend_mode: e.target.value })}
                className="input w-full"
              >
                <option value="turbo">turbo (CPU nhanh)</option>
                <option value="turbo_gpu">turbo_gpu (GPU)</option>
                <option value="standard">standard (CPU/GPU)</option>
                <option value="fast">fast (LMDeploy — không hỗ trợ Windows)</option>
                <option value="remote">remote (Server API)</option>
                <option value="xpu">xpu (Intel GPU)</option>
              </select>
              <div className="text-footnote text-apple-gray-secondary">
                turbo = CPU nhanh | turbo_gpu/fast = GPU | remote = server
              </div>
            </div>
          </SectionCard>

          {/* Remote API URL */}
          {processingOptions.dub_backend_mode === 'remote' && (
            <SectionCard title="Remote API URL">
              <input
                type="text"
                value={processingOptions.dub_remote_api_base || 'http://localhost:23333/v1'}
                onChange={(e) => updateProcessingOptions({ dub_remote_api_base: e.target.value })}
                className="input w-full"
                placeholder="http://localhost:23333/v1"
              />
            </SectionCard>
          )}

          {/* Giọng mẫu */}
          {processingOptions.dub_mode === 'preset' && (
            <SectionCard title="Giọng Mẫu">
              <div className="flex gap-3">
                <select
                  value={processingOptions.dub_preset_voice || ''}
                  onChange={(e) => updateProcessingOptions({ dub_preset_voice: e.target.value })}
                  className="input flex-1"
                  disabled={voices.length === 0}
                >
                  {voices.length === 0 ? (
                    <option value="">Chưa có giọng nào</option>
                  ) : (
                    voices.map((voice) => (
                      <option key={voice} value={voice}>{voice}</option>
                    ))
                  )}
                </select>
                <button
                  onClick={loadVoices}
                  disabled={loadingVoices}
                  className="btn btn-tertiary rounded-apple-md px-6"
                >
                  {loadingVoices ? 'Đang tải...' : 'Tải Danh Sách Giọng'}
                </button>
              </div>
            </SectionCard>
          )}

          {/* Clone giọng */}
          {processingOptions.dub_mode === 'clone' && (
            <SectionCard title="Clone Giọng">
              <div>
                <label className="block text-control font-medium text-apple-gray-secondary mb-2">
                  File Giọng Mẫu
                </label>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={processingOptions.dub_ref_audio || ''}
                    onChange={(e) => updateProcessingOptions({ dub_ref_audio: e.target.value })}
                    className="input flex-1"
                    placeholder="Đường dẫn file audio mẫu..."
                  />
                  <button
                    onClick={handleFileSelect}
                    className="btn btn-tertiary rounded-apple-md px-6"
                  >
                    Chọn File
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-control font-medium text-apple-gray-secondary mb-2">
                  Nội Dung File Mẫu
                </label>
                <textarea
                  value={processingOptions.dub_ref_text || ''}
                  onChange={(e) => updateProcessingOptions({ dub_ref_text: e.target.value })}
                  rows={3}
                  className="input w-full resize-none"
                  placeholder="Nhập nội dung của file audio mẫu..."
                />
              </div>
            </SectionCard>
          )}

          {/* Trộn audio */}
          <SectionCard title="Trộn Audio">
            <SliderField
              label="Âm Lượng Giọng Đọc"
              value={processingOptions.dub_voice_volume || 1.35}
              displayValue={String(processingOptions.dub_voice_volume || 1.35)}
              min={0.5}
              max={3.0}
              step={0.05}
              onChange={(v) => updateProcessingOptions({ dub_voice_volume: v })}
            />
            <p className="text-footnote text-apple-gray-secondary -mt-3">
              1.0 = giữ nguyên | tăng nếu giọng đọc còn nhỏ
            </p>

            <SliderField
              label="Âm Lượng Gốc"
              value={processingOptions.dub_source_volume || 0.18}
              displayValue={String(processingOptions.dub_source_volume || 0.18)}
              min={0.0}
              max={1.0}
              step={0.05}
              onChange={(v) => updateProcessingOptions({ dub_source_volume: v })}
            />
            <p className="text-footnote text-apple-gray-secondary -mt-3">
              0 = tắt tiếng gốc, 0.18 = nền nhỏ phía sau
            </p>

            <div>
              <label className="block text-control font-medium text-apple-gray-secondary mb-2">
                Cách Mix Audio
              </label>
              <select
                value={processingOptions.dub_mix_mode || 'ducking_thong_minh'}
                onChange={(e) => updateProcessingOptions({ dub_mix_mode: e.target.value })}
                className="input w-full"
              >
                <option value="ducking_thong_minh">Ducking Thông Minh (ưu tiên giọng lồng tiếng)</option>
                <option value="nen_nho">Nền Nhỏ (giữ nhạc nền nhỏ)</option>
                <option value="tat_goc">Tắt Gốc (tắt audio gốc)</option>
              </select>
              <div className="text-footnote text-apple-gray-secondary mt-1">
                Ducking thông minh sẽ hạ nhỏ audio gốc khi có giọng đọc. Nền nhỏ giữ nhạc nền nhẹ. Tắt gốc sẽ tắt hoàn toàn audio gốc.
              </div>
            </div>
          </SectionCard>

          {/* Nghe thử */}
          <SectionCard title="Nghe Thử Giọng">
            <div>
              <label className="block text-control font-medium text-apple-gray-secondary mb-2">
                Text Nghe Thử
              </label>
              <textarea
                value={previewText}
                onChange={(e) => setPreviewText(e.target.value)}
                rows={4}
                className="input w-full resize-none"
                placeholder="Nhập text để nghe thử giọng đọc..."
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={testVoice}
                disabled={testingVoice || !previewText.trim()}
                className="btn btn-primary rounded-apple-md"
              >
                {testingVoice ? 'Đang Tạo...' : 'Nghe Thử Giọng'}
              </button>

              <button
                onClick={stopPreview}
                disabled={!previewAudio}
                className="btn btn-tertiary rounded-apple-md"
              >
                Dừng Nghe Thử
              </button>
            </div>

            {previewAudio && (
              <div className="surface-subtle rounded-apple-md p-4">
                <audio
                  ref={setAudioPlayer}
                  controls
                  src={previewAudio}
                  className="w-full"
                />
              </div>
            )}
          </SectionCard>

          {/* Hướng dẫn */}
          <div className="card notice-info">
            <h3 className="text-body font-semibold text-blue-900 mb-2">Hướng Dẫn Sử Dụng</h3>
            <ul className="text-control text-blue-800 space-y-1 list-disc list-inside">
              <li>Giọng mẫu: dùng nhanh, không cần file mẫu.</li>
              <li>Clone giọng: nên dùng file 3–5 giây, 1 người nói rõ, ít nhạc nền, ít vang.</li>
              <li>Mode VieNeu: turbo=CPU GGUF, turbo_gpu=GPU, standard=CPU/GPU, fast=LMDeploy, remote=server API, xpu=Intel GPU.</li>
              <li>Thời gian xử lý: khoảng 1–2 phút cho video 10 phút.</li>
              <li>Câu ngắn 5–15 từ cho kết quả tốt nhất.</li>
            </ul>
          </div>
        </>
      )}
    </div>
  )
}

export default DubTab
