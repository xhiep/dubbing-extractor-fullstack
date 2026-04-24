"""Platform detection and URL normalization."""
import re
from typing import Literal

PlatformType = Literal["douyin", "bilibili", "youtube", "other"]

def detect_platform(url: str) -> str:
    """Trả về 'douyin' | 'bilibili' | 'youtube' | 'other'."""
    u = url.lower()
    if "douyin.com" in u or "iesdouyin.com" in u or "lesdouyin.com" in u:
        return "douyin"
    if "bilibili.com" in u or "b23.tv" in u:
        return "bilibili"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    return "other"

def normalize_douyin_url(url: str) -> str:
    """
    Chuyển URL Douyin về dạng video chuẩn.
    Hỗ trợ:
      - douyin.com/user/xxx?modal_id=<id>  -> douyin.com/video/<id>
      - lesdouyin.com/share/video/<id>/... -> douyin.com/video/<id>  (domain quốc tế)
    """
    u_lower = url.lower()
    if "douyin.com" not in u_lower and "iesdouyin.com" not in u_lower and "lesdouyin.com" not in u_lower:
        return url

    # lesdouyin.com là domain quốc tế — yt-dlp không hỗ trợ.
    # KHÔNG dùng douyin.com/video/<id> vì từ VN sẽ bị redirect lại lesdouyin.
    # Dùng iesdouyin.com (ByteDance internal share domain) — yt-dlp hỗ trợ trực tiếp.
    import re as _re
    m = _re.search(r'lesdouyin\.com/share/video/(\d+)', url)
    if m:
        video_id = m.group(1)
        return f"https://www.iesdouyin.com/share/video/{video_id}/"

    # Nếu đã là /video/ rồi thì không cần làm gì
    if re.search(r'/video/\d+', url):
        return url

    # Extract modal_id từ query string
    m = re.search(r'[?&]modal_id=(\d+)', url)
    if m:
        video_id = m.group(1)
        return f"https://www.douyin.com/video/{video_id}"
    return url

