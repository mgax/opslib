API
===

Components
----------

.. module:: opslib.components

.. autoclass:: Component
   :members:

.. autoclass:: Stack
   :show-inheritance:
   :members:

.. autofunction:: walk

.. module:: opslib.props

.. autoclass:: Prop

.. autoclass:: InstanceProps

.. module:: opslib.lazy

.. autoclass:: Lazy

.. autoclass:: NotAvailable
   :show-inheritance:

.. autofunction:: evaluate

.. autofunction:: lazy_property

Operations
----------

.. module:: opslib.operations

.. autoclass:: Operation

.. autofunction:: apply

.. module:: opslib.results

.. autoclass:: Result
   :members:

.. autoclass:: OperationError

.. module:: opslib.local

.. autoclass:: LocalRunResult
   :show-inheritance:

.. autofunction:: run

.. module:: opslib.cli

.. autofunction:: get_main_cli

.. autofunction:: main

Places
------

.. module:: opslib.places

.. autoclass:: BaseHost
   :members:

.. autoclass:: LocalHost
   :show-inheritance:
   :members:

.. autoclass:: SshHost
   :show-inheritance:
   :members:

.. autoclass:: Directory
   :members: subdir, __truediv__, file

.. autoclass:: File

.. autoclass:: Command
   :members: run

Ansible
-------

.. module:: opslib.ansible

.. autoclass:: AnsibleAction
   :members: run

.. autoclass:: AnsibleResult

.. autofunction:: run_ansible

Terraform
---------

.. module:: opslib.terraform

.. autoclass:: TerraformProvider
   :members:

.. autoclass:: TerraformResource
   :members: import_resource, output, run

.. autoclass:: TerraformDataSource
   :members: output, run

.. autoclass:: TerraformResult
   :members:
