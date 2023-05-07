import json

import pytest

from opslib.extras.restic import ResticRepository
from opslib.local import run
from opslib.operations import apply
from opslib.places import LocalHost


@pytest.mark.slow
def test_initialize(tmp_path, stack):
    repo_path = tmp_path / "repo"

    stack.repo = ResticRepository(
        repository=str(repo_path),
        password="not-so-secret",
    )
    assert not stack.repo.initialized

    apply(stack, deploy=True)
    assert repo_path.exists()
    assert stack.repo.initialized


@pytest.mark.slow
def test_backup_script(tmp_path, stack):
    repo_path = tmp_path / "repo"
    target_path = tmp_path / "target"
    target_path.mkdir()
    target_1_path = target_path / "1.txt"
    target_2_path = target_path / "2.txt"
    target_1_path.write_text("hello world")
    backup_script_path = tmp_path / "backup_script"

    stack.repo = ResticRepository(
        repository=str(repo_path),
        password="not-so-secret",
    )
    stack.plan = stack.repo.plan(
        precommands=[f"cp {target_1_path} {target_2_path}"],
        paths=[target_path],
        exclude=[target_1_path],
    )
    stack.script = stack.plan.backup_script(
        directory=LocalHost().directory(backup_script_path.parent),
        name=backup_script_path.name,
    )
    assert not stack.repo.initialized

    apply(stack, deploy=True)
    run(backup_script_path)

    snapshot_paths = {
        json.loads(line).get("path")
        for line in stack.repo.run("ls", "latest", "--json").stdout.splitlines()
    }
    assert str(target_1_path) not in snapshot_paths
    assert str(target_2_path) in snapshot_paths
    assert stack.repo.run("dump", "latest", target_2_path).stdout == "hello world"
