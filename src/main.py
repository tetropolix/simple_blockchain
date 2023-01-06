from __future__ import annotations
import sys

from node import Node
from node_cli import NodeCLI


def main() -> None:
    print('Arguments provided to CLI: ' + str(sys.argv))
    node_to_contact = None
    if (len(sys.argv) > 2):
        node_to_contact = sys.argv[2]
    node = Node.create_node(sys.argv[1], node_to_contact)
    cli = NodeCLI(node)
    cli.run()


if __name__ == '__main__':
    main()
