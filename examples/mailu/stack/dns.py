import re

import click

from opslib.components import Component
from opslib.lazy import Lazy, evaluate, lazy_property
from opslib.local import run
from opslib.operations import Printer
from opslib.props import Prop
from opslib.results import Result
from opslib.state import JsonState
from opslib.terraform import TerraformProvider
from opslib.utils import diff

from .mailu import Mailu

DNS_RECORDS = {
    "mx": ("@", "MX"),
    "spf": ("@", "TXT"),
    # XXX there is no mechanism for updating the TLSA record when the cert is renewed
    # "tlsa": ("_25._tcp.@", "TLSA"),
    "dkim": ("dkim._domainkey.@", "TXT"),
    "dmarc": ("_dmarc.@", "TXT"),
    "dmarc_report": ("@_report._dmarc.@", "TXT"),
    "autoconfig_imap": ("_imap._tcp.@", "SRV"),
    "autoconfig_pop3": ("_pop3._tcp.@", "SRV"),
    "autoconfig_submission": ("_submission._tcp.@", "SRV"),
    "autoconfig_autodiscover": ("_autodiscover._tcp.@", "SRV"),
    "autoconfig_submissions": ("_submissions._tcp.@", "SRV"),
    "autoconfig_imaps": ("_imaps._tcp.@", "SRV"),
    "autoconfig_pop3s": ("_pop3s._tcp.@", "SRV"),
    "autoconfig_cname": ("autoconfig.@", "CNAME"),
}


class CloudflareZone(Component):
    class Props:
        zone_name = Prop(str)

    def build(self):
        # https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs
        self.provider = TerraformProvider(
            name="cloudflare",
            source="cloudflare/cloudflare",
            version="~> 4.2",
        )

        self.zone_lookup = self.provider.data(
            type="cloudflare_zones",
            args=dict(
                filter=dict(
                    name=self.props.zone_name,
                ),
            ),
            output=["zones"],
        )

    @lazy_property
    def zone_id(self):
        zones = evaluate(self.zone_lookup.output["zones"])
        assert len(zones) == 1, f"Expected one zone, found {len(zones)}: {zones!r}"
        return zones[0]["id"]

    def record(self, fqdn, type, args=None):
        def get_args():
            return dict(
                zone_id=evaluate(self.zone_id),
                name=self.name_in_zone(fqdn),
                type=type,
                proxied=False,
                **evaluate(args),
            )

        return self.provider.resource(
            type="cloudflare_record",
            args=Lazy(get_args),
        )

    def name_in_zone(self, fqdn):
        if fqdn == self.props.zone_name:
            return "@"

        suffix = f".{self.props.zone_name}"
        assert fqdn.endswith(suffix), f"{fqdn!r} not in zone {self.props.zone_name!r}"
        return fqdn[: -len(suffix)]


class MailDnsRecords(Component):
    class Props:
        mailu = Prop(Mailu)
        zone = Prop(CloudflareZone)

    state = JsonState()

    def build(self):
        zone = self.props.zone

        def dns_record(key):
            name_format, type = DNS_RECORDS[key]
            name = self.get_name(name_format)

            def get_args():
                line = evaluate(self.mailu_records)[key]
                (_name, _ttl, _in, _type, _value) = line.split(" ", 4)
                if (_name, _in, _type) != (name, "IN", type):
                    # We need must careful with data from the Mailu API: if the
                    # instance is compromised, it should not be able to set
                    # random DNS records in our zone.
                    raise ValueError(f"Unexpected record for {key!r}: {line!r}")

                ttl = int(_ttl)

                if type == "MX":
                    (_priority, value) = _value.split(" ", 1)
                    return dict(
                        ttl=ttl,
                        priority=int(_priority),
                        value=value,
                    )

                if type == "TLSA":
                    (_usage, _selector, _matching_type, _hash) = _value.split()
                    return dict(
                        ttl=ttl,
                        data=dict(
                            usage=int(_usage),
                            selector=int(_selector),
                            matching_type=int(_matching_type),
                            certificate=_hash,
                        ),
                    )

                if type == "SRV":
                    (_service, _proto, _name) = name.split(".", 2)
                    (_priority, _weight, _port, _target) = _value.split()
                    return dict(
                        ttl=ttl,
                        data=dict(
                            service=_service,
                            proto=_proto,
                            name=_name.rstrip("."),
                            priority=_priority,
                            weight=_weight,
                            port=_port,
                            target=_target.rstrip("."),
                        ),
                    )

                return dict(
                    ttl=ttl,
                    value=_value.strip('"').replace('" "', ""),
                )

            return zone.record(
                fqdn=name.rstrip("."),
                type=type,
                args=Lazy(get_args),
            )

        for key in DNS_RECORDS:
            setattr(self, key, dns_record(key))

    @lazy_property
    def mailu_records(self):
        mailu = self.props.mailu
        data = mailu.api.get(f"/domain/{mailu.props.main_domain}").json
        autoconfig_map = {
            record.split()[0]: record for record in data["dns_autoconfig"]
        }

        rv = {}

        for key, (name_format, _) in DNS_RECORDS.items():
            if key.startswith("autoconfig_"):
                rv[key] = autoconfig_map[self.get_name(name_format)]

            else:
                rv[key] = data[f"dns_{key}"]

        return rv

    def get_name(self, name_format):
        return name_format.replace("@", f"{self.props.mailu.props.main_domain}.")

    def add_commands(self, cli):
        @cli.command()
        @click.argument("server", default="")
        def check(server):
            """
            Compare expected DNS records with the ones returned by ``dig``.
            Optionally provide a DNS server to query directly to avoid waiting
            for DNS propagation.
            """

            def dig(name_format, type):
                cmd = ["dig", "+noall", "+answer"]
                if server:
                    cmd.append(f"@{server}")
                dig_result = run(*cmd, type, self.get_name(name_format))
                return re.sub(r"\s+", " ", dig_result.output.strip()).replace('" "', "")

            expected = "".join(
                record.replace('" "', "") + "\n"
                for record in evaluate(self.mailu_records).values()
            )
            actual = "".join(f"{dig(*DNS_RECORDS[key])}\n" for key in DNS_RECORDS)
            result = Result(
                changed=actual != expected,
                output=diff("dns", expected, actual),
            )
            Printer(self).print_result(result)
            if not result.changed:
                click.echo(actual)
