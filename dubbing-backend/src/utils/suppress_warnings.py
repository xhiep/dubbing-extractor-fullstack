import sys
import io
import re

class SuppressOrtWarnings(io.TextIOBase):
    def __init__(self, original_stream):
        super().__init__()
        self.original_stream = original_stream

    def write(self, s):
        # The logging often spans multiple writes. If the string contains ONLY formatting codes
        # or parts of the error, we suppress it completely.

        # Clean string to ignore ANSI coloring characters
        clean_s = re.sub(r'\x1b\[[0-9;]*m', '', s)

        suppressed_keywords = [
            "onnxruntime", "TryGetProviderInfo_CUDA", "CUDAExecutionProvider",
            "cublasLt64", "Redirects are currently not supported", "torch_dtype",
            "Skipping import of cpp extensions", "provider_bridge_ort", "pybind_state",
            "HF_TOKEN"
        ]

        for k in suppressed_keywords:
            if k in clean_s:
                return len(s)

        # Catch parts of the multiline error that might not contain the exact keywords on their line
        if "which depends on" in clean_s or "(Error 126:" in clean_s or "and the latest MSVC runtime" in clean_s or "Requirements" in clean_s or "https://onnxruntime" in clean_s:
            return len(s)

        # Catch isolated color codes and newlines that ONNX prints
        if not clean_s.strip():
            # If the string is purely whitespace/newlines or ANSI codes, we still check
            # if it's likely a byproduct of the suppressed warning.
            return len(s)

        # Fallback keyword checks
        if "onnx" in clean_s.lower() or "Failed to create" in clean_s or "onnxruntime::" in clean_s or "Error 126" in clean_s or "Require cuDNN" in clean_s or "cublas" in clean_s.lower():
            return len(s)

        if "[E:onnxruntime" in clean_s or "[W:onnxruntime" in clean_s or "Error loading" in clean_s:
             return len(s)

        return self.original_stream.write(s)

    def flush(self):
        self.original_stream.flush()

def install_stderr_filter():
    import warnings
    warnings.filterwarnings("ignore")

    import os
    os.environ["ORT_CPP_LOG_LEVEL"] = "4"  # FATAL
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" # FATAL

    sys.stderr = SuppressOrtWarnings(sys.stderr)
    sys.stdout = SuppressOrtWarnings(sys.stdout)
