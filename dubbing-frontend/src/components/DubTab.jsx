import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import useAppStore from '../store/appStore'
import { ttsAPI } from '../api/client'
import { Play, Loader2 } from 'lucide-react'

const DubTab = () => {
  const { processingOptions, updateProcessingOptions } = useAppStore()
  const [testText, setTestText] = useState('Xin chào, đây là bài test giọng đọc')
  const [testVoice, setTestVoice] = useState(processingOptions.tts_voice)
  const [audioUrl, setAudioUrl] = useState(null)

  const { data: voices } = useQuery({
    queryKey: ['tts-voices'],
    queryFn: () => ttsAPI.listVoices(),
  })

  const handleTestVoice = async () => {
    try {
      const result = await ttsAPI.test(testText, testVoice)
      setAudioUrl(result.audio_url)
    } catch (error) {
      console.error('Failed to test voice:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* Enable dubbing */}
      <div className="card">
        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={processingOptions.enable_dubbing}
            onChange={(e) => updateProcessingOptions({ enable_dubbing: e.target.checked })}
            className="w-5 h-5"
          />
          <div>
            <div className="font-medium text-lg">Bật Lồng Tiếng (VieNeu-TTS)</div>
            <div className="text-sm text-dark-300 mt-1">
              Tự động lồng tiếng tiếng Việt vào video
            </div>
          </div>
        </label>
      </div>

      {processingOptions.enable_dubbing && (
        <>
          {/* Voice selection */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">Chọn Giọng Đọc</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  Voice Preset
                </label>
                <select
                  value={processingOptions.tts_voice}
                  onChange={(e) => {
                    updateProcessingOptions({ tts_voice: e.target.value })
                    setTestVoice(e.target.value)
                  }}
                  className="input"
                >
                  {voices?.voices?.map((voice) => (
                    <option key={voice} value={voice}>
                      {voice.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                    </option>
                  )) || (
                    <>
                      <option value="female_north">Female North</option>
                      <option value="female_south">Female South</option>
                      <option value="male_north">Male North</option>
                      <option value="male_south">Male South</option>
                    </>
                  )}
                </select>
              </div>
            </div>
          </div>

          {/* Voice test */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">Test Giọng Đọc</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  Text để test
                </label>
                <textarea
                  value={testText}
                  onChange={(e) => setTestText(e.target.value)}
                  rows={3}
                  maxLength={500}
                  className="input resize-none"
                  placeholder="Nhập text để test giọng đọc..."
                />
                <div className="text-xs text-dark-400 mt-1">
                  {testText.length}/500 ký tự
                </div>
              </div>

              <button
                onClick={handleTestVoice}
                disabled={!testText.trim()}
                className="btn btn-primary"
              >
                <Play className="h-4 w-4 mr-2" />
                Test Voice
              </button>

              {audioUrl && (
                <div className="bg-dark-700 rounded-lg p-4">
                  <audio
                    controls
                    src={audioUrl}
                    className="w-full"
                    autoPlay
                  />
                </div>
              )}
            </div>
          </div>

          {/* TTS info */}
          <div className="card bg-blue-900/20 border-blue-700">
            <h3 className="font-medium text-blue-400 mb-2">ℹ️ Lưu ý về TTS</h3>
            <ul className="text-sm text-dark-300 space-y-1 list-disc list-inside">
              <li>VieNeu-TTS chỉ hỗ trợ tiếng Việt</li>
              <li>Thời gian xử lý: ~1-2 phút cho video 10 phút</li>
              <li>Chất lượng giọng đọc phụ thuộc vào độ dài câu</li>
              <li>Câu ngắn (5-15 từ) cho kết quả tốt nhất</li>
            </ul>
          </div>
        </>
      )}
    </div>
  )
}

export default DubTab
