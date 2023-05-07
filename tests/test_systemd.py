import pytest

from opslib.extras.systemd import SystemdUnit
from opslib.operations import apply


@pytest.mark.slow
def test_unit_enable(ssh_container, stack):
    stack.unit = SystemdUnit(
        host=ssh_container.sudo(),
        name="httplogs.service",
        contents=dict(
            Service=dict(
                ExecStart="python3 -m http.server",
                WorkingDirectory="/var/log",
            ),
            Install=dict(
                WantedBy="multi-user.target",
            ),
        ),
    )
    stack.enable_unit = stack.unit.enable_command(now=True)

    apply(stack, deploy=True)

    dpkg_log = ssh_container.run("curl", "localhost:8000/dpkg.log").stdout
    assert "status installed curl:" in dpkg_log
