"""Crash-safe JSON persistence for the 2.1 test application's local settings.

All writes create a temporary sibling, flush the complete JSON document,
then atomically replace the previous version. A process crash during the
temporary write cannot truncate an existing preferences or profile file.
"""

import json
import os
from pathlib import Path
import tempfile
import time


def write_json_atomically(path, document):
    """Replace a local JSON file only after its complete contents are on disk.

    A unique temporary filename avoids collisions when separate app workers
    persist different data in the same directory. Temporary files are removed
    on exceptions; the previous destination is preserved.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=target.name + ".",
            suffix=".tmp", dir=target.parent, delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Windows file scanners, sync software and concurrent app windows
        # can briefly hold the previous preferences.json open. Retry only
        # Windows sharing/access-violation errors with bounded backoff.
        # Any other storage fault must retain the prior committed JSON.
        for attempt in range(4):
            try:
                os.replace(temporary, target)
                break
            except PermissionError as exc:
                if (os.name != "nt" or getattr(exc, "winerror", None)
                        not in (5, 32, 33) or attempt == 3):
                    raise
                time.sleep(0.025 * (attempt + 1))
    finally:
        if temporary is not None:
            # Failure to clean a stale temporary file is not permission to
            # mask the actual persistence result or crash the settings UI.
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
