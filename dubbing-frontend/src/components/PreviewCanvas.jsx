import { useEffect, useRef, useState } from 'react'

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

const wrapPreviewText = (text, maxCharsPerLine) => {
  const normalized = (text || '').trim()
  if (!normalized) return ''
  if (normalized.includes('\n')) return normalized
  if (normalized.length <= maxCharsPerLine) return normalized

  const words = normalized.split(/\s+/)
  const lines = []
  let current = ''

  words.forEach((word) => {
    const candidate = current ? `${current} ${word}` : word
    if (candidate.length <= maxCharsPerLine) {
      current = candidate
    } else {
      if (current) lines.push(current)
      current = word
    }
  })

  if (current) lines.push(current)
  return lines.slice(0, 2).join('\n')
}

const computeSubtitleLayout = ({
  videoHeight,
  subtitleTopY,
  subtitleBottomY,
  fontScale,
  fontSizeOverride,
  marginOffset,
}) => {
  let marginV
  if (subtitleBottomY != null) {
    marginV = Math.min(Math.max(28, videoHeight - subtitleBottomY + 18), Math.floor(videoHeight * 0.22))
  } else if (subtitleTopY == null) {
    marginV = Math.max(28, Math.floor(videoHeight * 0.035))
  } else {
    marginV = Math.min(Math.max(28, videoHeight - subtitleTopY + 14), Math.floor(videoHeight * 0.22))
  }

  marginV = clamp(marginV + marginOffset, 8, Math.floor(videoHeight * 0.45))
  const fontSize = fontSizeOverride > 0
    ? Math.max(10, Math.floor(fontSizeOverride))
    : Math.max(14, Math.floor(videoHeight * 0.03 * Math.max(fontScale, 0.5)))

  return { marginV, fontSize }
}

const expandBandFromCenter = (topY, bottomY, frameHeight, paddingPx, offsetPx = 0) => {
  const centerY = (topY + bottomY) / 2
  const baseHeight = Math.max(2, bottomY - topY + 1)
  const halfHeight = baseHeight / 2 + Math.max(0, paddingPx || 0)
  const shift = clamp(offsetPx || 0, -frameHeight, frameHeight)
  const newTop = clamp(Math.round(centerY - halfHeight - shift), 0, frameHeight - 2)
  const newBottom = clamp(Math.round(centerY + halfHeight - shift), newTop + 1, frameHeight - 1)
  return { topY: newTop, bottomY: newBottom }
}

