from pathlib import Path
from textwrap import dedent

import pytest

from opslib.local import run
from opslib.places import SshHost

CONTAINER_IMAGE_NAME = "opslib-tests"
CONTAINER_SSH_PORT = 22022
CONTAINER_NAME = "opslib-tests"
CONTAINER_SRC = Path(__file__).parent / "sshd-container"


class VM:
    def __init__(self, name):
        self.name = name
        self.hostname = f"{name}.miv"

    def create(self, image):
        return run("miv", "create", image, self.name)

    def destroy(self):
        return run("miv", "destroy", self.name)

    def start(self):
        return run(
            "miv",
            "start",
            self.name,
            "--daemon",
            "--wait-for-ssh=10",
            capture_output=False,
        )


@pytest.fixture
def container_image():
    run("podman", "build", ".", "--tag", CONTAINER_IMAGE_NAME, cwd=CONTAINER_SRC)
    return CONTAINER_IMAGE_NAME


@pytest.fixture
def container_ssh(container_image, tmp_path):
    run("podman", "kill", CONTAINER_NAME, check=False)
    run(
        "podman",
        "run",
        "--rm",
        "--name",
        CONTAINER_NAME,
        "-p",
        f"127.0.0.1:{CONTAINER_SSH_PORT}:22",
        "-d",
        "--cap-add",
        "SYS_CHROOT",
        container_image,
    )

    with (CONTAINER_SRC / "id_ed25519").open() as f:
        privkey = f.read()

    with (CONTAINER_SRC / "ssh_host_ed25519_key.pub").open() as f:
        pubkey = f.read()

    identity = tmp_path / "identity"
    known_hosts = tmp_path / "known_hosts"
    config_file = tmp_path / "ssh_config"

    with identity.open("w") as f:
        f.write(privkey)

    with known_hosts.open("w") as f:
        f.write(f"[localhost]:22022 {pubkey}\n")

    with config_file.open("w") as f:
        f.write(
            dedent(
                f"""\
                    Host opslib-tests
                        UserKnownHostsFile {known_hosts}
                        Hostname localhost
                        Port {CONTAINER_SSH_PORT}
                        User opslib
                        IdentityFile {identity}
                """
            )
        )

    identity.chmod(0o600)
    known_hosts.chmod(0o600)

    try:
        yield SshHost("opslib-tests", config_file=config_file)

    finally:
        run("podman", "kill", CONTAINER_NAME)


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", help="Run slow tests")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "slow" in item.keywords:
            if not config.getoption("--runslow"):
                item.add_marker(pytest.mark.skip(reason="need --runslow option to run"))


@pytest.fixture(autouse=True)
def no_statedir_outside_tmp_path(tmp_path, monkeypatch):
    from opslib import state

    original_init = state.ComponentStateDirectory.init

    def mock_init(self):
        assert self._prefix.is_relative_to(tmp_path), "No statedir outside tmp"
        original_init(self)

    monkeypatch.setattr(state.ComponentStateDirectory, "init", mock_init)


@pytest.fixture
def Stack(tmp_path):
    from opslib.components import Stack

    class TestingStack(Stack):
        def get_state_directory(self):
            return tmp_path / "statedir"

    return TestingStack
