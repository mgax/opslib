API
===

Components
----------

.. module:: opslib.components

.. autoclass:: Component
   :members:

.. autoclass:: Stack
   :show-inheritance:

.. module:: opslib.lazy

.. autoclass:: Lazy

.. autofunction:: evaluate

.. autofunction:: lazy_property

Operations
----------

.. module:: opslib.results

.. autoclass:: Result

.. autoclass:: OperationError

.. module:: opslib.local

.. autoclass:: LocalRunResult
   :show-inheritance:

.. autofunction:: run

Places
------

.. module:: opslib.places

.. autoclass:: BaseHost
   :members:

.. autoclass:: LocalHost
   :show-inheritance:

.. autoclass:: SshHost
   :show-inheritance:

.. autoclass:: Directory

.. autoclass:: File

.. autoclass:: Command

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
