"""Project-local runtime environment helpers."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_runtime_dirs() -> dict[str, Path]:
    cache_root = PROJECT_ROOT / ".cache"
    tmp_root = PROJECT_ROOT / ".tmp"
    return {
        "project": PROJECT_ROOT,
        "cache_root": cache_root,
        "tmp_root": tmp_root,
        "hf_home": cache_root / "huggingface",
        "hf_hub": cache_root / "huggingface" / "hub",
        "transformers": cache_root / "huggingface" / "transformers",
        "torch": cache_root / "torch",
        "pip": cache_root / "pip",
        "uv": cache_root / "uv",
        "tts": cache_root / "vieneu",
        "preview": PROJECT_ROOT / "output" / "_preview_cache",
    }


def ensure_local_runtime_env() -> dict[str, Path]:
    dirs = get_runtime_dirs()
    for path in dirs.values():
        if isinstance(path, Path) and path.suffix == "":
            path.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("XDG_CACHE_HOME", str(dirs["cache_root"]))
    os.environ.setdefault("HF_HOME", str(dirs["hf_home"]))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(dirs["hf_hub"]))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(dirs["transformers"]))
    os.environ.setdefault("TORCH_HOME", str(dirs["torch"]))
    os.environ.setdefault("PIP_CACHE_DIR", str(dirs["pip"]))
    os.environ.setdefault("UV_CACHE_DIR", str(dirs["uv"]))
    os.environ.setdefault("TEMP", str(dirs["tmp_root"]))
    os.environ.setdefault("TMP", str(dirs["tmp_root"]))
    os.environ.setdefault("TMPDIR", str(dirs["tmp_root"]))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    # Fix for LMDeploy and llama-cpp-python failing on Windows due to missing CUDA_PATH
    if os.name == "nt" and "CUDA_PATH" not in os.environ:
        try:
            import torch
            torch_lib = Path(torch.__file__).parent / "lib"
            if torch_lib.exists():
                # LMDeploy checks for os.path.join(CUDA_PATH, 'bin')
                # llama-cpp-python checks for os.path.join(CUDA_PATH, 'lib')
                dummy_cuda = dirs["cache_root"] / "dummy_cuda"
                (dummy_cuda / "bin").mkdir(parents=True, exist_ok=True)
                (dummy_cuda / "lib").mkdir(parents=True, exist_ok=True)
                os.environ["CUDA_PATH"] = str(dummy_cuda)
        except Exception:
            pass

    return dirs
