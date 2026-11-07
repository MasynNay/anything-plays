"""Crash-safe JSON persistence for the 2.1 test application's local settings.

All writes create a temporary sibling, flush the complete JSON document,
then atomically replace the previous version. A process crash during the
temporary write cannot truncate an existing preferences or profile file.
"""

import json
import os
from pathlib import Path
import tempfile


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
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
