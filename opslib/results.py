from click import echo


class OperationError(Exception):
    """
    Exception raised when an operation fails.

    :ivar result: The operation's :class:`Result`, useful to figure out what
                  went wrong.
    """

    def __init__(self, *args, result):
        assert result.failed
        self.result = result
        super().__init__(*args)

    def __repr__(self):
        return f"<{type(self).__name__} {self.args!r}>"


class Result:
    """
    The Results class wraps the outcome and output of an operation.

    :ivar changed: ``True`` if the operation changed anything.
    :ivar output: Textual output.
    :ivar failed: ``True`` if the operation ended in failure.
    """

    def __init__(self, changed=False, output="", failed=False):
        self.changed = changed
        self.output = output
        self.failed = failed

    def __repr__(self):
        return f"<{type(self).__name__} changed={self.changed} failed={self.failed}>"

    def raise_if_failed(self, *args):
        """
        Check if the ``failed`` flag is set, and if so, raises
        :class:`OperationError`.

        :param args: Arguments to be passed to *OperationError*.
        """

        if self.failed:
            raise OperationError(*args, result=self)

    def print_output(self):
        if self.output:
            echo(self.output)
