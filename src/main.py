import datetime
from blockchain import Block
from node import Node


def main() -> None:
    block = Block.create_genesis()
    print(block.block_hash)
    block2 = Block.create_block(
        1, datetime.datetime.now(), [], block.prev_hash)
    print(block2.block_hash)
    node = Node.create_node('127.0.0.1:3001', None)


if __name__ == '__main__':
    main()
