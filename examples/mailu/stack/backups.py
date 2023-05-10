from tempfile import TemporaryDirectory

from opslib.components import Component
from opslib.extras.restic import ResticRepository
from opslib.extras.systemd import SystemdTimerService
from opslib.lazy import evaluate, lazy_property
from opslib.local import run
from opslib.places import Directory
from opslib.props import Prop
from opslib.terraform import TerraformProvider


class Backups(Component):
    class Props:
        directory = Prop(Directory)
        b2_name = Prop(str)
        restic_password = Prop(str)
        backup_paths = Prop(list, lazy=True)
        backup_exclude = Prop(list, lazy=True)

    KEY_CAPABILITIES = [
        "deleteFiles",
        "listBuckets",
        "listFiles",
        "readFiles",
        "writeFiles",
    ]

    def build(self):
        self.directory = self.props.directory

        # https://registry.terraform.io/providers/Backblaze/b2/latest/docs
        self.provider = TerraformProvider(
            name="b2",
            source="Backblaze/b2",
            version="~> 0.8.4",
        )

        self.bucket = self.provider.resource(
            type="b2_bucket",
            args=dict(
                bucket_name=self.props.b2_name,
                bucket_type="allPrivate",
            ),
            output=["bucket_id"],
        )

        self.key = self.provider.resource(
            type="b2_application_key",
            args=dict(
                capabilities=self.KEY_CAPABILITIES,
                key_name=self.props.b2_name,
                bucket_id=self.bucket.output["bucket_id"],
            ),
            output=["application_key_id", "application_key"],
        )

        self.install_restic = self.directory.host.sudo().ansible_action(
            module="ansible.builtin.apt",
            args=dict(
                name="restic",
            ),
        )

        self.restic = ResticRepository(
            repository=f"b2:{self.props.b2_name}:",
            password=self.props.restic_password,
            env=self.env_vars,
        )

        self.plan = self.restic.plan(
            paths=self.props.backup_paths,
            exclude=self.props.backup_exclude,
        )

        self.backup_script = self.plan.backup_script(
            directory=self.directory,
            name="backup",
        )

        self.backup_cron = SystemdTimerService(
            host=self.directory.host.sudo(),
            name="mailu-backup-daily",
            exec_start=str(self.backup_script.path),
            on_calendar="03:00",
            timeout_start_sec="30m",
        )

    @lazy_property
    def env_vars(self):
        return dict(
            B2_ACCOUNT_ID=evaluate(self.key.output["application_key_id"]),
            B2_ACCOUNT_KEY=evaluate(self.key.output["application_key"]),
        )

    def run_b2(self, *args, **kwargs):
        run("b2", *args, extra_env=evaluate(self.env_vars), **kwargs)

    def add_commands(self, cli):
        @cli.forward_command
        def b2(args):
            self.run_b2(*args, capture_output=False, exit=True)

        @cli.command()
        def empty_bucket():
            with TemporaryDirectory() as tmp:
                self.run_b2(
                    "sync",
                    "--allowEmptySource",
                    "--delete",
                    tmp,
                    f"b2://{self.props.b2_name}",
                    capture_output=False,
                    exit=True,
                )
