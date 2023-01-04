import socket
from concurrent import futures

from blockchain import Blockchain, Transaction
import protos.NodeConnector_pb2_grpc as NodeConnector_pb2_grpc
import protos.NodeConnector_pb2 as NodeConnector_pb2

import grpc


class NodeId:
    def __init__(self, node_id: str):
        self.node_id = node_id
        try:
            splitted = node_id.split(":")
            if len(splitted) != 2:
                raise ValueError(
                    "Unable to split node id %s to host and port part" % node_id)
            self.host = splitted[0]
            self.port = splitted[1]
            socket.inet_aton(self.host)
            if (int(self.port) < 2000 and int(self.port) > 10000):
                raise ValueError(
                    "Port for node id %s should be number in interval <2000,10000>" % node_id)
        except socket.error:
            raise ValueError(
                "Node id %s does not contain valid ip address" % node_id)


class NodeRPCService(NodeConnector_pb2_grpc.NodeConnectorServicer):
    def __init__(self, node_id: NodeId):
        self.node_id = node_id
        self.server = None

    def Greet(self, request, context):
        return NodeConnector_pb2.GreetResponse(node_id=self.node_id)

    def start_service(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
        NodeConnector_pb2_grpc.add_NodeConnectorServicer_to_server(
            self, self.server)
        self.server.add_insecure_port(self.node_id.node_id)
        self.server.start()
        self.server.wait_for_termination()

    def stop_service(self):
        if (self.server is not None):
            self.server.stop(None)


class Node():
    def __init__(self, node_id: str, blockchain: Blockchain, nodes: list[NodeRPCService], transactions: list[Transaction]) -> None:
        self.node_id = NodeId(node_id)
        self.blockchain = blockchain
        self.nodes: list[NodeRPCService] = nodes
        self.transactions: list[Transaction] = transactions
        self.node_rpc_service = NodeRPCService(self.node_id)
        self.node_rpc_service.start_service()

    @classmethod
    def create_node(cls, node_id: str, first_node: str):
        return cls(node_id, None, None, None)
