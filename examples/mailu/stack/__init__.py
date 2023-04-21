import os

from opslib.components import Stack

from .backups import Backups
from .dns import CloudflareZone, MailDnsRecords
from .hetzner import VPS
from .mailu import Mailu


class MailuExample(Stack):
    def build(self):
        zone_name = os.environ["CLOUDFLARE_ZONE_NAME"]
        hostname = os.environ["MAILU_HOSTNAME"]
        main_domain = os.environ["MAILU_DOMAIN"]
        restic_password = os.environ["RESTIC_PASSWORD"]

        self.vps = VPS(
            hostname=hostname,
        )

        self.zone = CloudflareZone(
            zone_name=zone_name,
        )

        self.a_record = self.zone.record(
            fqdn=hostname,
            type="A",
            body=dict(
                value=self.vps.server.output["ipv4_address"],
            ),
        )

        self.mailu = Mailu(
            hostname=hostname,
            main_domain=main_domain,
            directory=self.vps.host.directory("/opt/mailu"),
            volumes=self.vps.host.directory("/opt/volumes"),
            public_address=self.vps.server.output["ipv4_address"],
        )

        self.dns = MailDnsRecords(
            mailu=self.mailu,
            zone=self.zone,
        )

        self.backups = Backups(
            directory=self.vps.host.directory("/opt/backups"),
            b2_name=f"opslib-backups-{hostname.replace('.', '-')}",
            restic_password=restic_password,
            backup_paths=self.mailu.backup_paths,
            backup_exclude=self.mailu.backup_exclude,
        )


def get_stack():
    return MailuExample()
