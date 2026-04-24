"""SRT subtitle file generation."""
from pathlib import Path
from typing import List, Dict

from ...utils.text_utils import srt_time

def parse_srt(srt_path: Path) -> List[Dict]:
    """Parse an SRT subtitle file into timed segments.

    Reads SRT format and extracts timing and text information for each subtitle.

    Args:
        srt_path: Path to SRT subtitle file

    Returns:
        List of subtitle segments, each containing:
            - start: Start time in seconds
            - end: End time in seconds
            - text: Subtitle text (may contain multiple lines)

    Raises:
        FileNotFoundError: If SRT file does not exist
    """
    if not srt_path.exists():
        return []

    def _parse_time(value: str) -> float:
        hh, mm, rest = value.strip().split(":")
        ss, ms = rest.split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000

    content = srt_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not content:
        return []

    segments: List[Dict] = []
    blocks = [block.strip() for block in content.split("\n\n") if block.strip()]
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_text, end_text = [part.strip() for part in lines[1].split("-->")]
        segments.append({
            "start": _parse_time(start_text),
            "end": _parse_time(end_text),
            "text": "\n".join(lines[2:]),
        })
    return segments

def write_srt(segments: List[Dict], output_path: Path, max_chars_per_line: int = 45) -> None:
    """Write subtitle segments to SRT file format.

    Formats segments into standard SRT format with automatic line wrapping
    for long text. Each subtitle is numbered sequentially.

    Args:
        segments: List of segments with 'start', 'end', and 'text' fields
        output_path: Path where SRT file will be written
        max_chars_per_line: Maximum characters per line before wrapping

    Raises:
        IOError: If file cannot be written
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start = srt_time(seg["start"])
            end = srt_time(seg["end"])
            text = seg["text"].strip()
            
            # Split long lines
            if len(text) > max_chars_per_line:
                words = text.split()
                lines = []
                current_line = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) + 1 <= max_chars_per_line:
                        current_line.append(word)
                        current_length += len(word) + 1
                    else:
                        if current_line:
                            lines.append(" ".join(current_line))
                        current_line = [word]
                        current_length = len(word)
                
                if current_line:
                    lines.append(" ".join(current_line))
                
                text = "\n".join(lines)
            
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")
