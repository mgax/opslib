from opslib.components import Component, Stack
from opslib.places import LocalHost


class Cat(Component):
    def build(self):
        self.speak = LocalHost().command(
            args=["echo", "meow"],
        )


class House(Component):
    def build(self):
        self.spot = Cat()
        self.oscar = Cat()


stack = Stack(__name__)
stack.apartment = House()

print(list(stack))
print(list(stack.apartment))
print(stack.apartment.spot)
print(repr(stack.apartment.spot))
