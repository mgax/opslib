Contributing
============

Opslib development takes place on GitHub: https://github.com/mgax/opslib.

Setup
-----

To set up a development environment, first clone the repository, ``cd`` into
it, and create a virtualenv::

    git clone https://github.com/mgax/opslib
    cd opslib
    python3 -m venv .venv

Set up an ``.envrc`` file; this will enable the virtualenv automatically and
set up environment variables:

.. code-block:: none
    :caption: ``.envrc``

    source .venv/bin/activate
    export TF_PLUGIN_CACHE_DIR=$HOME/.terraform.d/plugin-cache

Approve the ``.envrc`` file::

    direnv allow

Install dependencies::

    pip install -U setuptools pip
    pip install poetry
    poetry install

Run the test suite::

    pytest
