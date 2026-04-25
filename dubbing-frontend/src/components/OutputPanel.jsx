import { FolderOpen, Download, FileVideo, FileAudio, FileText } from 'lucide-react'
import useAppStore from '../store/appStore'

const OutputPanel = () => {
  const { status, outputs } = useAppStore()

  if (status !== 'completed' || !outputs || Object.keys(outputs).length === 0) {
    return null
  }

  const handleOpenFolder = async () => {
    if (!outputs.out_dir) return

    try {
      const response = await fetch('/api/process/open-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_path: outputs.out_dir }),
      })

      if (!response.ok) {
        console.error('Failed to open folder:', await response.text())
        alert(`Không thể mở thư mục. Vui lòng mở thủ công: ${outputs.out_dir}`)
      }
    } catch (error) {
      console.error('Error opening folder:', error)
      alert(`Không thể mở thư mục. Vui lòng mở thủ công: ${outputs.out_dir}`)
    }
  }

  const handleDownloadFile = (filePath) => {
    if (filePath) {
      window.open(`/api/process/download/${encodeURIComponent(filePath)}`, '_blank')
    }
  }

  const getFilename = (filePath) => filePath?.split(/[/\\]/).pop() || ''

  const fileItems = [
    {
      key: 'video',
      label: 'Video đã xử lý',
      path: outputs.video_path,
      icon: <FileVideo className="h-5 w-5 text-blue-600" />,
    },
    {
      key: 'audio',
      label: 'Audio gốc',
      path: outputs.audio_path,
      icon: <FileAudio className="h-5 w-5 text-blue-600" />,
    },
    {
      key: 'subtitle',
      label: 'Phụ đề',
      path: outputs.srt_path,
      icon: <FileText className="h-5 w-5 text-blue-600" />,
    },
  ].filter((item) => item.path)

  return (
    <div className="card output-panel mt-8">
      <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-utility font-sf-display text-green-800">
            Xử Lý Hoàn Tất
          </h2>
          <p className="mt-1 text-control text-apple-gray-secondary">
            Tất cả artifact đã sẵn sàng để mở hoặc tải xuống.
          </p>
        </div>

        <button
          onClick={handleOpenFolder}
          className="btn btn-primary btn-pill"
        >
          <FolderOpen className="h-4 w-4" />
          Mở Thư Mục
        </button>
      </div>

      <div className="space-y-3">
        {outputs.out_dir && (
          <div className="output-panel-row rounded-apple-lg p-4">
            <div className="text-control text-apple-gray-secondary mb-1">
              Thư mục kết quả
            </div>
            <div className="text-body font-mono text-apple-ink break-all">
              {outputs.out_dir}
            </div>
          </div>
        )}

        {fileItems.length > 0 && (
          <div className="space-y-3">
            <div className="text-control text-apple-gray-secondary">Files đã tạo</div>
            {fileItems.map((item) => (
              <div
                key={item.key}
                className="output-panel-row flex flex-col gap-3 rounded-apple-lg p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-center gap-3">
                  {item.icon}
                  <div>
                    <div className="text-body text-apple-ink">{item.label}</div>
                    <div className="text-control text-apple-gray-secondary font-mono break-all">
                      {getFilename(item.path)}
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleDownloadFile(item.path)}
                  className="btn btn-tertiary btn-pill"
                >
                  <Download className="h-4 w-4" />
                  Tải xuống
                </button>
              </div>
            ))}
          </div>
        )}

        {outputs.title && (
          <div className="output-panel-row rounded-apple-lg p-4">
            <div className="text-control text-apple-gray-secondary mb-1">
              Tiêu đề
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
