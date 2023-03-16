import logging
import sys
from functools import cached_property
from pathlib import Path

logger = logging.getLogger(__name__)


class ThingStateDirectory:
    def __init__(self, meta):
        self.meta = meta

        if meta.parent is None:
            self._prefix = meta.thing.get_state_directory()

        else:
            self._prefix = meta.parent._meta.statedir._prefix / meta.name

        self._path = self._prefix / "_statedir"

    def init(self):
        if not self._prefix.exists():
            logger.debug("ThingState init %s", self._prefix)
            self._prefix.mkdir(mode=0o700)

        if not self._path.exists():
            logger.debug("ThingState init %s", self._path)
            self._path.mkdir(mode=0o700)

    @cached_property
    def path(self):
        assert (
            self._path.is_dir()
        ), f"State directory for {self.meta.thing!r} missing, please run `init`."
        return self._path


class StateDirectory:
    def __get__(self, obj, objtype=None):
        return ThingStateDirectory(obj)


def default_state_directory(stack):
    module = sys.modules[stack.__module__]
    return Path(module.__file__).parent / ".opslib"
