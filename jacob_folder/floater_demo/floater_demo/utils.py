from __future__ import annotations

from pathlib import Path
import hashlib
import json

import numpy as np


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def stable_color(seed: str | int) -> tuple[int, int, int]:
    digest = hashlib.md5(str(seed).encode("utf-8")).digest()
    return (
        50 + digest[0] % 180,
        50 + digest[1] % 180,
        50 + digest[2] % 180,
    )


def mask_to_bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask > 0)
    if xs.size == 0 or ys.size == 0:
        return (0, 0, 0, 0)
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    return (x0, y0, x1 - x0 + 1, y1 - y0 + 1)


def stem_id(path: str | Path) -> str:
    return Path(path).stem


def json_dumps(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=False)


def is_png(path: str | Path) -> bool:
    return Path(path).suffix.lower() == ".png"
