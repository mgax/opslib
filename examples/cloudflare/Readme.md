# Opslib Cloudflare Example

The Cloudflare example uses the [Cloudflare Terraform Provider](https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs) to set up a [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) that publishes our app on the Internet. Cloudflare Tunnels act as a reverse proxy from Cloudflare's network, through the tunnel, straight to the app, without opening any port on the host. The tunnel is secured by a pre-shared secret and Cloudflare will set up HTTPS certificates automatically.

Optionally it configures [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/applications/configure-apps/) authentication: when users access the website, they are presented with a page to enter their email; if the address is part of the allowed list, an email with a one-time password will be sent to that address.

Cloudflare is [free](https://www.cloudflare.com/plans/free/) for small-scale use. To run the example, you'll need a Cloudflare account, with an active DNS zone.

## Configuration

The stack expects a few environment variables to be defined:

```env
CLOUDFLARE_API_TOKEN=[api token]
CLOUDFLARE_ACCOUNT_ID=[account id]
CLOUDFLARE_ZONE_ID=[zone id]
CLOUDFLARE_ZONE_NAME=example.com
CLOUDFLARE_TUNNEL_NAME=opslib
CLOUDFLARE_TUNNEL_SECRET=[some random string]
```

When [creating an API token](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/), select the "Create Custom Token" option, and configure the permissions like so:

![](./cloudflare-token-permissions.png)

The "Zone ID" and "Account ID" values are shown at the bottom right of the Cloudflare dashboard pages for the domain.

Optionally, you can define a list of emails, for people who are allowed to access the app. If not provided the app will be public.

```env
CLOUDFLARE_ALLOW_EMAILS=foo@example.com,bar@example.com
```

## Deployment

```shell
opslib - deploy
```

After deployment, the app will be accessible at `https://{CLOUDFLARE_TUNNEL_NAME}.{CLOUDFLARE_ZONE_NAME}` (`https://opslib.example.com` with the values above).

## Tunnel sidecar

Cloudflare tunnels work by running [cloudflared](https://github.com/cloudflare/cloudflared) alongside the app. It will connect to the Cloudflare network and route incoming traffic to the app.

We run cloudflared as a container named ``sidecar`` next to the app. It needs two bits of configuration to work:

* A _token_, which contains the secret key, Account ID, and Tunnel ID.
* The URL of the app which it should proxy. In our case it's port 80 of the ``nginx`` container.

## Terraform resources

The stack creates 4 resources using Terraform:

* ``cloudflare_tunnel``: The tunnel itself. It receives the secret key and is named after the DNS record.
* ``cloudflare_record``: The DNS record. It's a ``CNAME`` to ``{tunnel_id}.cfargotunnel.com``; this tells Cloudflare it shoudl route traffic through the tunnel.
* ``cloudflare_access_application``: The Access Application, configured to control access to our app's domain.
* ``cloudflare_access_policy``: The Access Policy defines who can access our application.
