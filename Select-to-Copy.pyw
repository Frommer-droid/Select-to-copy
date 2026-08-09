from __future__ import annotations

import sys
import warnings

if sys.platform == "win32":
    # pywinauto/comtypes должны использовать STA, чтобы не конфликтовать с Qt OleInitialize.
    sys.coinit_flags = 2
    warnings.filterwarnings(
        "ignore",
        message=r"Apply externally defined coinit_flags: 2",
        category=UserWarning,
        module=r"pywinauto",
    )

from app.main import run


if __name__ == "__main__":
    raise SystemExit(run())
