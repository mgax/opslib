import hashlib
import json
from functools import partial, wraps

from .results import Result


class ThingUpToDate:
    def __init__(self, thing, get_snapshot):
        self.thing = thing
        self.get_snapshot = get_snapshot

    @property
    def _path(self):
        return self.thing._meta.statedir.path / "uptodate.json"

    def _get_hash(self):
        snapshot = self.get_snapshot()
        buffer = json.dumps(snapshot, sort_keys=True).encode("utf8")
        return hashlib.sha256(buffer).hexdigest()

    def set(self, uptodate):
        self._path.write_text(json.dumps(self._get_hash() if uptodate else None))

    def get(self):
        try:
            hash = json.loads(self._path.read_text())

        except FileNotFoundError:
            hash = None

        return hash == self._get_hash() if hash else False


class UpToDate:
    def __get__(self, obj, objtype=None):
        return ThingUpToDate(obj, partial(self.snapshot_func, obj))

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
