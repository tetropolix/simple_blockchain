from __future__ import annotations
import sys
import traceback
import click
import contextlib

from node import Node
from node_composition import NodeId


class NonWritable:
    def write(self, *args, **kwargs):
        pass

    def flush(self, *args, **kwargs):
        pass


class NodeCLI():
    def __init__(self, node: Node):
        self.node = node
        self.manual_exit = False

    def run(self):
        def node_id_prompt_util(user_input):
            try:
                return NodeId(user_input)
            except ValueError:
                raise click.UsageError('Inavlid input for node address %s' % user_input)

        def non_negative_amount(user_input):
            try:
                if(int(user_input) <0):
                    raise click.UsageError('Amount must be non negative integer')
                return int(user_input)
            except (ValueError,TypeError):
                raise click.UsageError('Amount must be non negative integer')


        @click.group()
        def cli():
            pass

        @cli.command(help='Shows current state of blockchain')
        def blockchain():
            print(self.node.blockchain_manager.blockchain)

        @cli.command(help='Lists all currently available peers in network')
        def nodes():
            print(self.node.nodes)

        @cli.command(help='Lists all currently available transactions for this node')
        def transactions():
            if (not len(self.node.blockchain_manager.transactions)):
                print('No transactions registered')
                return
            for t in self.node.blockchain_manager.transactions:
                print(t)

        @cli.command(help='Manual update of current blockchain state')
        def update():
            self.node.manual_blockchain_update()

        @cli.command(help='Shows current balanace of the node')
        def balance():
            print(self.node.node_balance())

        @cli.command(help='Generates transaction which will be broadcasted to all available peers')
        def transact():
            receiver: NodeId = click.prompt('... Enter full address of receiver or port', value_proc=node_id_prompt_util)
            amount: int = click.prompt('... Enter amount as integer', value_proc=non_negative_amount)
            try:
                self.node.make_transaction(receiver.node_address, amount)
            except ValueError:
                print('Insufficient funds!')

        @cli.command(help='Disconnects node from the network')
        def exit():
            self.node.stop()
            print('Node has been disconnected')
            self.manual_exit = True

        while True:
            try:
                user_input = input("%s #: " %
                                   self.node.node_id.node_address).split()

                # *Very bad approach, quick fix to mute undesired stderr output from click library in case of wrong input
                with contextlib.redirect_stderr(NonWritable()):  # type: ignore
                    cli(args=user_input)  # CLI is global :/

            except SystemExit as e:  # manual catch due to click terminates execution after handling user input as per docs
                if (self.manual_exit):
                    sys.exit(0)
                if (e.code == 0 or e.code == 1):  # 0 is normal exit 2 is for wrong input
                    pass
                elif (e.code == 2):
                    print('Unable to parse input, type --help for help')
                    pass
                elif (e.code):
                    print('Unhandled e.code')
                    raise
            except KeyboardInterrupt as e:  # kill node threads
                self.node.stop()
                raise
            except Exception as e:
                traceback.print_exc()
                print(type(e))
                print(str(e))
