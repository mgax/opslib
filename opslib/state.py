from collections.abc import Iterator
from contextlib import contextmanager
import json
import logging
from pathlib import Path
import shutil
from typing import cast

import opslib

logger = logging.getLogger(__name__)


class FilesystemStateProvider:
    def __init__(self, stateroot: Path):
        self.stateroot = stateroot

    def _get_directory(self, component: "opslib.Component") -> Path:
        if component._meta.parent is None:
            return self.stateroot

        return self._get_directory(component._meta.parent) / component._meta.name

    def _get_state_directory(self, component: "opslib.Component"):
        return self._get_directory(component) / "_statedir"

    @contextmanager
    def state_directory(self, component: "opslib.Component"):
        statedir = self._get_state_directory(component)
        if not statedir.exists():
            statedir.mkdir(parents=True)
        yield statedir

    def run_gc(self, component: "opslib.Component", dry_run=False):
        child_names = {child._meta.name for child in component}

        def unexpected(item):
            if isinstance(component, StatefulMixin) and item.name == "_statedir":
                return False

            if not item.is_dir():
                return False

            return item.name not in child_names

        directory = self._get_directory(component)
        if directory.exists():
            for item in directory.iterdir():
                if unexpected(item):
                    print(item)
                    if dry_run:
                        continue

                    shutil.rmtree(item)

        for child in component:
            self.run_gc(child, dry_run=dry_run)


class ComponentJsonState:
    def __init__(self, component):
        self.component = component

    @contextmanager
    def json_path(self) -> Iterator[Path]:
        with self.component.state_directory() as statedir:
            yield statedir / "state.json"

    @property
    def _data(self):
        try:
            with self.json_path() as json_path:
                with json_path.open() as f:
                    return json.load(f)

        except FileNotFoundError:
            return {}

    def save(self, data=(), **kwargs):
        with self.json_path() as json_path:
            with json_path.open("w") as f:
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


class StatefulMixin:
    _meta: "opslib.components.Meta"

    @contextmanager
    def state_directory(self):
        provider = self._meta.stack._state_provider
        with provider.state_directory(cast(opslib.Component, self)) as statedir:
            yield statedir
