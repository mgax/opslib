API
===

Components
----------

.. module:: opslib.components

.. autoclass:: Component
   :members:

.. autoclass:: Stack
   :show-inheritance:

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

Terraform
---------

.. module:: opslib.terraform

.. autoclass:: TerraformProvider

.. autoclass:: TerraformResource
