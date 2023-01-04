import sys
import datetime

from blockchain import Block
from node import Node


def main() -> None:
    # block = Block.create_genesis()
    # print(block.block_hash)
    # block2 = Block.create_block(
    #     1, datetime.datetime.now(), [], block.prev_hash)
    # print(block2.block_hash)
    print(sys.argv)
    node_to_contact = None
    if (len(sys.argv) > 2):
        node_to_contact = sys.argv[2]
    node = Node.create_node(sys.argv[1], node_to_contact)


if __name__ == '__main__':
    main()
