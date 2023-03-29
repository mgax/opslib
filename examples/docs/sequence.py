from opslib.components import Component, Stack


class Person(Component):
    def build(self):
        print(self)


class House(Component):
    def build(self):
        print(self)
        self.host = Person()
        print("house is ready")


class Demo(Stack):
    def build(self):
        print(self)
        self.house = House()
        print("knock knock")
        self.house.guest = Person()
        print("all done")


print("house:", repr(Demo().house))


def get_stack():
    return Demo()
