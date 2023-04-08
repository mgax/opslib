import os

from opslib.components import Stack

from .dns import Cloudflare, MailDnsRecords
from .hetzner import VPS
from .mailu import Mailu


class MailuExample(Stack):
    def build(self):
        zone_name = os.environ["CLOUDFLARE_ZONE_NAME"]
        dns_name = os.environ["MAILU_DNS_NAME"]

        self.vps = VPS(
            name="opslib-example-mailu",
        )

        self.cloudflare = Cloudflare(
            account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
            zone_id=os.environ["CLOUDFLARE_ZONE_ID"],
            zone_name=zone_name,
            dns_name=dns_name,
            public_address=self.vps.server.output["ipv4_address"],
        )

        self.mailu = Mailu(
            zone_name=zone_name,
            dns_name=dns_name,
            directory=self.vps.host.directory("/opt/mailu"),
            volumes=self.vps.host.directory("/opt/volumes"),
            public_address=self.vps.server.output["ipv4_address"],
        )

        self.dns = MailDnsRecords(
            mailu=self.mailu,
            cloudflare=self.cloudflare,
        )


def get_stack():
    return MailuExample()
