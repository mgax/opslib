import re

import click

from opslib.components import Component
from opslib.lazy import Lazy
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


class Cloudflare(Component):
    class Props:
        account_id = Prop(str)
        zone_id = Prop(str)
        zone_name = Prop(str)
        dns_name = Prop(str)
        public_address = Prop(str, lazy=True)

    def build(self):
        self.provider = TerraformProvider(
            name="cloudflare",
            source="cloudflare/cloudflare",
            version="~> 4.2",
        )

        self.a_record = self.record(
            type="A",
            name=self.props.dns_name,
            value=self.props.public_address,
        )

    def record(self, type, name, value):
        return self.provider.resource(
            type="cloudflare_record",
            body=dict(
                zone_id=self.props.zone_id,
                type=type,
                name=name,
                value=value,
                proxied=False,
            ),
        )


class MailDnsRecords(Component):
    class Props:
        mailu = Prop(Mailu)
        cloudflare = Prop(Cloudflare)

    state = JsonState()

    def build(self):
        cloudflare = self.props.cloudflare
        records = self.get_records()

        def dns_record(key):
            name, type = DNS_RECORDS[key]
            name = self.fqdn(name)

            def get_body():
                record = records[key]
                (_name, _ttl, _in, _type, value) = record.split(" ", 4)
                if (_name, _type) != (name, type):
                    raise ValueError(f"Unexpected record for {key!r}: {record!r}")

                body = dict(
                    zone_id=cloudflare.props.zone_id,
                    type=type,
                    name=self.reverse_fqdn(name),
                    ttl=int(_ttl),
                )

                if type == "MX":
                    (_priority, _value) = value.split(" ", 1)
                    body["data"] = dict(
                        priority=int(_priority),
                        value=_value,
                    )

                elif type == "TLSA":
                    (_usage, _selector, _matching_type, _hash) = value.split()
                    body["data"] = dict(
                        usage=int(_usage),
                        selector=int(_selector),
                        matching_type=int(_matching_type),
                        certificate=_hash,
                    )

                elif type == "SRV":
                    (_service, _proto, _name) = name.split(".", 2)
                    (_priority, _weight, _port, _target) = value.split()
                    body["data"] = dict(
                        service=_service,
                        proto=_proto,
                        name=_name,
                        priority=_priority,
                        weight=_weight,
                        port=_port,
                        target=_target,
                    )

                else:
                    body["data"] = dict(
                        value=value.strip('"').replace('" "', ""),
                    )

                return body

            return cloudflare.provider.resource(
                type="cloudflare_record",
                body=Lazy(get_body),
            )

        for key in DNS_RECORDS:
            setattr(self, key, dns_record(key))

    def get_records(self):
        mailu = self.props.mailu
        data = mailu.api.get(f"/domain/{mailu.domain}").json
        autoconfig_map = {
            record.split()[0]: record for record in data["dns_autoconfig"]
        }

        rv = {}

        for key, (name, _) in DNS_RECORDS.items():
            if key.startswith("autoconfig_"):
                rv[key] = autoconfig_map[self.fqdn(name)]

            else:
                rv[key] = data[f"dns_{key}"]

        return rv

    def fqdn(self, name):
        return name.replace("@", f"{self.props.mailu.domain}.")

    def reverse_fqdn(self, name):
        domain = f"{self.props.cloudflare.props.zone_name}."
        if name == domain:
            return "@"

        suffix = f".{domain}"
        assert name.endswith(suffix)
        return name[: -len(suffix)]

    def add_commands(self, cli):
        @cli.command()
        @click.argument("server")
        def check(server):
            def dig(name, type):
                cmd = ["dig", "+noall", "+answer"]
                dig_result = run(*cmd, type, self.fqdn(name), f"@{server}")
                return re.sub(r"\s+", " ", dig_result.output.strip()).replace('" "', "")

            expected = "".join(
                record.replace('" "', "") + "\n"
                for record in self.get_records().values()
            )
            actual = "".join(f"{dig(*DNS_RECORDS[key])}\n" for key in DNS_RECORDS)
            result = Result(
                changed=actual != expected,
                output=diff("dns", expected, actual),
            )
            Printer(self).print_result(result)
