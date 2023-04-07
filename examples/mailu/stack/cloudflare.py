from opslib.components import Component
from opslib.props import Prop
from opslib.terraform import TerraformProvider


class Cloudflare(Component):
    class Props:
        account_id = Prop(str)
        zone_id = Prop(str)
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
