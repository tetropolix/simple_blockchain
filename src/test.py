import click


class NodeCLI():
    def __init__(self, node: str):
        self.node = node

    def run(self):
        while True:
            user_input = input("%s #: " %
                               self.node).split()
            self.test(args=user_input)

    @staticmethod
    @click.command()
    @click.argument('new')
    def test(new):
        click.echo('test')


if __name__ == '__main__':
    cli = NodeCLI('me')
    cli.run()
