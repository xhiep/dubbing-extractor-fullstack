"""yt-dlp wrapper for downloading videos from various platforms."""
import logging
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional, Callable, Tuple

logger = logging.getLogger(__name__)

from .platform_detector import detect_platform
from ..video_processing.ffmpeg_wrapper import LOCAL_FFMPEG

HERE = Path(__file__).parent.parent.parent.parent


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from yt-dlp/ffmpeg errors."""
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def resolve_short_douyin_url(url: str, log_cb=None) -> str:
    """Resolve Douyin short links; keep non-Douyin URLs unchanged."""
    if "douyin.com" not in url and "iesdouyin.com" not in url:
        return url

    def _log(m): log_cb and log_cb(m)

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            final_url = resp.geturl()
            if final_url != url:
                _log("->  Da resolve short URL Douyin")
            return final_url
    except (urllib.error.URLError, OSError) as e:
        logger.debug(f"Could not resolve Douyin short URL: {e}")
        return url


def normalize_douyin_url(url: str) -> str:
    """Normalize common Douyin variants; keep other platforms unchanged."""
    if "douyin.com" not in url and "iesdouyin.com" not in url:
        return url

    modal_match = re.search(r"[?&]modal_id=(\d+)", url)
    if modal_match:
        return f"https://www.douyin.com/video/{modal_match.group(1)}"
    return url

def _build_ydl_headers(platform: str) -> dict:
    if platform == "douyin":
        return {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
            ),
            "Referer": "https://www.douyin.com/",
        }
    elif platform == "bilibili":
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            "Referer":    "https://www.bilibili.com/",
        }
    else:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
        }

def _validate_cookies_file(cookies_file: Path, log_cb=None) -> bool:
    """
    Kiểm tra cookies.txt có chứa domain douyin.com không.
    Trả về False nếu file trống / sai domain.
    """
    def _log(m): log_cb and log_cb(m)
    try:
        content = cookies_file.read_text(encoding="utf-8", errors="ignore")
        lines   = [l for l in content.splitlines() if not l.startswith("#") and l.strip()]
        if not lines:
            _log("⚠  cookies.txt trong — khong co cookie nao!")
            return False
        has_douyin = any("douyin.com" in l or "ttwid" in l or "msToken" in l
                         for l in lines)
        if not has_douyin:
            _log("⚠  cookies.txt khong chua cookie cua douyin.com!")
            _log("   Hay export lai tu tab douyin.com tren Chrome.")
            return False
        _log(f"   cookies.txt hop le ({len(lines)} cookies)")
        return True
    except Exception as e:
        _log(f"⚠  Doc cookies.txt that bai: {e}")
        return False


def _cookies_have_domain(cookies_file: Path, domain_markers: tuple[str, ...]) -> bool:
    """Check whether cookies.txt contains entries for a target domain."""
    try:
        content = cookies_file.read_text(encoding="utf-8", errors="ignore")
    except (OSError, IOError) as e:
        logger.debug(f"Could not read cookies file: {e}")
        return False
    lines = [l for l in content.splitlines() if not l.startswith("#") and l.strip()]
    return any(any(marker in line for marker in domain_markers) for line in lines)


def _bilibili_cookiefile(log_cb=None) -> dict:
    """Return Bilibili cookiefile option when cookies.txt contains Bilibili session."""
    def _log(m): log_cb and log_cb(m)

    cookies_file = HERE / "cookies.txt"
    if not cookies_file.exists():
        return {}
    if _cookies_have_domain(cookies_file, ("SESSDATA", "bili_jct", "DedeUserID")):
        _log("->  Tim thay cookie session Bilibili trong cookies.txt")
        return {"cookiefile": str(cookies_file)}
    if _cookies_have_domain(cookies_file, ("bilibili.com", ".bilibili.com", "buvid3", "b_nut")):
        _log("⚠  cookies.txt co cookie tracking Bilibili nhung thieu cookie session.")
        return {}
    _log("⚠  cookies.txt hien tai khong chua cookie Bilibili.")
    return {}


def _raise_bilibili_cookie_error() -> None:
    raise RuntimeError(
        "Bilibili dang chan request (HTTP 412). Can cookies.txt cua Bilibili.\n\n"
        "CACH SUA:\n"
        "  1. Mo bilibili.com tren Chrome va dang nhap neu can\n"
        "  2. Export cookie tab Bilibili ra file Netscape cookies.txt\n"
        "  3. Ghi de file cookies.txt trong thu muc project\n"
        "  4. Chay lai app\n\n"
        "Luu y: cookies.txt hien tai chi co cookie tracking Bilibili, thieu SESSDATA/bili_jct."
    )


def check_source_preconditions(source: str) -> tuple[bool, str]:
    """Validate whether a source has the minimum prerequisites to start processing."""
    platform = detect_platform(source)
    cookies_file = HERE / "cookies.txt"

    if platform == "youtube":
        return True, "YouTube san sang."

    if platform == "bilibili":
        if not cookies_file.exists():
            return False, (
                "Bilibili can cookies.txt co session.\n"
                "Hay export cookie Bilibili (SESSDATA/bili_jct) vao file cookies.txt."
            )
        if _cookies_have_domain(cookies_file, ("SESSDATA", "bili_jct", "DedeUserID")):
            return True, "Da tim thay cookie session Bilibili."
        if _cookies_have_domain(cookies_file, ("bilibili.com", ".bilibili.com", "buvid3", "b_nut")):
            return False, (
                "cookies.txt dang co cookie tracking Bilibili nhung thieu session.\n"
                "Can export lai cookie co SESSDATA/bili_jct."
            )
        return False, "cookies.txt hien tai khong chua cookie Bilibili."

    if platform == "douyin":
        if not cookies_file.exists():
            return False, "Douyin can cookies.txt. Hay export cookie tu douyin.com."
        if _cookies_have_domain(cookies_file, ("douyin.com", ".douyin.com", "ttwid", "msToken", "sessionid")):
            return True, "Da tim thay cookie Douyin."
        return False, "cookies.txt hien tai khong chua cookie Douyin hop le."

    return True, "Nguon URL hop le."


def fetch_preview_info(source: str) -> dict:
    """Fetch lightweight preview metadata for a remote source."""
    import yt_dlp

    platform = detect_platform(source)
    headers = _build_ydl_headers(platform)
    extra_opts = _build_extra_ydl_opts(platform)

    with yt_dlp.YoutubeDL({
        "quiet": True,
        "no_warnings": True,
        "http_headers": headers,
        **extra_opts,
    }) as ydl:
        info = ydl.extract_info(source, download=False)

    return {
        "title": info.get("title", "video"),
        "duration": info.get("duration", 0),
        "thumbnail": info.get("thumbnail"),
        "uploader": info.get("uploader") or info.get("channel") or "",
        "view_count": info.get("view_count") or 0,
        "webpage_url": info.get("webpage_url") or source,
    }

def _resolve_douyin_cookies(log_cb=None) -> dict:
    """
    Chrome 127+ dùng App-Bound Encryption → cookiesfrombrowser sẽ fail DPAPI.
    Giải pháp duy nhất ổn định: dùng cookies.txt export từ browser extension.
    """
    def _log(m): log_cb and log_cb(m)

    cookies_file = HERE / "cookies.txt"
    if cookies_file.exists():
        _log("✓  Tim thay cookies.txt — su dung de tai Douyin")
        _validate_cookies_file(cookies_file, log_cb)   # cảnh báo nếu sai
        return {"cookiefile": str(cookies_file)}

    # Không có cookies.txt → báo rõ hướng dẫn, không thử DPAPI (sẽ fail)
    _log("⚠  Chua co cookies.txt — Douyin can cookies de tai video.")
    _log("   HUONG DAN lay cookies (1 lan duy nhat):")
    _log("   1. Cai extension tren Chrome:")
    _log("      https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
    _log("   2. Mo douyin.com tren Chrome (dang nhap hoac khong deu duoc)")
    _log("   3. Click extension → Export → luu file la 'cookies.txt'")
    _log("   4. Dan file cookies.txt vao cung thu muc voi main.py")
    _log("   5. Chay lai app nay")
    raise RuntimeError(
        "Douyin yeu cau cookies.txt.\n"
        "Xem huong dan trong LOG de biet cach tao file nay."
    )

def _auto_update_ytdlp(log_cb=None):
    """
    Tự động update yt-dlp lên version mới nhất.
    Douyin extractor thay đổi thường xuyên — version cũ dễ bị block.
    """
    def _log(m): log_cb and log_cb(m)
    try:
        _log("->  Cap nhat yt-dlp len version moi nhat...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "-q"],
            capture_output=True, text=True, timeout=90,
        )
        if result.returncode == 0:
            # Lấy version sau update
            import yt_dlp
            ver = getattr(yt_dlp, "__version__", "?")
            _log(f"✓  yt-dlp {ver} san sang")
        else:
            _log(f"⚠  Khong the cap nhat yt-dlp (se thu voi version hien tai)")
    except Exception as e:
        _log(f"⚠  Loi khi cap nhat yt-dlp: {e}")


_FRESH_COOKIES_MSGS = (
    "fresh cookies",
    "Fresh cookies",
    "cookies (not necessarily logged in) are needed",
)

def _is_fresh_cookies_error(err_str: str) -> bool:
    return any(m in err_str for m in _FRESH_COOKIES_MSGS)


def _is_bilibili_412_error(err_str: str) -> bool:
    return "BiliBili" in err_str and "HTTP Error 412" in err_str

def _build_extra_ydl_opts(platform: str, log_cb=None) -> dict:
    if platform == "douyin":
        opts = {
            "extractor_args": {"douyin": {"download_video_params": ["pq=0&dr=0"]}},
            "nocheckcertificate": True,
        }
        opts.update(_resolve_douyin_cookies(log_cb))
        return opts
    if platform == "bilibili":
        return _bilibili_cookiefile(log_cb)
    return {}

# ─── FFMPEG HELPERS ───────────────────────────────────────────────────────────

def download(url: str, work_dir: Path, log_cb: Optional[Callable[[str], None]] = None) -> Tuple[Path, Path, str]:
    """Download video and audio from URL using yt-dlp.

    Supports multiple platforms (YouTube, Bilibili, Douyin) with platform-specific
    optimizations. Automatically handles cookies, headers, and format selection.

    Args:
        url: Video URL (YouTube, Bilibili, Douyin, etc.)
        work_dir: Working directory for downloaded files
        log_cb: Optional callback function for logging progress

    Returns:
        Tuple containing:
            - video_path: Path to downloaded video file (MP4)
            - audio_path: Path to extracted audio file (MP3)
            - title: Video title

    Raises:
        RuntimeError: If download fails or requires cookies
        FileNotFoundError: If downloaded files are missing
    """
    import yt_dlp

    def _log(m): log_cb and log_cb(m)

    orig_url   = url
    # Bước 1: resolve short link (v.douyin.com → URL thực, có thể là lesdouyin.com)
    url        = resolve_short_douyin_url(url, log_cb)
    # Bước 2: normalize URL (lesdouyin.com / modal_id → douyin.com/video/<id>)
    url        = normalize_douyin_url(url)
    if url != orig_url:
        _log(f"-> Douyin: chuyen ve URL video chuan")
        _log(f"   {url}")
    platform   = detect_platform(url)
    headers    = _build_ydl_headers(platform)
    extra_opts = _build_extra_ydl_opts(platform, log_cb)
    ff_loc     = str(LOCAL_FFMPEG.parent) if LOCAL_FFMPEG.exists() else None

    platform_label = {"douyin": "Douyin", "bilibili": "Bilibili",
                      "youtube": "YouTube"}.get(platform, "")
    if platform_label:
        _log(f"-> Phat hien {platform_label}...")

    # Douyin extractor thay đổi liên tục → auto-update yt-dlp trước
    if platform == "douyin":
        _auto_update_ytdlp(log_cb)
        import importlib
        import yt_dlp as _ydl_reload
        importlib.reload(_ydl_reload)
        import yt_dlp

    _log("->  Dang lay thong tin video...")
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                                "http_headers": headers, **extra_opts}) as ydl:
            meta  = ydl.extract_info(url, download=False)
            title = meta.get("title", "video")
            dur   = meta.get("duration", 0)
            _log(f"   {title[:60]}")
            _log(f"   {int(dur//60)}:{int(dur%60):02d}  |  {meta.get('view_count',0):,} luot xem")
    except Exception as exc:
        clean = strip_ansi(str(exc))
        if platform == "bilibili" and _is_bilibili_412_error(clean):
            _raise_bilibili_cookie_error()
        if _is_fresh_cookies_error(clean):
            raise RuntimeError(
                "Douyin bao loi: cookies.txt bi het han hoac khong hop le!\n\n"
                "CACH SUA:\n"
                "  1. Mo Chrome → vao douyin.com → doi trang tai xong hoan toan\n"
                "  2. Click extension 'Get cookies.txt LOCALLY' → Export\n"
                "     Luu de ghi de len file cookies.txt cu (cung thu muc main.py)\n"
                "  3. Chay lai app\n\n"
                "Neu van loi: xoa cookies.txt → export lai tu dau."
            ) from None
        raise RuntimeError(clean) from None

    video_path = work_dir / "raw_video.mp4"
    _log("->  Tai VIDEO chat luong cao nhat...")

    def _hook(d):
        if d["status"] == "downloading":
            done  = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 1)
            speed = (d.get("speed") or 0) / 1024 / 1024
            pct   = min(done / total * 100, 100) if total else 0
            if log_cb:
                try:
                    log_cb(
                        f"__PROGRESS__{pct:.1f}",
                        f"  [{int(done/1024/1024)}MB / {int(total/1024/1024)}MB]  {speed:.1f} MB/s"
                    )
                except TypeError:
                    log_cb(f"  [{int(done/1024/1024)}MB / {int(total/1024/1024)}MB]  {speed:.1f} MB/s")
        elif d["status"] == "finished":
            if log_cb:
                try:
                    log_cb("__PROGRESS__100.0")
                except TypeError:
                    pass

    try:
        with yt_dlp.YoutubeDL({
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(video_path),
            "merge_output_format": "mp4",
            "progress_hooks": [_hook],
            "quiet": True, "no_warnings": True,
            "http_headers": headers,
            "retries": 5,
            "ffmpeg_location": ff_loc,
            **extra_opts,
        }) as ydl:
            ydl.download([url])
    except Exception as exc:
        clean = strip_ansi(str(exc))
        if platform == "bilibili" and _is_bilibili_412_error(clean):
            _raise_bilibili_cookie_error()
        if _is_fresh_cookies_error(clean):
            raise RuntimeError(
                "Douyin bao loi: cookies.txt bi het han hoac khong hop le!\n\n"
                "CACH SUA:\n"
                "  1. Mo Chrome → vao douyin.com → doi trang tai xong hoan toan\n"
                "  2. Click extension 'Get cookies.txt LOCALLY' → Export\n"
                "     Luu de ghi de len file cookies.txt cu (cung thu muc main.py)\n"
                "  3. Chay lai app\n\n"
                "Neu van loi: xoa cookies.txt → export lai tu dau."
            ) from None
        raise RuntimeError(clean) from None

    if not video_path.exists():
        candidates = sorted(work_dir.glob("raw_video*"))
        if candidates:
            video_path = candidates[0]
        else:
            raise FileNotFoundError("Khong tim thay file video sau khi tai!")
    _log(f"✓  Video: {video_path.stat().st_size/1024/1024:.1f} MB")

    _log("->  Xuat AUDIO goc (mp3)...")
    with yt_dlp.YoutubeDL({
        "format": "bestaudio/best",
        "outtmpl": str(work_dir / "audio_raw.%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3", "preferredquality": "192"}],
        "progress_hooks": [_hook],
        "quiet": True, "no_warnings": True,
        "http_headers": headers,
        "ffmpeg_location": ff_loc,
        **extra_opts,
    }) as ydl:
        ydl.download([url])

    audio_path = work_dir / "audio_goc.mp3"
    for f in work_dir.glob("audio_raw*"):
        f.replace(audio_path)
        break

    _log(f"✓  Audio: {audio_path.stat().st_size/1024/1024:.1f} MB")
    return video_path, audio_path, title

# ─── CORE: CHE PHỤ ĐỀ GỐC ────────────────────────────────────────────────────

