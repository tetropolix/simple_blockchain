from __future__ import annotations
import logging
import sys
from datetime import datetime

from blockchain import Blockchain, Transaction, Block
from persistence.database import Database
import protos.NodeRPCService_pb2 as NodeRPCService_pb2
import node_composition

import grpc


class RemoteNode():
    def __init__(self, node_id: node_composition.NodeId | str):
        self.node_id = node_composition.NodeId(node_id) if isinstance(node_id, str) else node_id
        self.stub = node_composition.NodeRPCService.get_node_rpc_stub(self.node_id)

    def __eq__(self, other):
        if (not isinstance(other, RemoteNode)):
            return False
        return self.node_id.node_address == other.node_id.node_address

    def __hash__(self):
        return hash(self.node_id.node_address)

    def greet(self, sender: node_composition.NodeId):
        self.stub.Greet(NodeRPCService_pb2.GreetRequest(node_id=sender.node_address))

    def heartbeat(self, sender: node_composition.NodeId, nodes: list[node_composition.NodeId]):
        str_nodes = [node.node_address for node in nodes]
        self.stub.Heartbeat(NodeRPCService_pb2.HeartbeatRequest(node_id=sender.node_address, node_nodes=str_nodes))

    def transact(self, transaction: Transaction):
        self.stub.SendTransaction(transaction.to_grpc_message())

    def send_new_block(self, new_block: Block):
        self.stub.SendBlock(new_block.to_grpc_message())

    def query_blockchain(self) -> Blockchain:
        blockchain_resp: NodeRPCService_pb2.Blockchain = self.stub.QueryBlockchain(NodeRPCService_pb2.Empty())
        return Blockchain.from_grpc_message(blockchain_resp)


class Node():
    NODE_DB_FILE = 'persistence/p2p.db'
    NODE_DB_INIT_FILE = 'persistence/init.sql'

    def __init__(self, node_id: str, nodes: list[RemoteNode]) -> None:
        self.node_id = node_composition.NodeId(node_id)

        self.database = Database(Node.NODE_DB_FILE, Node.NODE_DB_INIT_FILE)
        blockchain = self.database.get_node_blockchain_state(self.node_id.node_address)
        transactions = self.database.get_node_stored_transactions(self.node_id.node_address)
        transactions = [] if transactions is None else transactions

        self.blockchain_manager = node_composition.BlockchainManager(self, blockchain, transactions, self.database)
        self.nodes_manager = node_composition.NodesManager(self.node_id, nodes)
        self.node_rpc_service = node_composition.NodeRPCService(self.node_id, self.nodes_manager, self.blockchain_manager)

        # self.blockchain_manager.update_blockchain_from_peers()
        self.node_rpc_service.start_service()
        self.nodes_manager.start_heartbeat_task()

    @ property
    def nodes(self) -> list[str]:
        return [n.node_id.node_address for n in self.nodes_manager.nodes]

    @ classmethod
    def logger(cls):
        return logging.getLogger(cls.__name__)

    @ classmethod
    def create_node(cls, node_id: str, node_to_contact: str | None):
        nodes: list[RemoteNode] = []
        if (node_to_contact is not None):  # not the first node
            remote_node = RemoteNode(node_to_contact)
            try:
                remote_node.greet(node_composition.NodeId(node_id))
            except grpc.RpcError as e:
                if (e.code() == grpc.StatusCode.UNAVAILABLE):  # type: ignore
                    sys.exit("Node %s unavailable" %
                             remote_node.node_id.node_address)
                raise
            nodes.append(remote_node)
        return cls(node_id, nodes)

    def make_transaction(self, receiver: str, amount: int):
        sender = self.node_id.node_address
        timestamp = int(datetime.now().timestamp())
        if(self.blockchain_manager.get_amount() < amount):
            raise ValueError('Transaction with amount higher than available balance')
        transaction = Transaction(sender, receiver, amount, timestamp)
        self.nodes_manager.broadcast_transaction(transaction)
        self.blockchain_manager.add_transaction(transaction)

    def node_balance(self):
        return self.blockchain_manager.get_amount()

    def manual_blockchain_update(self):
        self.blockchain_manager.update_blockchain_from_peers()

    def stop(self):
        self.node_rpc_service.stop_service()
        self.nodes_manager.stop_heartbeat()
        self.database.stop()
