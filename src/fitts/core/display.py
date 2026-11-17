"""Render directly at native pixels instead of Windows bitmap DPI scaling."""

import os
import sys


def enable_native_dpi() -> None:
    """Set process DPI awareness before SDL creates its first window."""
    if sys.platform != "win32":
        return
    os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
    try:
        import ctypes
        # -4 is DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2. A false return
        # commonly means awareness was already set by the application host.
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        # Older Windows/SDL versions can use the SDL hint above.
        pass
