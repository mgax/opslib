from opslib.components import Component, Stack
from opslib.places import LocalHost
from opslib.props import Prop


class Cat(Component):
    class Props:
        color = Prop(str)
        energy = Prop(int, default=2)

    def build(self):
        if self.props.energy > 5:
            self.play = LocalHost().command(
                args=["echo", f"You see a blur of {self.props.color}."],
            )


stack = Stack(__name__)
stack.spot = Cat(color="orange", energy=11)
print(stack.spot.props)
print(stack.spot.play.run().output)
stack.oscar = Cat(color="orange")
print(stack.oscar.props)
print(stack.oscar.play.run().output)
