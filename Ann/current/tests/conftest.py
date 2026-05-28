import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_qtimer_singleshot():
    # Determine which Qt library is in use and patch QTimer.singleShot to run synchronously
    patched = False
    patcher = None
    try:
        from PyQt6.QtCore import QTimer
        # Use patch.object to redirect singleShot to run the callback synchronously
        patcher = patch.object(QTimer, "singleShot", side_effect=lambda delay, callback: callback() if callable(callback) else None)
        patcher.start()
        patched = True
    except ImportError:
        pass

    if not patched:
        try:
            from PySide6.QtCore import QTimer
            # Do the same for PySide6 if PyQt6 is not in use
            patcher = patch.object(QTimer, "singleShot", side_effect=lambda delay, callback: callback() if callable(callback) else None)
            patcher.start()
            patched = True
        except ImportError:
            pass

    yield

    if patched and patcher:
        try:
            patcher.stop()
        except Exception:
            pass
