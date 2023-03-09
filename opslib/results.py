class OperationError(Exception):
    def __init__(self, *args, result):
        assert result.failed
        self.result = result
        super().__init__(*args)

    def __repr__(self):
        return f"<{type(self).__name__} {self.args!r}>"


class Result:
    def __init__(self, changed=False, output="", failed=False):
        self.changed = changed
        self.output = output
        self.failed = failed

    def __repr__(self):
        return f"<{type(self).__name__} changed={self.changed} failed={self.failed}>"

    def raise_if_failed(self, *args):
        if self.failed:
            raise OperationError(*args, result=self)
