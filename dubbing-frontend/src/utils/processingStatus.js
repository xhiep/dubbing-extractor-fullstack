export const PROCESSING_STEPS = [
  { num: 1, key: 'prepare', name: 'Chuan bi' },
  { num: 2, key: 'transcribe', name: 'Transcribe' },
  { num: 3, key: 'translate', name: 'Dich' },
  { num: 4, key: 'cover', name: 'Che phu de' },
  { num: 5, key: 'export', name: 'Xuat file' },
  { num: 6, key: 'burn', name: 'Burn subtitle' },
  { num: 7, key: 'dub', name: 'Long tieng' },
]

export const TOTAL_PROCESSING_STEPS = PROCESSING_STEPS.length

export const getStepLabel = (step) =>
  PROCESSING_STEPS.find((item) => item.num === step)?.name || 'Dang xu ly...'

export const getProgressSnapshot = (status, step, progress, message) => {
  if (status === 'queued') {
    return {
      safeStep: Math.max(1, Number(step) || 1),
      safeProgress: Math.max(0, Number(progress) || 0),
      safeMessage: message || 'Dang xep hang xu ly...',
    }
  }

  if (status === 'running') {
    return {
      safeStep: Math.max(1, Number(step) || 1),
      safeProgress: Math.max(0, Number(progress) || 0),
      safeMessage: message || 'Dang xu ly...',
    }
  }

  return {
    safeStep: Math.max(0, Number(step) || 0),
    safeProgress: Math.max(0, Number(progress) || 0),
    safeMessage: message || '',
  }
}
