Terraform wrapper
=================

The components defined in the :mod:`opslib.terraform` module allow calling out
to Terraform providers from `Terraform Registry`_, to deploy resources and
query data sources.

.. _Terraform Registry: https://registry.terraform.io/

.. code-block:: python

    from opslib import Stack
    from opslib.terraform import TerraformProvider

    stack = Stack(__name__)

    # https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs
    stack.cloudflare = TerraformProvider(
        name="cloudflare",
        source="cloudflare/cloudflare",
        version="~> 4.2",
    )

    stack.zone = stack.cloudflare.data(
        type="cloudflare_zone",
        name="example.com",
        output=["id"],
    )

    stack.www_record = stack.cloudflare.resource(
        type="cloudflare_record",
        args=dict(
            zone_id=stack.zone.output["id"],
            type="A",
            name="www",
            value="12.34.56.78",
        ),
    )

Providers
---------

:class:`~opslib.terraform.TerraformProvider` configures a provider. Unless
otherwise configured, the provider will be installed in the state directory of
the *TerraformProvider* instance, and used by all resources and data sources
linked to the instance.

Many providers require configuration of e.g. API credentials. This can be
specified through the ``config`` prop, and many providers support some
configuration through environment variables. Consult each provider's
documentation for details.

Resources
---------

:class:`~opslib.terraform.TerraformResource` defines a single `Terraform
Resource`_. The *args* prop provides a dictionary of arguments for the
resource.

*output* (optional) is a list of attributes to be fetched from the resource.
They are accessible on the :attr:`~opslib.terraform.TerraformResource.output`
property, which is a dictionary of lazy values.

.. _Terraform Resource: https://developer.hashicorp.com/terraform/language/resources

After a successful deployment, the component instance is marked as "up to
date", and will be skipped in subsequent deployments, unless any of the props
change. To check if remote state has changed, run ``opslib - diff``.

Many providers allow importing pre-existing resources into Terraform. Opslib
also supports this:

.. code-block:: none

    $ opslib www_record import "<zone_id>/<record_id>"

When a *TerraformResource* component is destroyed, the underlying resource is
destroyed, the same as if ``terraform apply -destroy`` was run.

Data Sources
------------

:class:`~opslib.terraform.TerraformDataSource` defines a single `Terraform Data
Source`_. The *args* prop provides a dictionary of arguments for the data
source.

*output* (optional) is a list of attributes to be fetched from the data source.
They are accessible on the :attr:`~opslib.terraform.TerraformDataSource.output`
property, which is a dictionary of lazy values.

.. _Terraform Data Source: https://developer.hashicorp.com/terraform/language/data-sources
