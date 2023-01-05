import logging
import socket
from concurrent import futures
import sys
import threading
import time

from blockchain import Blockchain, Transaction
import protos.NodeRPCService_pb2_grpc as NodeRPCService_pb2_grpc
import protos.NodeRPCService_pb2 as NodeRPCService_pb2

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


class NodeRPCService(NodeRPCService_pb2_grpc.NodeRPCServiceServicer):
    def __init__(self, node_id: NodeId | str):
        self.node_id = NodeId(node_id) if isinstance(node_id, str) else node_id
        self.server = None

    @staticmethod
    def get_node_rpc_stub(node_id: NodeId) -> NodeRPCService_pb2_grpc.NodeRPCServiceStub:
        channel = grpc.insecure_channel(node_id.node_address)
        return NodeRPCService_pb2_grpc.NodeRPCServiceStub(channel)

    def Greet(self, request, context):
        return NodeRPCService_pb2.GreetResponse(node_id=self.node_id.node_address)

    def Heartbeat(self, request, context):
        print(request)
        return NodeRPCService_pb2.Empty()

    def start_service(self):
        # TODO start service in separate thread
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
        NodeRPCService_pb2_grpc.add_NodeRPCServiceServicer_to_server(
            self, self.server)
        self.server.add_insecure_port(self.node_id.node_address)
        self.server.start()
        self.server.wait_for_termination()

    def stop_service(self):
        if (self.server is not None):
            self.server.stop(None)


class ConnectedNodesManager:
    HEARTBEAT_INTERVAL = 3  # seconds

    def __init__(self, node_id: NodeId, nodes: list[NodeRPCService]) -> None:
        self.node_id = node_id
        self.nodes = nodes
        self.heartbeat_running = False
        self.heartbeat_task = None

    def _create_heartbeat_task(self):
        return threading.Thread(target=self.heartbeat)

    def start_heartbeat_task(self):
        print('starting hb')
        if (self.heartbeat_task is not None and self.heartbeat_task.is_alive()):
            self.stop_heartbeat()
            self.heartbeat_task.join()
        self.heartbeat_task = self._create_heartbeat_task()
        self.heartbeat_running = True
        self.heartbeat_task.start()

    def heartbeat(self):
        while True:
            time.sleep(ConnectedNodesManager.HEARTBEAT_INTERVAL)
            if (not self.heartbeat_running):
                break
            for node in self.nodes:
                nodes = [node.node_id.node_address for node in self.nodes]
                stub = NodeRPCService.get_node_rpc_stub(node.node_id)
                stub.Heartbeat(NodeRPCService_pb2.HeartbeatRequest(
                    node_id=self.node_id.node_address, node_nodes=nodes))

    def stop_heartbeat(self):
        self.heartbeat_running = False


class Node():
    def __init__(self, node_id: str, blockchain: Blockchain | None, nodes: list[NodeRPCService], transactions: list[Transaction]) -> None:
        self.node_id = NodeId(node_id)
        self.blockchain = blockchain if blockchain is not None else Blockchain(
            None)
        self.transactions = transactions
        self.connected_nodes_manager = ConnectedNodesManager(
            self.node_id, nodes)
        self.node_rpc_service = NodeRPCService(self.node_id)

        self.connected_nodes_manager.start_heartbeat_task()
        self.node_rpc_service.start_service()

    @property
    def nodes(self):
        return self.connected_nodes_manager.nodes

    @classmethod
    def logger(cls):
        return logging.getLogger(cls.__name__)

    @classmethod
    def create_node(cls, node_id: str, node_to_contact: str | None):
        nodes: list[NodeRPCService] = []
        transactions: list[Transaction] = []
        if (node_to_contact is not None):  # not the first node
            try:
                stub = NodeRPCService.get_node_rpc_stub(
                    NodeId(node_to_contact))
                stub.Greet(NodeRPCService_pb2.GreetRequest(
                    node_id=NodeId(node_id).node_address))
            except grpc.RpcError as e:
                if (e.code() == grpc.StatusCode.UNAVAILABLE):  # type: ignore
                    sys.exit("Node %s unavailable" %
                             NodeId(node_to_contact).node_address)
                raise
            nodes.append(NodeRPCService(node_to_contact))
        return cls(node_id, None, nodes, transactions)
