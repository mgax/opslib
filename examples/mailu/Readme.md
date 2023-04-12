# Opslib Mailu Example

[Mailu](https://mailu.io) is a full mail server packaged as a set of container images. This example installs Mailu on a Hetzner VPS with DNS records configured on Cloudflare and daily Restic backups to Backblaze.

Mailu supports clamav antivirus, but it's not enabled in this example, to save on memory requirements.

## Configuration

The stack expects a few environment variables to be defined:

```env
CLOUDFLARE_API_TOKEN=[api token]
CLOUDFLARE_ZONE_NAME=example.com
HCLOUD_TOKEN=[api token] # https://docs.hetzner.cloud/#getting-started
B2_APPLICATION_KEY_ID=[...]
B2_APPLICATION_KEY=[...]
MAILU_HOSTNAME=mailu.example.com
MAILU_DOMAIN=example.com
RESTIC_PASSWORD=[some random password]
```

Make sure the Cloudflare token has "Zone - DNS - Edit" permission.

## Deployment

```shell
opslib - init
opslib - deploy
```

Create an initial admin user; replace `PASSWORD` with an initial password. Yes, there are 3 `admin`s in that command: the _admin_ command of the Opslib component, the mailu _admin_ subcommand which creates a user, and finally the _admin_ username of the new user.

```shell
opslib mailu admin admin admin mailu.opslib.grep.ro PASSWORD
```

Then go to the web admin at `https://{MAILU_HOSTNAME}/admin`, log in, and change the password from the _Update password_ link in the menu on the left.
