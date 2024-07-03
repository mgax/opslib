from collections.abc import Iterator
from contextlib import contextmanager
import hashlib
import json
from functools import partial, wraps
from pathlib import Path

from .results import Result


class ComponentUpToDate:
    def __init__(self, component, get_snapshot):
        self.component = component
        self.get_snapshot = get_snapshot

    @contextmanager
    def json_path(self) -> Iterator[Path]:
        with self.component.state_directory() as statedir:
            yield statedir / "uptodate.json"

    def _get_hash(self):
        snapshot = self.get_snapshot()
        buffer = json.dumps(snapshot, sort_keys=True).encode("utf8")
        return hashlib.sha256(buffer).hexdigest()

    def set(self, uptodate):
        with self.json_path() as json_path:
            json_path.write_text(json.dumps(self._get_hash() if uptodate else None))

    def get(self):
        try:
            with self.json_path() as json_path:
                hash = json.loads(json_path.read_text())

        except FileNotFoundError:
            hash = None

        return hash == self._get_hash() if hash else False


class UpToDate:
    def __get__(self, obj, objtype=None):
        return ComponentUpToDate(obj, partial(self.snapshot_func, obj))

    def snapshot(self, func):
        self.snapshot_func = func
        return func

    def refresh(self, func):
        @wraps(func)
        def decorator(obj):
            result = func(obj)
            obj.uptodate.set(not result.changed)
            return result

        return decorator

    def deploy(self, func):
        @wraps(func)
        def decorator(obj, dry_run=False):
            if obj.uptodate.get():
                return Result()

            result = func(obj, dry_run=dry_run)
            obj.uptodate.set((not result.changed) if dry_run else True)
            return result

        return decorator

    def destroy(self, func):
        @wraps(func)
        def decorator(obj, dry_run=False):
            result = func(obj, dry_run=dry_run)
            obj.uptodate.set(False)
            return result

        return decorator
