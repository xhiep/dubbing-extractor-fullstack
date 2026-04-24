import { FolderOpen, Download, FileVideo, FileAudio, FileText } from 'lucide-react'
import useAppStore from '../store/appStore'

const OutputPanel = () => {
  const { status, outputs, taskId } = useAppStore()

  if (status !== 'completed' || !outputs || Object.keys(outputs).length === 0) {
    return null
  }

  const handleOpenFolder = async () => {
    if (outputs.out_dir) {
      try {
        const response = await fetch('/api/process/open-folder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ folder_path: outputs.out_dir })
        })
        if (!response.ok) {
          console.error('Failed to open folder:', await response.text())
          alert('Không thể mở thư mục. Vui lòng mở thủ công: ' + outputs.out_dir)
        }
      } catch (error) {
        console.error('Error opening folder:', error)
        alert('Không thể mở thư mục. Vui lòng mở thủ công: ' + outputs.out_dir)
      }
    }
  }

  const handleDownloadFile = (filePath) => {
    if (filePath) {
      // Download file via backend
      window.open(`/api/process/download/${encodeURIComponent(filePath)}`, '_blank')
    }
  }

  const getFileIcon = (filename) => {
    if (!filename) return <FileText className="h-5 w-5" />
    if (filename.endsWith('.mp4') || filename.endsWith('.avi')) return <FileVideo className="h-5 w-5" />
    if (filename.endsWith('.mp3') || filename.endsWith('.wav')) return <FileAudio className="h-5 w-5" />
    return <FileText className="h-5 w-5" />
  }

  return (
    <div className="card bg-green-50 border-green-300">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-headline font-sf-display text-green-800">
          ✅ Xử Lý Hoàn Tất
        </h2>
        <button
          onClick={handleOpenFolder}
          className="btn btn-primary flex items-center gap-2"
        >
          <FolderOpen className="h-4 w-4" />
          Mở Thư Mục
        </button>
      </div>

      <div className="space-y-3">
        {/* Output directory */}
        {outputs.out_dir && (
          <div className="p-3 bg-white rounded-apple-md border border-green-200">
            <div className="text-control-sm text-apple-gray-secondary mb-1">
              Thư mục kết quả:
            </div>
            <div className="text-body font-mono text-apple-ink break-all">
              {outputs.out_dir}
            </div>
          </div>
        )}

        {/* Output files */}
        <div className="space-y-2">
          <div className="text-control-sm text-apple-gray-secondary">
            Files đã tạo:
          </div>

          {outputs.video_path && (
            <div className="flex items-center justify-between p-3 bg-white rounded-apple-md border border-green-200">
              <div className="flex items-center gap-3">
                <FileVideo className="h-5 w-5 text-blue-600" />
                <div>
                  <div className="text-body text-apple-ink">Video đã xử lý</div>
                  <div className="text-control-sm text-apple-gray-secondary font-mono">
                    {outputs.video_path.split(/[/\\]/).pop()}
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleDownloadFile(outputs.video_path)}
                className="btn-secondary flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Tải xuống
              </button>
            </div>
          )}

          {outputs.audio_path && (
            <div className="flex items-center justify-between p-3 bg-white rounded-apple-md border border-green-200">
              <div className="flex items-center gap-3">
                <FileAudio className="h-5 w-5 text-purple-600" />
                <div>
                  <div className="text-body text-apple-ink">Audio gốc</div>
                  <div className="text-control-sm text-apple-gray-secondary font-mono">
                    {outputs.audio_path.split(/[/\\]/).pop()}
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleDownloadFile(outputs.audio_path)}
                className="btn-secondary flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Tải xuống
              </button>
            </div>
          )}

          {outputs.srt_path && (
            <div className="flex items-center justify-between p-3 bg-white rounded-apple-md border border-green-200">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-green-600" />
                <div>
                  <div className="text-body text-apple-ink">Phụ đề</div>
                  <div className="text-control-sm text-apple-gray-secondary font-mono">
                    {outputs.srt_path.split(/[/\\]/).pop()}
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleDownloadFile(outputs.srt_path)}
                className="btn-secondary flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Tải xuống
              </button>
            </div>
          )}
        </div>

        {/* Title */}
        {outputs.title && (
          <div className="p-3 bg-white rounded-apple-md border border-green-200">
            <div className="text-control-sm text-apple-gray-secondary mb-1">
              Tiêu đề:
            </div>
            <div className="text-body text-apple-ink">
              {outputs.title}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default OutputPanel
