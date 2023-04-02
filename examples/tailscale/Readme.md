# Opslib Tailscale Example

The Tailscale example creates a VPS and adds it to the user's [Tailnet](https://tailscale.com/kb/1136/tailnet/). Upon deployment, the `TailscaleNetwork` component will create a one-off [auth key](https://tailscale.com/kb/1085/auth-keys/), and with it, register the host on the Tailnet.

[Tailscale](https://tailscale.com/) is a great way to connect all your hosts on a network that magically works regardless of where your devices are located on the internet. No need to whitelist IPs, open ports, or share keys; it will set up point-to-point [Wireguard](https://www.wireguard.com/) connections on demand between any two hosts that need to communicate.

## Configuration

The stack expects these environment variables to be defined:

```env
HCLOUD_TOKEN=... # https://docs.hetzner.cloud/#getting-started
TAILSCALE_API_KEY=tskey-api-... # https://tailscale.com/kb/1101/api/
```

## CLI

The `TailscaleNode` comopnent defines a CLI command named `run` that runs `tailscale` on the remote host:

```shell
opslib vps.tailscale run status
```
