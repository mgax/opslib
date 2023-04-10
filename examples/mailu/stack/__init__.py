import os

from opslib.components import Stack

from .dns import CloudflareZone, MailDnsRecords
from .hetzner import VPS
from .mailu import Mailu


class MailuExample(Stack):
    def build(self):
        zone_name = os.environ["CLOUDFLARE_ZONE_NAME"]
        hostname = os.environ["MAILU_HOSTNAME"]
        main_domain = os.environ["MAILU_DOMAIN"]

        self.vps = VPS(
            hostname=hostname,
        )

        self.zone = CloudflareZone(
            zone_name=zone_name,
        )

        self.a_record = self.zone.record(
            fqdn=main_domain,
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


def get_stack():
    return MailuExample()
