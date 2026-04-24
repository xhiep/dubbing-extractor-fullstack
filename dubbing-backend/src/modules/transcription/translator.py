"""Translation using deep-translator (batch mode)."""
import logging
import time
from typing import Optional, Callable, List, Dict, Any

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

from ...config import config

# Gộp tối đa 50 câu/request — an toàn với Google rate limit
_BATCH_SIZE = 50


def translate(segments: list, log_cb: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
    """Translate text segments to target language using Google Translate.

    Processes segments in batches to optimize API usage and avoid rate limits.
    Preserves original timing information while translating text content.

    Args:
        segments: List of segments with 'text', 'start', and 'end' fields
        log_cb: Optional callback function for logging progress

    Returns:
        List of translated segments, each containing:
            - start: Original start time in seconds
            - end: Original end time in seconds
            - text: Translated text
            - original: Original text before translation

    Raises:
        ConnectionError: If translation API is unreachable
        ValueError: If API returns invalid response
    """
    def _log(m): log_cb and log_cb(m)

    target_lang = config["target_language"]
    total = len(segments)
    _log(f"->  Dich {total} cau (batch {_BATCH_SIZE})...")

    texts = [seg["text"].strip() for seg in segments]
    translated: list[str] = []
    errors = 0

    batches = [texts[i:i + _BATCH_SIZE] for i in range(0, total, _BATCH_SIZE)]
    done = 0
    for batch in batches:
        tr = GoogleTranslator(source="auto", target=target_lang)
        try:
            results = tr.translate_batch(batch)
            # translate_batch có thể trả None cho câu rỗng
            results = [r or batch[j] for j, r in enumerate(results)]
        except (ConnectionError, ValueError, OSError) as e:
            logger.error(f"Translation batch failed: {e}")
            results = list(batch)
            errors += len(batch)
        translated.extend(results)
        done += len(batch)
        if log_cb:
            try:
                log_cb(f"__PROGRESS__{done/total*100:.1f}",
                       f"  Dich [{done}/{total}]")
            except TypeError:
                log_cb(f"  Dich [{done}/{total}]")
        if done < total:
            time.sleep(0.3)  # nghỉ ngắn giữa các batch

    out = []
    for seg, orig, vi in zip(segments, texts, translated):
        out.append({
            "start": seg["start"],
            "end": seg["end"],
            "original": orig,
            "text": vi or orig,
        })

    _log(f"✓  Dich xong ({errors} loi)")
    return out

# ─── CORE: XUẤT FILE ─────────────────────────────────────────────────────────
