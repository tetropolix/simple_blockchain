from __future__ import annotations
import sys

from node import Node
from node_cli import NodeCLI

import click


@click.command()
@click.argument('my_address', type=str)
@click.option('--connect_to', default=None, type=str,help='Address of node in p2p network to contact')
def main(my_address, connect_to) -> None:
    """
    \b
    Usage example: 
        - python main.py 3002 // Creates localhost node on port 3002, which has access to only it's network
        - python main.py 127.0.0.1:3005 --connect_to=3002// Creates localhost node on port 3005, which contacts localhost node on port 3002
    \b
    Notes:
        - address of node can be in {ip address}:{port} or {port} format
        - if CONNECT_TO option is ommited, created node can connect to the p2p network only when another node sends heartbeat to the local one
    """
    node = Node.create_node(my_address, connect_to)
    cli = NodeCLI(node)
    cli.run()


if __name__ == '__main__':
    main()
