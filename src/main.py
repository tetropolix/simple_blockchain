from __future__ import annotations
import sys
from argparse import ArgumentParser, Action

from node import Node
from node_cli import NodeCLI

arg_parser = ArgumentParser()


def main() -> None:
    # block = Block.create_genesis()
    # print(block.block_hash)
    # block2 = Block.create_block(
    #     1, datetime.datetime.now(), [], block.prev_hash)
    # print(block2.block_hash)
    try:
        print('Arguments provided to CLI: ' + str(sys.argv))
        node_to_contact = None
        if (len(sys.argv) > 2):
            node_to_contact = sys.argv[2]
        node = Node.create_node(sys.argv[1], node_to_contact)
        print('AFTER node creation')
        cli = NodeCLI(node)
        cli.run()
    except Exception as e:
        print('MAIN')
        print(e)


if __name__ == '__main__':
    main()
