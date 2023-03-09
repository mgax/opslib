import logging
import os
import subprocess
import sys

from .results import Result

logger = logging.getLogger(__name__)


class LocalRunResult(Result):
    def __init__(self, completed, encoding=None):
        def decode(buf):
            return buf.decode(encoding) if encoding else buf

        self.completed = completed
        self.stderr = decode(self.completed.stderr or b"")
        self.stdout = decode(self.completed.stdout or b"")

        super().__init__(
            changed=True,
            output=self.stderr + self.stdout,
            failed=completed.returncode != 0,
        )

    def __str__(self):
        return f"{super().__str__()} {self.completed.args}"


def run(
    *args,
    input=None,
    capture_output=True,
    encoding="utf8",
    extra_env=None,
    exit=False,
    **kwargs,
):
    if input is None:
        logger.debug("Running %r", args)

    else:
        if encoding and isinstance(input, str):
            input = input.encode("utf8")

        logger.debug("Running %r with input = %r", args, input)

    if extra_env:
        kwargs["env"] = dict(os.environ, **extra_env)

    completed = subprocess.run(
        args,
        input=input,
        capture_output=capture_output,
        **kwargs,
    )

    if exit:
        sys.exit(completed.returncode)

    result = LocalRunResult(completed, encoding=encoding)
    result.raise_if_failed("Local command failed")
    return result
