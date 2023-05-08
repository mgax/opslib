import os

from opslib.components import Stack

from .backups import Backups
from .dns import CloudflareZone, MailDnsRecords
from .hetzner import VPS
from .mailu import Mailu

zone_name = os.environ["CLOUDFLARE_ZONE_NAME"]
hostname = os.environ["MAILU_HOSTNAME"]
main_domain = os.environ["MAILU_DOMAIN"]
restic_password = os.environ["RESTIC_PASSWORD"]

stack = Stack(__name__)

stack.vps = VPS(
    hostname=hostname,
)

stack.zone = CloudflareZone(
    zone_name=zone_name,
)

stack.a_record = stack.zone.record(
    fqdn=hostname,
    type="A",
    args=dict(
        value=stack.vps.server.output["ipv4_address"],
    ),
)

stack.mailu = Mailu(
    hostname=hostname,
    main_domain=main_domain,
    directory=stack.vps.host.directory("/opt/mailu"),
    volumes=stack.vps.host.directory("/opt/volumes"),
    public_address=stack.vps.server.output["ipv4_address"],
)

stack.dns = MailDnsRecords(
    mailu=stack.mailu,
    zone=stack.zone,
)

stack.backups = Backups(
    directory=stack.vps.host.directory("/opt/backups"),
    b2_name=f"opslib-backups-{hostname.replace('.', '-')}",
    restic_password=restic_password,
    backup_paths=stack.mailu.backup_paths,
    backup_exclude=stack.mailu.backup_exclude,
)
