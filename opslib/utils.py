from pathlib import Path
from tempfile import TemporaryDirectory

from .local import run


def colordiff(path, before, after):
    diff_output = plain_diff(path, before, after)
    return run("colordiff", input=diff_output).stdout


def plain_diff(path, before, after):
    with TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)
        before_path = tmp / "before"
        after_path = tmp / "after"

        with before_path.open("w") as f:
            f.write(before)

        with after_path.open("w") as f:
            f.write(after)

        result = run(
            "diff",
            "-U3",
            before_path,
            after_path,
            "--label",
            path,
            "--label",
            path,
            check=False,
        )
        if result.completed.returncode in [0, 1]:
            return result.stdout

        result.raise_if_failed()


def get_diff_tool():
    if run("which", "colordiff", check=False).stdout:
        return colordiff

    return plain_diff


def diff(path, before, after):
    tool = get_diff_tool()
    return tool(path, before, after)
