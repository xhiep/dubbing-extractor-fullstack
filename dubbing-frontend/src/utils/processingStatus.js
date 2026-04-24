export const PROCESSING_STEPS = [
  { num: 1, key: 'prepare', name: 'Chuẩn bị' },
  { num: 2, key: 'transcribe', name: 'Transcribe' },
  { num: 3, key: 'translate', name: 'Dịch' },
  { num: 4, key: 'cover', name: 'Che phụ đề' },
  { num: 5, key: 'export', name: 'Xuất file' },
  { num: 6, key: 'burn', name: 'Burn subtitle' },
  { num: 7, key: 'dub', name: 'Lồng tiếng' },
]

export const TOTAL_PROCESSING_STEPS = PROCESSING_STEPS.length

export const getStepLabel = (step) =>
  PROCESSING_STEPS.find((item) => item.num === step)?.name || 'Đang xử lý...'

const STEP_MESSAGE_MAP = {
  'Preparing source...': 'Đang chuẩn bị nguồn video...',
  'Step 1 completed': 'Bước 1 đã hoàn tất.',
  'Transcribing audio...': 'Đang nhận dạng giọng nói...',
  'Step 2 completed': 'Bước 2 đã hoàn tất.',
  'Translating subtitle...': 'Đang dịch phụ đề...',
  'Step 3 completed': 'Bước 3 đã hoàn tất.',
  'Covering original subtitle...': 'Đang che phụ đề gốc...',
  'Step 4 completed': 'Bước 4 đã hoàn tất.',
  'Exporting files...': 'Đang xuất file...',
  'Step 5 completed': 'Bước 5 đã hoàn tất.',
  'Burning subtitle into video...': 'Đang ghi phụ đề vào video...',
  'Step 6 completed': 'Bước 6 đã hoàn tất.',
  'Generating dub...': 'Đang tạo lồng tiếng...',
  'Step 7 completed': 'Bước 7 đã hoàn tất.',
  'Burn subtitle disabled, skipped': 'Đã bỏ qua bước burn subtitle.',
  'Dub disabled, skipped': 'Đã bỏ qua bước lồng tiếng.',
  'Processing started': 'Đã bắt đầu xử lý.',
}

export const normalizeProcessingMessage = (message) => {
  const raw = (message || '').trim()
  if (!raw) return ''
  if (STEP_MESSAGE_MAP[raw]) return STEP_MESSAGE_MAP[raw]

  const startedMatch = raw.match(/^Step\s+(\d+)\s+started$/i)
  if (startedMatch) {
    return `Đã bắt đầu bước ${startedMatch[1]}.`
  }

  return raw
}

export const getProgressSnapshot = (status, step, progress, message) => {
  const normalizedMessage = normalizeProcessingMessage(message)

  if (status === 'queued') {
    return {
      safeStep: Math.max(1, Number(step) || 1),
      safeProgress: Math.max(0, Number(progress) || 0),
      safeMessage: normalizedMessage || 'Đang xếp hàng xử lý...',
    }
  }

  if (status === 'running') {
    return {
      safeStep: Math.max(1, Number(step) || 1),
      safeProgress: Math.max(0, Number(progress) || 0),
      safeMessage: normalizedMessage || 'Đang xử lý...',
    }
  }

  return {
    safeStep: Math.max(0, Number(step) || 0),
    safeProgress: Math.max(0, Number(progress) || 0),
    safeMessage: normalizedMessage || '',
  }
}
