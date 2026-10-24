"""A date and a time in front of every line that a long run prints (so that a log says when each thing happened and when it went quiet)."""

from __future__ import annotations

import builtins
import time
from typing import Any

_print = builtins.print
_installed = False


def install() -> None:
    """From now on `print` writes `[2026-10-24 15:08:39] ` before its text. Safe to call more than once."""
    global _installed
    if _installed:
        return
    _installed = True

    def stamped(*args: Any, **kwargs: Any) -> None:
        _print(time.strftime("[%Y-%m-%d %H:%M:%S]"), *args, **kwargs)

    builtins.print = stamped
