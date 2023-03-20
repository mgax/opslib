import json
import logging
import sys
from functools import cached_property
from pathlib import Path

logger = logging.getLogger(__name__)


class ComponentStateDirectory:
    def __init__(self, meta):
        self.meta = meta

        if meta.parent is None:
            self._prefix = meta.component.get_state_directory()

        else:
            self._prefix = meta.parent._meta.statedir._prefix / meta.name

        self._path = self._prefix / "_statedir"

    def init(self):
        changed = False

        if not self._prefix.exists():
            logger.debug("ComponentState init %s", self._prefix)
            self._prefix.mkdir(mode=0o700)
            changed = True

        if not self._path.exists():
            logger.debug("ComponentState init %s", self._path)
            self._path.mkdir(mode=0o700)
            changed = True

        return changed

    @cached_property
    def path(self):
        assert (
            self._path.is_dir()
        ), f"State directory for {self.meta.component!r} missing, please run `init`."
        return self._path


class StateDirectory:
    def __get__(self, obj, objtype=None):
        return ComponentStateDirectory(obj)


def default_state_directory(stack):
    module = sys.modules[stack.__module__]
    return Path(module.__file__).parent / ".opslib"


class ComponentJsonState:
    def __init__(self, component):
        self.component = component

    @cached_property
    def _path(self):
        return self.component._meta.statedir.path / "state.json"

    @cached_property
    def _data(self):
        try:
            with self._path.open() as f:
                return json.load(f)

        except FileNotFoundError:
            return {}

    def save(self, data=(), **kwargs):
        with self._path.open("w") as f:
            json.dump(dict(data, **kwargs), f, indent=2)

        self.__dict__["_data"] = data

    def update(self, *args, **kwargs):
        data = dict(self._data)
        data.update(*args, **kwargs)
        self.save(data)

    def __setitem__(self, key, value):
        self.update(**{key: value})

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __eq__(self, other):
        return self._data == other

    def __iter__(self):
        return iter(self._data.items())


class JsonState:
    def __get__(self, obj, objtype=None):
        return ComponentJsonState(obj)
