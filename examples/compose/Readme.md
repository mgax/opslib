# Opslib Compose Example

The Compose example illustrates how to set up a (Docker) Compose project, with automated commands to build, pull and start the containers.

## `run_after`

It would be overkill to run ``build``, ``pull``, ``up -d`` and ``restart nginx`` on every deployment. We can tell the [``Command``](https://pyopslib.readthedocs.io/en/latest/api.html#opslib.places.Command) component to run _only after another component changes_ by specifying the ``run_after`` prop.


```py
        self.compose_up = self.directory.host.command(
            args=[*self.compose_args, "up", "-d", "-t1"],
            run_after=[
                self.compose_file,
                self.compose_build,
            ],
        )
```

In this example, `docker compose up -d -t1` will be run only if the `docker-compose.yml` file changes, or if the `docker compose build` command is run.

You can verify that this works: make changes to either ``stack.py``, ``nginx.conf``, ``app.py`` or ``Dockerfile``, then run ``opslib - deploy``, and watch Opslib only run the commands that are necessary.

## Run `docker compose`

The ``App`` component defines a CLI command, ``compose``, which can be run, for example, to tear down the Compose project:

```shell
opslib app compose down
```
