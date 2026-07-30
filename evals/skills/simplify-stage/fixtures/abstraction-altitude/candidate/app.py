class GreetingStrategy:
    def render(self, name):
        return f"Hello, {name}!"


def greeting(name):
    strategy = GreetingStrategy()
    return strategy.render(name)
