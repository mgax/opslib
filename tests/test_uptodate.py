from unittest.mock import Mock

import pytest

from opslib.components import Component
from opslib.operations import apply
from opslib.props import Prop
from opslib.results import Result
from opslib.uptodate import UpToDate


@pytest.fixture
def mock_deploy():
    return Mock()


@pytest.fixture
def Bench(TestingStack, tmp_path, mock_deploy):
    path = tmp_path / "target.txt"

    class Target(Component):
        class Props:
            content = Prop(str)

        uptodate = UpToDate()

        @property
        @uptodate.snapshot
        def content(self):
            return self.props.content

        @uptodate.refresh
        def refresh(self):
            ok = path.exists() and path.read_text() == self.content
            return Result(changed=not ok)

        @uptodate.deploy
        def deploy(self, dry_run=False):
            if dry_run:
                return self.refresh()

            mock_deploy()
            path.write_text(self.content)
            return Result(changed=True)

    class Bench(TestingStack):
        class Props:
            content = Prop(str)

        def build(self):
            self.path = path
            self.target = Target(
                content=self.props.content,
            )

    return Bench


def test_after_deploy(Bench, mock_deploy):
    bench = Bench(content="hello")
    apply(bench, deploy=True)

    assert bench.path.read_text() == "hello"
    assert bench.target.uptodate.get()


@pytest.mark.parametrize("op", [dict(refresh=True), dict(deploy=True, dry_run=True)])
@pytest.mark.parametrize("same", [True, False])
def test_after_check(Bench, mock_deploy, op, same):
    bench = Bench(content="hello")
    bench.path.write_text("hello" if same else "different")
    assert not bench.target.uptodate.get()

    apply(bench, **op)
    assert bench.target.uptodate.get() == same

    mock_deploy.reset_mock()
    apply(bench, deploy=True)
    assert mock_deploy.call_count == (not same)


@pytest.mark.parametrize("same", [True, False])
@pytest.mark.parametrize("dry_run", [True, False])
def test_skips_check(Bench, mock_deploy, same, dry_run):
    bench = Bench(content="hello")
    apply(bench, deploy=True)
    mock_deploy.reset_mock()

    if not same:
        bench.path.write_text("different")

    results = apply(bench, deploy=True, dry_run=dry_run)
    assert not results[bench.target].changed


def test_change(Bench):
    bench = Bench(content="hello")
    apply(bench, deploy=True)

    bench2 = Bench(content="different")
    results = apply(bench2, deploy=True)
    assert results[bench2.target].changed
    assert bench.path.read_text() == "different"
