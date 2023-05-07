import json
import logging

logger = logging.getLogger(__name__)


class ComponentStateDirectory:
    def __init__(self, meta):
        self.meta = meta

    @property
    def prefix(self):
        if self.meta.parent is None:
            prefix = self.meta.stateroot

        else:
            parent_meta = self.meta.parent._meta
            prefix = parent_meta.statedir.prefix / self.meta.name

        self._mkdir(prefix)
        return prefix

    @property
    def path(self):
        path = self.prefix / "_statedir"
        self._mkdir(path)
        return path

    def _mkdir(self, path):
        if not path.is_dir():
            logger.debug("ComponentState init %s", path)
            path.mkdir(mode=0o700)


class StateDirectory:
    def __get__(self, obj, objtype=None):
        return ComponentStateDirectory(obj)


class ComponentJsonState:
    def __init__(self, component):
        self.component = component

    @property
    def _path(self):
        return self.component._meta.statedir.path / "state.json"

    @property
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
