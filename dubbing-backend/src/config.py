"""Configuration management for Dubbing Extractor."""
import os
import json
from pathlib import Path
from typing import Optional
from .utils.runtime_env import ensure_local_runtime_env

HERE = Path(__file__).parent.parent
CONFIG_FILE = HERE / "config.json"
ENV_FILE = HERE / ".env"
RUNTIME_DIRS = ensure_local_runtime_env()

# Default configuration
DEFAULTS = {
    "whisper_model": "base",
    "source_language": None,
    "target_language": "vi",
    "output_base_dir": "output",
    "video_speed": 1.0,
    "srt_max_chars_per_line": 45,
    "blur_padding_px": 12,
    "cover_offset_px": 0,
    "blur_power": 4,
    "ffmpeg_path": "",
    "ffprobe_path": "",
    "cookies_file": "cookies.txt",
    "debug": False,
    "enable_dub": False,
    "dub_mode": "preset",
    "dub_backend_mode": "turbo",
    "dub_remote_api_base": "http://localhost:23333/v1",
    "dub_preset_voice": "",
    "dub_ref_audio": "",
    "dub_ref_text": "",
    "dub_voice_volume": 1.35,
    "dub_source_volume": 0.18,
    "dub_mix_mode": "nen_nho",
    "tts_preview_text": "Xin chao, day la mau thu giong tieng Viet de kiem tra long tieng.",
}

# App-specific config (GUI state)
APP_CONFIG_DEFAULTS = {
    "source_input": "",
    "cover_mode": "blur",
    "whisper_model": "base",
    "burn_sub": False,
    "subtitle_offset_sec": 0.0,
    "subtitle_timing_scale": 1.0,
    "video_speed": 1.0,
    "subtitle_font_scale": 1.0,
    "subtitle_font_size": 0,
    "subtitle_margin_px": 0,
    "srt_max_chars_per_line": 45,
    "blur_padding_px": 12,
    "cover_offset_px": 0,
    "blur_power": 4,
    "subtitle_preset": "Custom",
    "preview_text": "Xem trước phụ đề dòng 1\nDòng 2 sau khi xuống dòng theo cài đặt hiện tại",
    "last_render_dir": "",
    "enable_dub": False,
    "dub_mode": "preset",
    "dub_backend_mode": "turbo",
    "dub_remote_api_base": "http://localhost:23333/v1",
    "dub_preset_voice": "",
    "dub_ref_audio": "",
    "dub_ref_text": "Day la mau giong de clone.",
    "dub_voice_volume": 1.35,
    "dub_source_volume": 0.18,
    "dub_mix_mode": "nen_nho",
    "tts_preview_text": "Xin chao, day la mau thu giong tieng Viet de kiem tra long tieng.",
}

class Config:
    """Configuration singleton."""
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_env(self):
        """Load .env file if exists."""
        if ENV_FILE.exists():
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
    
    def _load_config(self):
        """Load configuration from .env and config.json."""
        self._load_env()
        
        # Start with defaults
        self._config = DEFAULTS.copy()
        
        # Override with environment variables
        if os.getenv("WHISPER_MODEL"):
            self._config["whisper_model"] = os.getenv("WHISPER_MODEL")
        if os.getenv("SOURCE_LANGUAGE"):
            self._config["source_language"] = os.getenv("SOURCE_LANGUAGE")
        if os.getenv("TARGET_LANGUAGE"):
            self._config["target_language"] = os.getenv("TARGET_LANGUAGE")
        if os.getenv("OUTPUT_DIR"):
            self._config["output_base_dir"] = os.getenv("OUTPUT_DIR")
        if os.getenv("VIDEO_SPEED"):
            try:
                self._config["video_speed"] = float(os.getenv("VIDEO_SPEED"))
            except Exception:
                pass
        if os.getenv("FFMPEG_PATH"):
            self._config["ffmpeg_path"] = os.getenv("FFMPEG_PATH")
        if os.getenv("FFPROBE_PATH"):
            self._config["ffprobe_path"] = os.getenv("FFPROBE_PATH")
        if os.getenv("BLUR_PADDING_PX"):
            try:
                self._config["blur_padding_px"] = int(os.getenv("BLUR_PADDING_PX"))
            except Exception:
                pass
        if os.getenv("BLUR_POWER"):
            try:
                self._config["blur_power"] = int(os.getenv("BLUR_POWER"))
            except Exception:
                pass
        if os.getenv("COVER_OFFSET_PX"):
            try:
                self._config["cover_offset_px"] = int(os.getenv("COVER_OFFSET_PX"))
            except Exception:
                pass
        if os.getenv("COOKIES_FILE"):
            self._config["cookies_file"] = os.getenv("COOKIES_FILE")
        if os.getenv("DEBUG", "").lower() in ("true", "1", "yes"):
            self._config["debug"] = True
        if os.getenv("ENABLE_DUB", "").lower() in ("true", "1", "yes"):
            self._config["enable_dub"] = True
        if os.getenv("DUB_MODE"):
            self._config["dub_mode"] = os.getenv("DUB_MODE")
        if os.getenv("DUB_BACKEND_MODE"):
            self._config["dub_backend_mode"] = os.getenv("DUB_BACKEND_MODE")
        if os.getenv("DUB_REMOTE_API_BASE"):
            self._config["dub_remote_api_base"] = os.getenv("DUB_REMOTE_API_BASE")
        if os.getenv("DUB_PRESET_VOICE"):
            self._config["dub_preset_voice"] = os.getenv("DUB_PRESET_VOICE")
        if os.getenv("DUB_REF_AUDIO"):
            self._config["dub_ref_audio"] = os.getenv("DUB_REF_AUDIO")
        if os.getenv("DUB_REF_TEXT"):
            self._config["dub_ref_text"] = os.getenv("DUB_REF_TEXT")
        if os.getenv("DUB_VOICE_VOLUME"):
            try:
                self._config["dub_voice_volume"] = float(os.getenv("DUB_VOICE_VOLUME"))
            except Exception:
                pass
        if os.getenv("DUB_SOURCE_VOLUME"):
            try:
                self._config["dub_source_volume"] = float(os.getenv("DUB_SOURCE_VOLUME"))
            except Exception:
                pass
        if os.getenv("DUB_MIX_MODE"):
            self._config["dub_mix_mode"] = os.getenv("DUB_MIX_MODE")
        if os.getenv("TTS_PREVIEW_TEXT"):
            self._config["tts_preview_text"] = os.getenv("TTS_PREVIEW_TEXT")
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value (runtime only)."""
        self._config[key] = value
    
    def __getitem__(self, key: str):
        return self._config[key]
    
    def __setitem__(self, key: str, value):
        self._config[key] = value

def load_app_config() -> dict:
    """Load app-specific config from config.json."""
    if not CONFIG_FILE.exists():
        return APP_CONFIG_DEFAULTS.copy()
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Sanitize and merge with defaults
        result = APP_CONFIG_DEFAULTS.copy()
        for key in APP_CONFIG_DEFAULTS:
            if key in data:
                result[key] = data[key]
        
        return result
    except Exception:
        return APP_CONFIG_DEFAULTS.copy()

def save_app_config(data: dict) -> dict:
    """Save app-specific config to config.json."""
    current = load_app_config()
    if data:
        current.update(data)
    
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    
    return current

# Global config instance
config = Config()
