# Opslib tutorial

The Opslib tutorial project fully implemented.

1. Set up a virtualenv:

    ```shell
    python3 -m venv .venv
    ```

1. Create an `.envrc` file:

    ```shell
    source .venv/bin/activate
    ```

1. Approve the `.envrc` file:

    ```shell
    direnv allow
    ```

1. Install `opslib` in development mode:

    ```shell
    pip install git+https://github.com/mgax/opslib
    ```

1. Initialize local state:

    ```shell
    opslib - init
    ```

1. Check what will be deployed:

    ```shell
    opslib - diff
    ```

1. Deploy:

    ```shell
    opslib - deploy
    ```
