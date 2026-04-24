"""URL resolution for short links."""
import logging
import urllib.request
from typing import Optional, Callable

logger = logging.getLogger(__name__)

def resolve_short_douyin_url(url: str, log_cb=None) -> str:
    """
    Follow redirect cho short link Douyin (v.douyin.com/xxxxx/).
    v.douyin.com → có thể redirect về lesdouyin.com (domain quốc tế)
    Hàm này resolve về URL đích thực trước khi normalize.
    """
    def _log(m): log_cb and log_cb(m)
    if "v.douyin.com" not in url.lower():
        return url
    try:
        import urllib.request as _ur
        req = _ur.Request(url, method="HEAD", headers={
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
            )
        })
        with _ur.urlopen(req, timeout=10) as resp:
            resolved = resp.url
            if resolved != url:
                _log(f"-> Resolved short link: {resolved[:80]}")
            return resolved
    except (urllib.error.URLError, OSError) as e:
        logger.warning(f"Could not resolve short link: {e}")
        _log(f"-> Khong the resolve short link ({e}), dung URL goc")
        return url
