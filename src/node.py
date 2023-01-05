from __future__ import annotations
import logging
import sys


from blockchain import Blockchain, Transaction
import protos.NodeRPCService_pb2_grpc as NodeRPCService_pb2_grpc
import protos.NodeRPCService_pb2 as NodeRPCService_pb2
import node_composition

import grpc


class RemoteNode():
    def __init__(self, node_id: node_composition.NodeId | str):
        self.node_id = node_composition.NodeId(
            node_id) if isinstance(node_id, str) else node_id
        self.stub = node_composition.NodeRPCService.get_node_rpc_stub(
            self.node_id)

    def __eq__(self, other):
        if (not isinstance(other, RemoteNode)):
            return False
        return self.node_id.node_address == other.node_id.node_address

    def __hash__(self):
        return hash(self.node_id.node_address)

    def greet(self, sender: node_composition.NodeId):
        self.stub.Greet(NodeRPCService_pb2.GreetRequest(
            node_id=sender.node_address))

    def heartbeat(self, sender: node_composition.NodeId, nodes: list[node_composition.NodeId]):
        str_nodes = [node.node_address for node in nodes]
        self.stub.Heartbeat(NodeRPCService_pb2.HeartbeatRequest(
            node_id=sender.node_address, node_nodes=str_nodes))


class Node():
    def __init__(self, node_id: str, blockchain: Blockchain | None, nodes: list[RemoteNode], transactions: list[Transaction]) -> None:
        self.node_id = node_composition.NodeId(node_id)
        self.blockchain = blockchain if blockchain is not None else Blockchain(
            None)
        self.transactions = transactions
        self.nodes_manager = node_composition.NodesManager(
            self.node_id, nodes)
        self.node_rpc_service = node_composition.NodeRPCService(
            self.node_id, self.nodes_manager)
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
        transactions: list[Transaction] = []
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
        return cls(node_id, None, nodes, transactions)
