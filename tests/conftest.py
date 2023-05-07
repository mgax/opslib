import socket
import time
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent

import pytest

from opslib.components import Stack
from opslib.local import run
from opslib.places import SshHost
from opslib.state import ComponentStateDirectory

IMAGE = "opslib-tests"
SSH_PORT = 22022
CONTAINER = "opslib-tests"
SRC = Path(__file__).parent / "container"
HOST_KEY = SRC / "ssh_host_ed25519_key.pub"
PRIVKEY = SRC / "id_ed25519"


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


def podman(*args, **kwargs):
    return run("podman", *args, **kwargs)


@pytest.fixture(scope="session")
def container_image():
    if not PRIVKEY.exists():
        run("ssh-keygen", "-t", "ed25519", "-f", PRIVKEY, "-N", "")
    podman("build", ".", "--tag", IMAGE, cwd=SRC)
    host_key = podman("run", "--rm", IMAGE, "cat", f"/etc/ssh/{HOST_KEY.name}").stdout
    HOST_KEY.write_text(host_key)
    return IMAGE


@contextmanager
def container(image):
    podman("rm", "-f", CONTAINER, check=False)
    podman(
        "run",
        "--rm",
        "--name",
        CONTAINER,
        "-p",
        f"127.0.0.1:{SSH_PORT}:22",
        "-d",
        "--cap-add",
        "SYS_CHROOT",
        image,
        "systemd",
    )

    try:
        yield

    finally:
        podman("kill", CONTAINER, check=False)
        podman("rm", "-f", CONTAINER, check=False)


def wait_for_port(port, timeout=10, poll_interval=0.1):
    expires = time.monotonic() + timeout
    while time.monotonic() < expires:
        print("trying ...", timeout, time.monotonic())
        try:
            socket.create_connection(("localhost", port))
            return

        except OSError:
            pass

        time.sleep(poll_interval)

    raise RuntimeError(f"Timeout expired waiting for SSH on port {port}")


@pytest.fixture
def ssh_container(container_image, tmp_path):
    with container(container_image):
        privkey = (SRC / "id_ed25519").read_text()
        pubkey = HOST_KEY.read_text()
        identity = tmp_path / "identity"
        known_hosts = tmp_path / "known_hosts"
        config_file = tmp_path / "ssh_config"

        identity.write_text(privkey)
        known_hosts.write_text(f"[localhost]:22022 {pubkey}\n")
        config_file.write_text(
            dedent(
                f"""\
                Host opslib-tests
                    UserKnownHostsFile {known_hosts}
                    Hostname localhost
                    Port {SSH_PORT}
                    User opslib
                    IdentityFile {identity}
                """
            )
        )

        identity.chmod(0o600)
        known_hosts.chmod(0o600)

        wait_for_port(SSH_PORT)

        yield SshHost(hostname="opslib-tests", config_file=config_file)


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", help="Run slow tests")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "slow" in item.keywords:
            if not config.getoption("--runslow"):
                item.add_marker(pytest.mark.skip(reason="need --runslow option to run"))


@pytest.fixture(autouse=True)
def no_statedir_outside_tmp_path(tmp_path, monkeypatch):
    original_mkdir = ComponentStateDirectory._mkdir

    def mock_mkdir(self, path):
        assert path.is_relative_to(tmp_path), "No statedir outside tmp"
        original_mkdir(self, path)

    monkeypatch.setattr(ComponentStateDirectory, "_mkdir", mock_mkdir)


@pytest.fixture
def TestingStack(tmp_path):
    class TestingStack(Stack):
        def __init__(self, **kwargs):
            super().__init__(stateroot=tmp_path / "statedir", **kwargs)

    return TestingStack


@pytest.fixture
def stack(TestingStack):
    return TestingStack()
