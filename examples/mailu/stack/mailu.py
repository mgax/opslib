import click
import yaml

from opslib.components import Component
from opslib.lazy import evaluate, lazy_property
from opslib.places import Directory
from opslib.props import Prop

from .tokens import RandomToken


class Mailu(Component):
    class Props:
        zone_name = Prop(str)
        dns_name = Prop(str)
        directory = Prop(Directory)
        volumes = Prop(Directory)
        public_address = Prop(str, lazy=True)

    mailu_version = "2.0"
    ports = [80, 443, 25, 465, 587, 110, 995, 143, 993]

    @property
    def domain(self):
        return f"{self.props.dns_name}.{self.props.zone_name}"

    def build(self):
        self.directory = self.props.directory
        self.volumes = self.props.volumes
        self.secret_key = RandomToken(length=16)
        self.api_token = RandomToken()

        self.env_file = self.directory.file(
            name="mailu.env",
            content=self.env_content,
        )

        self.compose_file = self.directory.file(
            name="docker-compose.yml",
            content=self.compose_content,
        )

        self.compose_up = self.directory.host.command(
            args=[*self.compose_args, "up", "-d"],
            run_after=[
                self.env_file,
                self.compose_file,
            ],
        )

    @lazy_property
    def compose_content(self):
        public_address = evaluate(self.props.public_address)

        content = dict(
            version="2.2",
            services=dict(
                redis=dict(
                    image="redis:alpine",
                    restart="unless-stopped",
                    volumes=[
                        f"{self.volumes.path}/redis:/data",
                    ],
                    depends_on=["resolver"],
                    dns=["192.168.203.254"],
                ),
                front=dict(
                    image=self.mailu_image("nginx"),
                    restart="unless-stopped",
                    env_file="mailu.env",
                    logging=self.journald_logging("front"),
                    ports=[f"{public_address}:{port}:{port}" for port in self.ports],
                    networks=["default", "webmail"],
                    volumes=[
                        f"{self.volumes.path}/certs:/certs",
                        f"{self.volumes.path}/overrides/nginx:/overrides:ro",
                    ],
                    depends_on=["resolver"],
                    dns=["192.168.203.254"],
                ),
                resolver=dict(
                    image=self.mailu_image("unbound"),
                    env_file="mailu.env",
                    restart="unless-stopped",
                    networks=dict(
                        default=dict(ipv4_address="192.168.203.254"),
                    ),
                ),
                admin=dict(
                    image=self.mailu_image("admin"),
                    restart="unless-stopped",
                    env_file="mailu.env",
                    logging=self.journald_logging("admin"),
                    volumes=[
                        f"{self.volumes.path}/data:/data",
                        f"{self.volumes.path}/dkim:/dkim",
                    ],
                    depends_on=["redis", "resolver"],
                    dns=["192.168.203.254"],
                ),
                imap=dict(
                    image=self.mailu_image("dovecot"),
                    restart="unless-stopped",
                    env_file="mailu.env",
                    logging=self.journald_logging("imap"),
                    volumes=[
                        f"{self.volumes.path}/mail:/mail",
                        f"{self.volumes.path}/overrides/dovecot:/overrides:ro",
                    ],
                    depends_on=["front", "resolver"],
                    dns=["192.168.203.254"],
                ),
                smtp=dict(
                    image=self.mailu_image("postfix"),
                    restart="unless-stopped",
                    env_file="mailu.env",
                    logging=self.journald_logging("smtp"),
                    volumes=[
                        f"{self.volumes.path}/mailqueue:/queue",
                        f"{self.volumes.path}/overrides/postfix:/overrides:ro",
                    ],
                    depends_on=["front", "resolver"],
                    dns=["192.168.203.254"],
                ),
                antispam=dict(
                    image=self.mailu_image("rspamd"),
                    hostname="antispam",
                    restart="unless-stopped",
                    env_file="mailu.env",
                    logging=self.journald_logging("antispam"),
                    volumes=[
                        f"{self.volumes.path}/filter:/var/lib/rspamd",
                        f"{self.volumes.path}/overrides/rspamd:/overrides:ro",
                    ],
                    depends_on=["front", "redis", "resolver"],
                    dns=["192.168.203.254"],
                ),
                webmail=dict(
                    image=self.mailu_image("webmail"),
                    restart="unless-stopped",
                    env_file="mailu.env",
                    volumes=[
                        f"{self.volumes.path}/webmail:/data",
                        f"{self.volumes.path}/overrides/roundcube:/overrides:ro",
                    ],
                    networks=["webmail"],
                    depends_on=["front"],
                ),
            ),
            networks=dict(
                default=dict(
                    driver="bridge",
                    ipam=dict(
                        driver="default",
                        config=[
                            dict(subnet="192.168.203.0/24"),
                        ],
                    ),
                ),
                webmail=dict(
                    driver="bridge",
                ),
            ),
        )

        return yaml.dump(evaluate(content), sort_keys=False)

    def mailu_image(self, name):
        return f"ghcr.io/mailu/{name}:{self.mailu_version}"

    def journald_logging(self, name):
        return dict(
            driver="journald",
            options=dict(
                tag=f"mailu-{name}",
            ),
        )

    @lazy_property
    def env_content(self):
        vars = dict(
            SECRET_KEY=self.secret_key.value,
            SUBNET="192.168.203.0/24",
            DOMAIN=self.domain,
            HOSTNAMES=self.domain,
            POSTMASTER="admin",
            TLS_FLAVOR="letsencrypt",
            ADMIN="true",
            WEBMAIL="snappymail",
            API="true",
            MESSAGE_SIZE_LIMIT="50000000",
            FETCHMAIL_ENABLED="False",
            RECIPIENT_DELIMITER="+",
            DMARC_RUA="admin",
            DMARC_RUF="admin",
            WEBROOT_REDIRECT="/webmail",
            WEB_ADMIN="/admin",
            WEB_WEBMAIL="/webmail",
            WEB_API="/api",
            SITENAME="Mailu",
            WEBSITE="https://mailu.io",
            LOG_LEVEL="WARNING",
            API_TOKEN=self.api_token.value,
        )
        return "".join(f"{key}={value}\n" for key, value in evaluate(vars).items())

    @property
    def compose_args(self):
        return ["docker", "compose", "--project-directory", self.directory.path]

    def add_commands(self, cli):
        @cli.command(context_settings=dict(ignore_unknown_options=True))
        @click.argument("args", nargs=-1, type=click.UNPROCESSED)
        def compose(args):
            """Run `docker compose` with the given arguments"""
            self.directory.host.run(
                *[*self.compose_args, *args],
                capture_output=False,
                exit=True,
            )

        @cli.command(context_settings=dict(ignore_unknown_options=True))
        @click.argument("args", nargs=-1, type=click.UNPROCESSED)
        def admin(args):
            """Run Mailu `admin` with the given arguments"""
            self.directory.host.run(
                *[*self.compose_args, "exec", "admin", "flask", "mailu", *args],
                capture_output=False,
                exit=True,
            )
