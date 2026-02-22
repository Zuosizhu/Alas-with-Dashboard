import json
import os
from datetime import datetime
from typing import Any, Callable, Optional


def append_jsonl(
    path: str,
    payload: Any,
    rotate_bytes: Optional[int] = None,
    error_callback: Optional[Callable[[Exception], None]] = None,
) -> bool:
    """Append one JSON object line to `path`, rotating when oversized.

    Returns:
        bool: True when the line is written, False on any failure.
    """
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        if rotate_bytes and os.path.exists(path) and os.path.getsize(path) >= rotate_bytes:
            root, ext = os.path.splitext(path)
            ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            rotated = f'{root}.{ts}{ext or ".jsonl"}'
            os.replace(path, rotated)

        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=True) + '\n')
        return True
    except Exception as e:
        if error_callback is not None:
            try:
                error_callback(e)
            except Exception:
                # Logging callback must never break caller flow.
                pass
        return False
