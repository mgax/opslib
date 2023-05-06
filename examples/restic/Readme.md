# Opslib Restic Example

[Restic](https://restic.net/) is a wonderful tool for making backups. The Opslib integration handles the boilerplate of initializing repositories and creating backup scripts. It also provides a CLI command to run arbitrary `restic` commands on your repository.

## Configuration

The stack expects a few environment variables to be defined:

```env
export RESTIC_PASSWORD=[...]
```

## Running

Deploying the stack will set up the Restic repository and create a backup script:

```shell
opslib - deploy
```

The backup script does a few things:
1. Run a pre-command. This is useful to e.g. run a database dump, since it's better to back up an SQL dump than the database's data directory.
1. Set up environment variables with secrets. The script is created with permissions `700` but keep in mind secrets will be stored cleartext in the script.
1. Run `restic backup` with the specified paths and excludes.

Let's run the script:

```
$ ./demo/backup
repository 7cb28c82 opened (version 2, compression level auto)
no parent snapshot found, will read all files

Files:           2 new,     0 changed,     0 unmodified
Dirs:            7 new,     0 changed,     0 unmodified
Added to the repository: 3.422 KiB (2.740 KiB stored)

processed 2 files, 123 B in 0:00
snapshot 1c39e55a saved
```

We can then inspect the repository:

```
$ opslib restic run snapshots
repository 7cb28c82 opened (version 2, compression level auto)
ID        Time                 Host        Tags        Paths
--------------------------------------------------------------------------------------------------
1c39e55a  2023-04-04 20:08:07  ufo                     /opt/prj/opslib/examples/restic/demo/target
--------------------------------------------------------------------------------------------------
1 snapshots
```

```
$ opslib restic run dump latest /opt/prj/opslib/examples/restic/demo/target/wisdom.txt
repository 7cb28c82 opened (version 2, compression level auto)
Preudhomme's Law of Window Cleaning:
        It's on the other side.
```

## Remote repositories

Backups are more useful if they are saved elsewhere. We can configure `ResticRepository` to save its repository for example [on Backblaze](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html#backblaze-b2). Following the documentation, we specify the repository name as `b2:{b2_bucket}` and provide credentials as environment variables (the `env` prop).

```python
restic = ResticRepository(
    repository=f"b2:{b2_bucket}:",
    password=password,
    env=dict(
        B2_ACCOUNT_ID=b2_key_id,
        B2_ACCOUNT_KEY=b2_key,
    ),
)
```
