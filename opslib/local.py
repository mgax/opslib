import logging
import os
import subprocess
import sys

from .results import Result

logger = logging.getLogger(__name__)


class LocalRunResult(Result):
    """
    The result of a call to :func:`run`. In addition to the fields inherited
    from :class:`~opslib.results.Result`, it contains the following:

    :ivar completed: Exit code of the subprocess.
    :ivar stderr: Standard error from the subprocess (:class:`str`).
    :ivar stdout: Standard output from the subprocess (:class:`str`).
    """

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

        logger.debug("%r output:\n====\n%s====", self, self.output)

    def __str__(self):
        return f"{super().__str__()} {self.completed.args}"


def run(
    *args,
    input=None,
    capture_output=True,
    encoding="utf8",
    extra_env=None,
    exit=False,
    exit_on_error=False,
    check=True,
    exec=False,
    **kwargs,
):
    """
    The ``run`` function is a thin wrapper around :func:`subprocess.run`. It
    captures output and exit code and returns them as a :class:`LocalRunResult`
    object.

    :param input: Content to send to *stdin* (optional).
    :param capture_output: Capture *stdout* and *stderr*. Enabled by default.
    :param encoding: Text encoding for *stdin*, *stdout* and *stderr*. Defaults
                     to ``"utf8"``. Set to ``None`` to disable encoding and use
                     raw :class:`bytes`.
    :param extra_env: A dictionary of environment variables to send to the
                      subprocess, in addition to the ones in :obj:`os.environ`.
    :param exit: If set, when the subprocess is complete, call :func:`sys.exit`
                 with the subprocess exit code. Useful when wrapping commands
                 for the CLI.
    :param check: If True (default), when the subprocess exits with an error
                  code, raise :class:`~opslib.results.OperationError`.
    :param exec: Instead of calling :func:`subprocess.run`, invoke the command
                 using :func:`os.execvpe`. This will replace the current
                 program with the new one. Useful when wrapping commands for
                 the CLI.
    """

    if input is None:
        logger.debug("Running %r", args)

    else:
        if encoding and isinstance(input, str):
            input = input.encode("utf8")

        logger.debug("Running %r with input = %r", args, input)

    if extra_env:
        kwargs["env"] = dict(os.environ, **extra_env)

    if exec:
        env = dict(os.environ, **(extra_env or {}))
        os.execvpe(args[0], args, env)

    completed = subprocess.run(
        args,
        input=input,
        capture_output=capture_output,
        **kwargs,
    )

    if exit:
        sys.exit(completed.returncode)

    if exit_on_error and completed.returncode:
        sys.exit(completed.returncode)

    result = LocalRunResult(completed, encoding=encoding)
    if check:
        result.raise_if_failed("Local command failed")

    return result
