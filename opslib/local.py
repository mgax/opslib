import sys
import subprocess

from .results import Result


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
    capture_output=True,
    encoding="utf8",
    exit=False,
    **kwargs,
):
    completed = subprocess.run(
        args,
        capture_output=capture_output,
        **kwargs,
    )

    if exit:
        sys.exit(completed.returncode)

    result = LocalRunResult(completed, encoding=encoding)
    result.raise_if_failed("Local command failed")
    return result
