import json
from pathlib import Path
from typing import Any

_CACHE_ROOT: Path = Path(__file__).resolve().parent.parent / "data" / "cache"


class FileCache:
    def __init__(self, namespace: str) -> None:
        self._dir: Path = _CACHE_ROOT / namespace

    def _key_path(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    def read(self, key: str) -> dict[str, Any] | None:
        path: Path = self._key_path(key)
        if path.exists():
            return json.loads(path.read_text())  # type: ignore
        return None

    def write(self, key: str, data: dict[str, Any]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._key_path(key).write_text(json.dumps(data, indent=2))
