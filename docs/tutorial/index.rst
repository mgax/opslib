Tutorial
========

.. toctree::
   :caption: Contents:
   :maxdepth: 1

   local
   cloud

This tutorial will walk you through deploying a web application using Opslib.
We'll use Gitea_ as our application, because it's a good example of a well
packaged, easy to deploy application.

.. _Gitea: https://gitea.io/

At first, we'll deploy the app locally, to test our stack and experiment more
easily. Then we'll set up a Hetzner_ VPS, and finally expose the app to the
internet using `Cloudflare Tunnels`_.

.. _Hetzner: https://www.hetzner.com/
.. _Cloudflare Tunnels: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/

The completed project is available at
https://github.com/mgax/opslib/tree/main/examples/tutorial; feel free to
reference it if the code snippets in the tutorial are confusing.

First, follow the guide in :ref:`Getting Started`, then continue to
:doc:`local`.
