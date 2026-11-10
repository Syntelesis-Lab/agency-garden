"""One canonical JSON representation for configurations, records and identities."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    """Reject non-finite values instead of writing nonstandard JSON evidence."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def clone(value: Any) -> Any:
    return json.loads(canonical(value))


def write_json(path: Path, value: Any) -> None:
    """Replace complete exports atomically, even if rendering is interrupted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
