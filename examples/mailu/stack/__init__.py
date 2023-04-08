import os

from opslib.components import Stack

from .dns import CloudflareZone, MailDnsRecords
from .hetzner import VPS
from .mailu import Mailu


class MailuExample(Stack):
    def build(self):
        zone_name = os.environ["CLOUDFLARE_ZONE_NAME"]
        dns_name = os.environ["MAILU_DNS_NAME"]
        mail_domain = f"{dns_name}.{zone_name}"

        self.vps = VPS(
            name="opslib-example-mailu",
        )

        self.zone = CloudflareZone(
            account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
            zone_id=os.environ["CLOUDFLARE_ZONE_ID"],
            zone_name=zone_name,
        )

        self.a_record = self.zone.record(
            fqdn=mail_domain,
            type="A",
            body=dict(
                value=self.vps.server.output["ipv4_address"],
            ),
        )

        self.mailu = Mailu(
            hostname=mail_domain,
            main_domain=mail_domain,
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
