import socket
from concurrent import futures

from blockchain import Blockchain, Transaction
import protos.NodeConnector_pb2_grpc as NodeConnector_pb2_grpc
import protos.NodeConnector_pb2 as NodeConnector_pb2

import grpc


class NodeId:
    def __init__(self, node_id: str):
        self.node_address = node_id
        try:
            splitted = self.node_address.split(":")
            if len(splitted) == 1:
                self.node_address = self._only_port_provided(node_id)
            splitted = self.node_address.split(":")
            if len(splitted) != 2:
                raise ValueError(
                    "Unable to split node id %s to host and port part" % node_id)
            self.host = splitted[0]
            self.port = splitted[1]
            socket.inet_aton(self.host)
            if (int(self.port) < 2000 and int(self.port) > 10000):
                raise ValueError(
                    "Port %s should be number in interval <2000,10000>" % node_id)
        except socket.error:
            raise ValueError(
                "Node id %s does not contain valid ip address" % node_id)

    def _only_port_provided(self, port: str) -> str:
        if (int(port) < 2000 or int(port) > 10000):
            raise ValueError(
                "Port %s should be number in interval <2000,10000>" % port)
        return "127.0.0.1:"+port


class NodeRPCService(NodeConnector_pb2_grpc.NodeConnectorServicer):
    def __init__(self, node_id: NodeId):
        self.node_id = node_id
        self.server = None

    @staticmethod
    def get_node_rpc_stub(node_id: NodeId) -> NodeConnector_pb2_grpc.NodeConnectorStub:
        channel = grpc.insecure_channel(node_id.node_address)
        return NodeConnector_pb2_grpc.NodeConnectorStub(channel)

    def Greet(self, request, context):
        return NodeConnector_pb2.GreetResponse(node_id=self.node_id.node_address)

    def start_service(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
        NodeConnector_pb2_grpc.add_NodeConnectorServicer_to_server(
            self, self.server)
        self.server.add_insecure_port(self.node_id.node_address)
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
    def create_node(cls, node_id: str, node_to_contact: str | None):
        if (node_to_contact is not None):
            stub = NodeRPCService.get_node_rpc_stub(NodeId(node_to_contact))
            resp = stub.Greet(NodeConnector_pb2.GreetRequest(
                node_id=NodeId(node_id).node_address))
        return cls(node_id, None, None, None)
