"""TUI encoding utilities for Windows compatibility."""
import sys


def ensure_utf8_streams():
    """Ensure stdout/stderr use UTF-8 encoding for proper Chinese character display.

    This is critical for Windows where the default console encoding might be GBK,
    causing UnicodeEncodeError when printing Chinese characters.
    """
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
