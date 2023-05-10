import json
from base64 import b64encode
from functools import cached_property

from opslib import Component, Prop, evaluate, lazy_property
from opslib.terraform import TerraformProvider


class Cloudflare(Component):
    class Props:
        zone_name = Prop(str)
        record_name = Prop(str)
        tunnel_secret = Prop(str)

    def build(self):
        self.provider = TerraformProvider(
            name="cloudflare",
            source="cloudflare/cloudflare",
            version="~> 4.2",
        )

        self.zone = self.provider.data(
            type="cloudflare_zone",
            args=dict(
                name=self.props.zone_name,
            ),
            output=["id", "account_id"],
        )

        self.tunnel = self.provider.resource(
            type="cloudflare_tunnel",
            args=dict(
                account_id=self.zone.output["account_id"],
                name=self.props.record_name,
                secret=self.secret_base64,
            ),
            output=["id"],
        )

        self.cname = self.provider.resource(
            type="cloudflare_record",
            args=dict(
                zone_id=self.zone.output["id"],
                name=self.props.record_name,
                type="CNAME",
                value=self.tunnel_cname,
                proxied=True,
            ),
        )

    @cached_property
    def secret_base64(self):
        return b64encode(self.props.tunnel_secret.encode()).decode()

    @lazy_property
    def tunnel_cname(self):
        return f"{evaluate(self.tunnel.output['id'])}.cfargotunnel.com"

    def token(self):
        payload = {
            "a": evaluate(self.zone.output["account_id"]),
            "t": evaluate(self.tunnel.output["id"]),
            "s": evaluate(self.secret_base64),
        }
        return b64encode(json.dumps(payload).encode("utf8")).decode("utf8")

    def sidecar(self, url):
        return dict(
            image="cloudflare/cloudflared",
            command=f"tunnel --no-autoupdate run --token {self.token()} --url {url}",
            restart="unless-stopped",
        )
