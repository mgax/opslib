from opslib import LocalHost, Stack

stack = Stack(__name__)
stack.host = LocalHost()
stack.hello = stack.host.command(
    args=["echo", "Hello world!"],
)