const PreviewCanvas = ({
  thumbnail,
  previewText,
  coverMode,
  coverStrength,
  subtitleFontScale,
  subtitleFontSize,
  subtitleMargin,
  blurPadding,
  coverOffset,
  maxCharsPerLine,
  previewWidth,
  previewHeight,
  interactive = false,
  onSubtitleDrag,
}) => {
  const canvasRef = useRef(null)
  const dragStateRef = useRef(null)
  const [imageLoaded, setImageLoaded] = useState(false)
  const imgRef = useRef(null)

  useEffect(() => {
    if (!thumbnail) return

    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.src = `/api/preview/thumbnail?url=${encodeURIComponent(thumbnail)}`

    img.onload = () => {
      imgRef.current = img
      setImageLoaded(true)
    }

    img.onerror = () => {
      console.error('Failed to load thumbnail for canvas')
    }
  }, [thumbnail])

  useEffect(() => {
    if (!imageLoaded || !imgRef.current || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const img = imgRef.current

    canvas.width = img.width
    canvas.height = img.height
    ctx.drawImage(img, 0, 0)

    const frameHeight = previewHeight || img.height
    const representativeTopY = Math.floor(frameHeight * 0.82)
    const representativeBottomY = Math.floor(frameHeight * 0.92)
    const coverBand = expandBandFromCenter(
      representativeTopY,
      representativeBottomY,
      frameHeight,
      blurPadding,
      coverOffset
    )

    const coverTop = Math.round((coverBand.topY / frameHeight) * img.height)
    const coverBottom = Math.round((coverBand.bottomY / frameHeight) * img.height)
    const coverHeight = Math.max(2, coverBottom - coverTop + 1)

    const layout = computeSubtitleLayout({
      videoHeight: frameHeight,
      subtitleTopY: representativeTopY,
      subtitleBottomY: representativeBottomY,
      fontScale: subtitleFontScale,
      fontSizeOverride: subtitleFontSize,
      marginOffset: subtitleMargin,
    })

    const subtitleBaselineY = img.height - Math.round((layout.marginV / frameHeight) * img.height)

    if (coverMode === 'blur') {
      const tempCanvas = document.createElement('canvas')
      tempCanvas.width = img.width
      tempCanvas.height = coverHeight
      const tempCtx = tempCanvas.getContext('2d')

      tempCtx.drawImage(
        img,
        0, coverTop,
        img.width, coverHeight,
        0, 0,
        img.width, coverHeight
      )

      tempCtx.filter = `blur(${coverStrength}px)`
      tempCtx.drawImage(tempCanvas, 0, 0)
      ctx.drawImage(tempCanvas, 0, coverTop)
    } else if (coverMode === 'blackbar') {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'
      ctx.fillRect(0, coverTop, img.width, coverHeight)
    }

    const wrappedText = wrapPreviewText(previewText, maxCharsPerLine)
    if (!wrappedText) return

    const lines = wrappedText.split('\n').filter(Boolean)
    const baseFontSize = Math.max(14, Math.round((layout.fontSize / frameHeight) * img.height))
    const lineHeight = baseFontSize * 1.3
    const totalTextHeight = lines.length * lineHeight
    const startY = subtitleBaselineY - totalTextHeight + lineHeight

    ctx.font = `bold ${baseFontSize}px Arial, sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'alphabetic'
    ctx.fillStyle = 'white'
    ctx.strokeStyle = 'black'
    ctx.lineWidth = baseFontSize * 0.15

    lines.forEach((line, index) => {
      const y = startY + index * lineHeight
      ctx.strokeText(line, img.width / 2, y)
      ctx.fillText(line, img.width / 2, y)
    })
  }, [
    imageLoaded,
    previewText,
    coverMode,
    coverStrength,
    subtitleFontScale,
    subtitleFontSize,
    subtitleMargin,
    blurPadding,
    coverOffset,
    maxCharsPerLine,
    previewWidth,
    previewHeight,
  ])

  useEffect(() => {
    if (!interactive || !canvasRef.current || !onSubtitleDrag) return

    const canvas = canvasRef.current

    const handlePointerDown = (event) => {
      const rect = canvas.getBoundingClientRect()
      dragStateRef.current = {
        startY: event.clientY,
        startMargin: subtitleMargin,
        rectHeight: rect.height,
      }
    }

    const handlePointerMove = (event) => {
      if (!dragStateRef.current) return
      const { startY, startMargin, rectHeight } = dragStateRef.current
      const deltaPx = event.clientY - startY
      const frameH = previewHeight || imgRef.current?.height || rectHeight || 1
      const canvasDelta = rectHeight > 0 ? (deltaPx / rectHeight) * frameH : deltaPx
      onSubtitleDrag(Math.round(startMargin - canvasDelta))
    }

    const handlePointerUp = () => {
      dragStateRef.current = null
    }

    canvas.addEventListener('pointerdown', handlePointerDown)
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)

    return () => {
      canvas.removeEventListener('pointerdown', handlePointerDown)
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }
  }, [interactive, onSubtitleDrag, previewHeight, subtitleMargin])

  return (
    <canvas
      ref={canvasRef}
      className={`w-full h-full object-contain ${interactive ? 'cursor-ns-resize' : ''}`}
      style={{ display: imageLoaded ? 'block' : 'none' }}
    />
  )
}

export default PreviewCanvas
