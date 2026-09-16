"""Write a file so a concurrent reader never sees half of it.

`Path.write_text` truncates the file and then writes it. A reader that opens it
in between gets a truncated JSON document and a JSONDecodeError. That is fine
when nothing else runs, and this project now refreshes the boards WHILE two
scoring runs append to their caches, so it stopped being fine.

Write to a temporary file in the same directory and rename it over the target.
Rename within one filesystem is atomic, so a reader sees either the whole old
file or the whole new one, never a mixture.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

__all__ = ["write_json_atomic"]


def write_json_atomic(path: Path, data, **dump_kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, **dump_kwargs)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        # Never leave the temp file behind on any exit path, including
        # KeyboardInterrupt, which is how a long run usually ends.
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
