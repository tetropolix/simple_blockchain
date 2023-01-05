import traceback
import click
import contextlib

from node import Node


class NonWritable:
    def write(self, *args, **kwargs):
        pass

    def flush(self, *args, **kwargs):
        pass


class NodeCLI():
    def __init__(self, node: Node):
        self.node = node

    def run(self):
        @click.group()
        def cli():
            pass

        @cli.command(help='Shows current state of blockchain')
        def blockchain():
            print(self.node.blockchain)

        @cli.command(help='Lists all currently available peers in network')
        def nodes():
            print(self.node.nodes)

        while True:
            try:
                user_input = input("%s #: " %
                                   self.node.node_id.node_address).split()

                # *Very bad approach, quick fix to mute undesired stderr output from click library in case of wrong input
                with contextlib.redirect_stderr(NonWritable()):  # type: ignore
                    cli(args=user_input)  # CLI is global :/

            except SystemExit as e:  # manual catch due to click terminates execution after handling user input as per docs
                if (e.code == 0):  # 0 is normal exit 2 is for wrong input
                    pass
                elif (e.code == 2):
                    print('Unable to parse input, type --help for help')
                    pass
                elif (e.code):
                    print('RAISE')
                    print(e.code)
                    raise
            except Exception as e:
                traceback.print_exc()
                print(type(e))
                print(str(e))
