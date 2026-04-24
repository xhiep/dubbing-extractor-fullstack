import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import useAppStore from '../store/appStore'
import { ttsAPI } from '../api/client'

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

      if (!result.available && result.error && result.error.includes('CUDA')) {
        const currentMode = processingOptions.dub_backend_mode || 'turbo'
        if (currentMode === 'turbo_gpu' || currentMode === 'fast') {
          updateProcessingOptions({ dub_backend_mode: 'turbo' })
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
      <div className="card">
        <h2 className="text-headline font-sf-display text-apple-ink mb-4">Trạng Thái VieNeu-TTS</h2>

        <div className="space-y-3">
          {checkingStatus ? (
            <div className="text-control text-apple-gray-secondary">Đang kiểm tra...</div>
          ) : ttsStatus.available === true ? (
            <div className="flex items-center gap-2 text-control text-green-600">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              VieNeu-TTS sẵn sàng
            </div>
          ) : ttsStatus.available === false ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-control text-red-600">
                <div className="w-2 h-2 rounded-full bg-red-500" />
                VieNeu-TTS không khả dụng
              </div>
              {ttsStatus.error && (
                <div className="surface-subtle text-footnote text-apple-gray-secondary rounded-apple-md p-3">
                  {ttsStatus.error}
                  {ttsStatus.error.includes('CUDA') && (
                    <div className="notice-warning mt-2 p-3 rounded-apple-md text-yellow-800">
                      <strong>Giải pháp:</strong>
                      <ul className="list-disc list-inside mt-1 text-xs">
                        <li>Đổi sang mode &quot;turbo (CPU nhanh)&quot; bên dưới.</li>
                        <li>Cài PyTorch có CUDA nếu máy có GPU NVIDIA phù hợp.</li>
                        <li>Dùng mode &quot;remote&quot; để kết nối server TTS khác.</li>
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-control text-apple-gray-secondary">Chưa kiểm tra</div>
          )}
        </div>
      </div>

      <div className="card">
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={processingOptions.enable_dub || false}
            onChange={(e) => updateProcessingOptions({ enable_dub: e.target.checked })}
            className="mt-1 w-5 h-5 rounded border-apple-border-soft text-apple-blue focus:ring-apple-blue"
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
          <div className="card">
            <h2 className="text-headline font-sf-display text-apple-ink mb-4">Chế Độ Giọng</h2>

            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="dub_mode"
                  value="preset"
                  checked={processingOptions.dub_mode === 'preset'}
                  onChange={(e) => updateProcessingOptions({ dub_mode: e.target.value })}
                  className="w-4 h-4 text-apple-blue focus:ring-apple-blue"
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
                  className="w-4 h-4 text-apple-blue focus:ring-apple-blue"
                />
                <span className="text-body text-apple-ink">Clone Từ File</span>
              </label>
            </div>
          </div>

          <div className="card">
            <h2 className="text-headline font-sf-display text-apple-ink mb-4">Backend VieNeu</h2>

            <div className="space-y-3">
              <select
                value={processingOptions.dub_backend_mode || 'turbo'}
                onChange={(e) => updateProcessingOptions({ dub_backend_mode: e.target.value })}
                className="input w-full"
              >
                <option value="turbo">turbo (CPU nhanh)</option>
                <option value="turbo_gpu">turbo_gpu (GPU)</option>
                <option value="standard">standard (CPU/GPU)</option>
                <option value="fast">fast (LMDeploy - không hỗ trợ Windows)</option>
                <option value="remote">remote (Server API)</option>
                <option value="xpu">xpu (Intel GPU)</option>
              </select>

              <div className="text-footnote text-apple-gray-secondary">
                turbo = CPU nhanh | turbo_gpu/fast = GPU | remote = server
              </div>
            </div>
          </div>

          {processingOptions.dub_backend_mode === 'remote' && (
            <div className="card">
              <h2 className="text-headline font-sf-display text-apple-ink mb-4">Remote API URL</h2>

              <input
                type="text"
                value={processingOptions.dub_remote_api_base || 'http://localhost:23333/v1'}
                onChange={(e) => updateProcessingOptions({ dub_remote_api_base: e.target.value })}
                className="input w-full"
                placeholder="http://localhost:23333/v1"
              />
            </div>
          )}

          {processingOptions.dub_mode === 'preset' && (
            <div className="card">
              <h2 className="text-headline font-sf-display text-apple-ink mb-4">Giọng Mẫu</h2>

              <div className="space-y-3">
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
                        <option key={voice} value={voice}>
                          {voice}
                        </option>
                      ))
                    )}
                  </select>

                  <button
                    onClick={loadVoices}
                    disabled={loadingVoices}
                    className="btn btn-tertiary rounded-apple-md px-6"
                  >
                    {loadingVoices ? 'Đang Tải...' : 'Tải Danh Sách Giọng'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {processingOptions.dub_mode === 'clone' && (
            <div className="card">
              <h2 className="text-headline font-sf-display text-apple-ink mb-4">Clone Giọng</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-control font-medium text-apple-ink mb-2">
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
                  <label className="block text-control font-medium text-apple-ink mb-2">
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
              </div>
            </div>
          )}

          <div className="card">
            <h2 className="text-headline font-sf-display text-apple-ink mb-4">Trộn Audio</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-control font-medium text-apple-ink mb-2">
                  Âm Lượng Giọng Đọc: {processingOptions.dub_voice_volume || 1.35}
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="3.0"
                  step="0.05"
                  value={processingOptions.dub_voice_volume || 1.35}
                  onChange={(e) => updateProcessingOptions({ dub_voice_volume: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <div className="text-footnote text-apple-gray-secondary mt-1">
                  1.0 = giữ nguyên | tăng nếu giọng đọc còn nhỏ
                </div>
              </div>

              <div>
                <label className="block text-control font-medium text-apple-ink mb-2">
                  Âm Lượng Gốc: {processingOptions.dub_source_volume || 0.18}
                </label>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={processingOptions.dub_source_volume || 0.18}
                  onChange={(e) => updateProcessingOptions({ dub_source_volume: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <div className="text-footnote text-apple-gray-secondary mt-1">
                  0 = tắt tiếng gốc, 0.18 = nền nhỏ phía sau
                </div>
              </div>

              <div>
                <label className="block text-control font-medium text-apple-ink mb-2">
                  Cách Mix Audio
                </label>
                <select
                  value={processingOptions.dub_mix_mode || 'ducking_thong_minh'}
                  onChange={(e) => updateProcessingOptions({ dub_mix_mode: e.target.value })}
                  className="input w-full"
                >
                  <option value="ducking_thong_minh">Ducking Thong Minh (uu tien giọng lồng tiếng)</option>
                  <option value="nen_nho">Nền Nhỏ (giữ nhạc nền nhỏ)</option>
                  <option value="tat_goc">Tắt Gốc (tắt audio gốc)</option>
                </select>
                <div className="text-footnote text-apple-gray-secondary mt-1">
                  Ducking thong minh se ha nho audio goc khi co giọng doc. Nen nho giu nhac nen nhe. Tat goc se tat hoan toan audio goc.
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="text-headline font-sf-display text-apple-ink mb-4">Nghe Thử Giọng</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-control font-medium text-apple-ink mb-2">
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
            </div>
          </div>

          <div className="card notice-info">
            <h3 className="text-body font-semibold text-blue-900 mb-2">Hướng Dẫn Sử Dụng</h3>
            <ul className="text-control text-blue-800 space-y-1 list-disc list-inside">
              <li>Giọng mẫu: dùng nhanh, không cần file mẫu.</li>
              <li>Clone giọng: nên dùng file 3-5 giây, 1 người nói rõ, ít nhạc nền, ít vang.</li>
              <li>Mode VieNeu: turbo=CPU GGUF, turbo_gpu=GPU, standard=CPU/GPU, fast=LMDeploy, remote=server API, xpu=Intel GPU.</li>
              <li>Thời gian xử lý: khoảng 1-2 phút cho video 10 phút.</li>
              <li>Câu ngắn 5-15 từ cho kết quả tốt nhất.</li>
            </ul>
          </div>
        </>
      )}
    </div>
  )
}

export default DubTab
